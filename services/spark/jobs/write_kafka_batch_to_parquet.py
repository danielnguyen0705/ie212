from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, DoubleType

spark = (
    SparkSession.builder
    .appName("ie212-write-kafka-batch-to-parquet")
    .getOrCreate()
)

json_schema = (
    StructType()
    .add("symbol", StringType(), True)
    .add("price", DoubleType(), True)
)

df_raw = (
    spark.read
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:9092")
    .option("subscribe", "stock-price")
    .option("startingOffsets", "earliest")
    .option("endingOffsets", "latest")
    .load()
)

df_parsed = (
    df_raw
    .selectExpr(
        "CAST(value AS STRING) AS value_str",
        "topic",
        "partition",
        "offset",
        "timestamp"
    )
    .withColumn("json_data", from_json(col("value_str"), json_schema))
    .select(
        col("json_data.symbol").alias("symbol"),
        col("json_data.price").alias("price"),
        col("topic"),
        col("partition").alias("partition_id"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("event_time")
    )
    .filter(col("symbol").isNotNull() & col("price").isNotNull())
)

print("=== Parsed Data ===")
df_parsed.show(truncate=False)

print("=== Row count ===")
print(df_parsed.count())

(
    df_parsed
    .coalesce(1)
    .write
    .mode("overwrite")
    .parquet("/opt/spark/out/kafka_ticks_parquet")
)

print("=== Wrote parquet to /opt/spark/out/kafka_ticks_parquet ===")

spark.stop()