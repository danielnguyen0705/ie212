#!/usr/bin/env bash
set -euo pipefail

KAFKA_CONTAINER="${KAFKA_CONTAINER:-ie212-kafka}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-localhost:9092}"
TOPIC="${TOPIC:-stock-price}"
GROUP="${GROUP:-}"

echo "Kafka container: ${KAFKA_CONTAINER}"
echo "Topic: ${TOPIC}"
echo "Log end offsets:"
docker exec "${KAFKA_CONTAINER}" /opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --bootstrap-server "${BOOTSTRAP_SERVER}" \
  --topic "${TOPIC}" \
  --time -1

if [ -n "${GROUP}" ]; then
  echo "Consumer group lag for ${GROUP}:"
  docker exec "${KAFKA_CONTAINER}" /opt/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --describe \
    --group "${GROUP}"
else
  echo "No GROUP provided. Spark batch jobs in this project read explicit earliest/latest offsets, so no stable Kafka consumer group lag exists by default."
  echo "Set GROUP=<consumer-group> to check a registered consumer group."
fi
