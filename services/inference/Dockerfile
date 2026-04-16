FROM python:3.11-slim

WORKDIR /workspace

COPY services/inference/requirements.infer.txt /tmp/requirements.infer.txt

RUN pip install --no-cache-dir -r /tmp/requirements.infer.txt && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

CMD ["tail", "-f", "/dev/null"]