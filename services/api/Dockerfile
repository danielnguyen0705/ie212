FROM python:3.11-slim

WORKDIR /app

COPY services/api/requirements.api.txt /tmp/requirements.api.txt
RUN pip install --no-cache-dir -r /tmp/requirements.api.txt

COPY services/api /app/services/api

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]