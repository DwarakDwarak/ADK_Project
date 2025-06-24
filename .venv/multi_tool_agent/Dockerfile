# Use a minimal Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (optional but safe for Google API clients)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY requirements.txt .
COPY agent.py .
COPY service.json .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV GOOGLE_GENAI_USE_VERTEXAI=FALSE
ENV GOOGLE_API_KEY=AIzaSyAWjaYe3_S5djdQuhCbr7Nv0EEJCd1CN-0
ENV AGENT_ROOT=agent.root_agent  # Adjust this to match the correct path to your agent object
ENV GOOGLE_SHEET_ID=1HTc47DLLkCoGcG0c_TR8aeBLU34NTAOea4o2lYQCwgY

# Run ADK web interface
CMD ["adk", "web"]
