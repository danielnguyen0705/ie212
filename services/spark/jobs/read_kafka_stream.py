from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, DoubleType

spark = (
    SparkSession.builder
    .appName("ie212-read-kafka-stream")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

json_schema = (
    StructType()
    .add("symbol", StringType(), True)
    .add("price", DoubleType(), True)
)

df_raw = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:9092")
    .option("subscribe", "stock-price")
    .option("startingOffsets", "earliest")
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
        col("partition"),
        col("offset"),
        col("timestamp")
    )
)

query = (
    df_parsed.writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", False)
    .option("numRows", 50)
    .start()
)

query.awaitTermination()