FROM python:3.13-slim

WORKDIR /tracker_adk_sample

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --force-reinstall google-adk

ENV PATH="/root/.local/bin:$PATH"
ENV GOOGLE_GENAI_USE_VERTEXAI=FALSE
ENV GOOGLE_API_KEY=AIzaSyAWjaYe3_S5djdQuhCbr7Nv0EEJCd1CN-0

COPY . .
# Let Cloud Run know we use this port
EXPOSE 8000

# Use shell to expand $PORT
CMD ["adk", "web", "/tracker_adk_sample","--host", "0.0.0.0"]