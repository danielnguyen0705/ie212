FROM apache/airflow:3.2.0-python3.12

USER root

RUN apt-get -o Acquire::Retries=5 -o Acquire::ForceIPv4=true update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow