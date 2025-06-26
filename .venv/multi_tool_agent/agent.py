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

    # --- Fix: Clean up suffixes like 1st, 2nd, 3rd, 4th ---
    def clean_ordinal_suffix(date_str):
        return re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)

    # --- Fix: Date ---
    date_match = re.search(r"Today's date is ([\w\d\s]+)", text)
    if date_match:
        raw_date = clean_ordinal_suffix(date_match.group(1).strip())
        try:
            entry["Date"] = datetime.strptime(raw_date, "%d %B %Y").strftime("%Y-%m-%d")
            entry["Date update on"] = entry["Date"]
        except:
            entry["Date"] = entry["Date update on"] = ""

    # Project Name
    proj_match = re.search(r"worked on (.*?) project", text)
    entry["Project Name"] = proj_match.group(1).strip() + " project" if proj_match else ""

    # Leave/WFH
    entry["Leave/WFH"] = "WFH" if "from home" in text else "Office"

    # Tasks Completed Today
    task_match = re.search(r"completed (.*?)(?:,|\.|;)", text)
    entry["Tasks Completed Today"] = task_match.group(1).strip() if task_match else ""

    # Hours Worked
    hours_match = re.search(r"(\d+)\s+hours\s+worked", text)
    entry["Hours Worked"] = hours_match.group(1) if hours_match else ""

    # Blockers
    blockers_match = re.search(r"(no blockers|blockers.*?)\.", text)
    entry["Blockers / Issues"] = blockers_match.group(1).strip() if blockers_match else ""

    # Tomorrow Plan
    tomorrow_match = re.search(r"tomorrow.*?(?:will|to)\s+(.*?)(?:\.|,|$)", text)
    entry["Planned Tasks for Tomorrow"] = tomorrow_match.group(1).strip() if tomorrow_match else ""

    # --- Fix: Notes/Remarks at end ---
    note_match = re.search(r"Notes?:\s*(.+)", text, re.IGNORECASE)
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
