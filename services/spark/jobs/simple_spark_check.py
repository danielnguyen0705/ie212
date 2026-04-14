from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("ie212-spark-check")
    .getOrCreate()
)

data = [
    ("AAPL", 210.15),
    ("MSFT", 438.20),
    ("AMD", 167.05),
]

df = spark.createDataFrame(data, ["symbol", "price"])

print("=== Spark DataFrame ===")
df.show()

print("=== Row count ===")
print(df.count())

spark.stop()