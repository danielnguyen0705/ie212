from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, DoubleType

# Tạo SparkSession
spark = (
    SparkSession.builder
    .appName("ie212-read-kafka-batch")
    .getOrCreate()
)

# Đọc dữ liệu batch từ Kafka topic stock-price
# Vì Spark đang chạy trong Docker network, broker sẽ là kafka:9092
df_raw = (
    spark.read
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:9092")
    .option("subscribe", "stock-price")
    .option("startingOffsets", "earliest")
    .option("endingOffsets", "latest")
    .load()
)

print("=== Schema gốc từ Kafka ===")
df_raw.printSchema()

print("=== Dữ liệu raw ===")
df_raw.selectExpr(
    "CAST(key AS STRING) AS key",
    "CAST(value AS STRING) AS value",
    "topic",
    "partition",
    "offset",
    "timestamp"
).show(truncate=False)

# Parse JSON trong cột value
json_schema = (
    StructType()
    .add("symbol", StringType(), True)
    .add("price", DoubleType(), True)
)

df_parsed = (
    df_raw
    .selectExpr("CAST(value AS STRING) AS value_str", "topic", "partition", "offset", "timestamp")
    .withColumn("json_data", from_json(col("value_str"), json_schema))
    .select(
        col("json_data.symbol").alias("symbol"),
        col("json_data.price").alias("price"),
        col("topic"),
        col("partition"),
        col("offset"),
        col("timestamp")
    )
)

print("=== Dữ liệu đã parse JSON ===")
df_parsed.show(truncate=False)

print("=== Row count ===")
print(df_parsed.count())

spark.stop()