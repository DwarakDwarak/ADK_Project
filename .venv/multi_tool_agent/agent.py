from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.adk.agents import Agent
import os
import re
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
# ------------------ File Paths ------------------
base_dir = os.path.dirname(__file__)
credential = os.path.join(base_dir, 'service.json')

# ------------------ Google Sheets Setup ------------------
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(credential, scopes=SCOPES)
sheet_service = build("sheets", "v4", credentials=creds)

# ------------------ Function: Log Daily Update ------------------
def log_daily_update(name: str, entry: dict) -> dict:
    try:
        sheet_name = name.strip()
        sheets_metadata = sheet_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = [s['properties']['title'] for s in sheets_metadata['sheets']]

        if sheet_name not in existing_sheets:
            return {
                "status": "error",
                "error_message": f"Sheet '{sheet_name}' does not exist. Cannot add entry."
            }

        values = [[
            entry.get("Date", ""),
            entry.get("Project Name", ""),
            entry.get("Leave/WFH", ""),
            entry.get("Tasks Completed Today", ""),
            entry.get("Hours Worked", ""),
            entry.get("Blockers / Issues", ""),
            entry.get("Planned Tasks for Tomorrow", ""),
            entry.get("Notes/Remarks", ""),
            entry.get("Date update on", "")
        ]]
        sheet_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values}
        ).execute()

        return {
            "status": "success",
            "report": f"Daily update added to sheet '{sheet_name}'."
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# ------------------ Function: Parse Natural Language ------------------
def parse_natural_language(text: str) -> dict:
    entry = {}

    def clean_ordinal_suffix(date_str):
        return re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)

    # --- Date ---
    date_match = re.search(r"(?:Today's date is|Date[:\-]?)\s*([\d]{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})", text, re.IGNORECASE)
    if date_match:
        raw_date = clean_ordinal_suffix(date_match.group(1).strip())
        try:
            entry["Date"] = datetime.strptime(raw_date, "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            entry["Date"] = ""
    else:
        entry["Date"] = ""
    entry["Date update on"] = entry["Date"]

    # --- Project Name ---
    proj_match = re.search(r"(?:worked on|Project[:\-]?)\s*(.*?)(?:\s+project)?[\.,\n]", text, re.IGNORECASE)
    entry["Project Name"] = proj_match.group(1).strip() + " project" if proj_match else ""

    # --- Leave/WFH ---
    if re.search(r"(from home|wfh)", text, re.IGNORECASE):
        entry["Leave/WFH"] = "WFH"
    elif re.search(r"(office|onsite)", text, re.IGNORECASE):
        entry["Leave/WFH"] = "Office"
    else:
        entry["Leave/WFH"] = ""

    # --- Tasks Completed Today ---
    task_match = re.search(r"(?:completed|Tasks Done[:\-]?)\s+(.*?)(?:[\.,\n]|Hours|Blockers|Tomorrow)", text, re.IGNORECASE)
    entry["Tasks Completed Today"] = task_match.group(1).strip() if task_match else ""

    # --- Hours Worked ---
    hours_match = re.search(r"(\d+)\s+(?:hrs|hours)\s+worked", text, re.IGNORECASE)
    if not hours_match:
        hours_match = re.search(r"Hours[:\-]?\s*(\d+)", text, re.IGNORECASE)
    entry["Hours Worked"] = hours_match.group(1) if hours_match else ""

    # --- Blockers / Issues ---
    blockers_match = re.search(r"(no blockers|Blockers[:\-]?\s*.*?)(?:[\n\.]|Tomorrow|Note|$)", text, re.IGNORECASE)
    if blockers_match:
        blockers_text = blockers_match.group(1).strip()
        # Normalize phrasing like "Blockers: none" → "no blockers"
        if re.search(r"\bnone\b|\bno\b", blockers_text.lower()):
            entry["Blockers / Issues"] = "no blockers"
        else:
            entry["Blockers / Issues"] = blockers_text.replace("Blockers:", "").strip()
    else:
        entry["Blockers / Issues"] = ""

    # --- Planned Tasks for Tomorrow ---
    tomorrow_match = re.search(r"(?:tomorrow.*?(?:will|to)\s+|Tomorrow[:\-]?)\s*(.*?)(?:[\n\.]|Note|$)", text, re.IGNORECASE)
    entry["Planned Tasks for Tomorrow"] = tomorrow_match.group(1).strip() if tomorrow_match else ""

    # --- Notes/Remarks ---
    note_match = re.search(r"(?:Note[s]?:|Remarks[:\-]?)\s*(.+)", text, re.IGNORECASE)
    entry["Notes/Remarks"] = note_match.group(1).strip() if note_match else ""

    return entry



# ------------------ Function: Handle Natural Language Update ------------------
def handle_natural_language_update(prompt: str) -> dict:
    # Expect strict format: "Update for Name: ..."
    name_match = re.match(r"Update for (\w+):", prompt.strip(), re.IGNORECASE)
    
    if not name_match:
        return {
            "status": "error",
            "error_message": (
                "Please begin your message with a clear format like: 'Update for Siva: ...'"
            )
        }

    name = name_match.group(1).strip()

    # Parse the update
    entry = parse_natural_language(prompt)

    # Log to sheet
    return log_daily_update(name, entry)



# ------------------ Agent Setup ------------------
root_agent = Agent(
    name="task_logger_agent",
    model="gemini-2.0-flash",
    description="Manages employee task and daily updates in Google Sheets.",
    instruction=(
        "Use `handle_natural_language_update` for natural language input.\n"
        "Use `log_daily_update` if the entry is already structured."
    ),
    tools=[log_daily_update, handle_natural_language_update],
)



# Update for Kevin: worked on Daily Task Logger project from home, completed Google Sheets logging integration, 2 hours worked, no blockers, tomorrow will work on email feature. Today's date is 30th June 2025. Note: All modules integrated successfully.