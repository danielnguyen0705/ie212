from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StringType, DoubleType

spark = (
    SparkSession.builder
    .appName("ie212-write-kafka-stream-to-postgres")
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
    .option("startingOffsets", "latest")
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

def write_batch_to_postgres(batch_df, batch_id):
    if batch_df.isEmpty():
        print(f"Batch {batch_id}: empty, skip.")
        return

    out_df = batch_df.withColumn("ingested_at", current_timestamp())

    (
        out_df.write
        .format("jdbc")
        .option("url", "jdbc:postgresql://postgres:5432/stock_project")
        .option("dbtable", "stock.kafka_ticks")
        .option("user", "stock_user")
        .option("password", "change_me_postgres")
        .option("driver", "org.postgresql.Driver")
        .mode("append")
        .save()
    )

    print(f"Batch {batch_id}: wrote {out_df.count()} rows to PostgreSQL.")

query = (
    df_parsed.writeStream
    .foreachBatch(write_batch_to_postgres)
    .outputMode("append")
    .option("checkpointLocation", "/opt/spark/work-dir/checkpoints/write_kafka_stream_to_postgres")
    .start()
)

query.awaitTermination()