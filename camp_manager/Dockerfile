FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Create non-root application user -> Security before execution -> Docker security + TLS 

RUN groupadd --system appgroup \
    && useradd --system \
        --gid appgroup \
        --create-home \
        appuser


COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt


COPY --chown=appuser:appgroup . .

# Run the application as not root user

USER appuser

STOPSIGNAL SIGTERM

CMD ["python", "src/main.py"]