FROM python:3.12-slim

WORKDIR /app

# Paths are relative to the build context, which docker-compose sets to
# ./dashboard - same convention used by the other services in the repo
# (camp_manager, ambient_sensor, ...).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
