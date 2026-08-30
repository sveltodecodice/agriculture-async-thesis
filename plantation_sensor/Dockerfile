FROM python:3.11-slim

WORKDIR /app

# Copy dependencies first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Ensure core module imports resolve properly
ENV PYTHONPATH=/app

CMD ["python", "main.py"]