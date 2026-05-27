FROM python:3.11-slim

WORKDIR /workspace

COPY services/producer/requirements.producer.txt /tmp/requirements.producer.txt

RUN pip install --no-cache-dir -r /tmp/requirements.producer.txt

CMD ["python", "scripts/publish_stock_ticks.py"]
