from opencage.geocoder import OpenCageGeocode
import geohash
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when
from pyspark.sql.types import StringType
from pyspark.sql.functions import udf

def initialize_spark(app_name="SimpleApp", executor_memory="1g", driver_memory="1g"):
    """Initializes and returns a Spark session."""
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.executor.memory", executor_memory) \
        .config("spark.driver.memory", driver_memory) \
        .config("spark.executor.cores", "2") \
        .config("spark.sql.shuffle.partitions", "200") \
        .config("spark.sql.broadcastTimeout", "600") \
        .config("spark.sql.autoBroadcastJoinThreshold", "-1")\
    .getOrCreate()
    return spark

def set_azure_configuration(spark, azure_acc, azure_client_id, azure_client_secret, azure_tenant_id):
    """Sets the Azure configurations for Spark."""
    spark.conf.set(f"fs.azure.account.auth.type.{azure_acc}.dfs.core.windows.net", "OAuth")
    spark.conf.set(f"fs.azure.account.oauth.provider.type.{azure_acc}.dfs.core.windows.net",
                   "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
    spark.conf.set(f"fs.azure.account.oauth2.client.id.{azure_acc}.dfs.core.windows.net", azure_client_id)
    spark.conf.set(f"fs.azure.account.oauth2.client.secret.{azure_acc}.dfs.core.windows.net", azure_client_secret)
    spark.conf.set(f"fs.azure.account.oauth2.client.endpoint.{azure_acc}.dfs.core.windows.net",
                   f"https://login.microsoftonline.com/{azure_tenant_id}/oauth2/token")

def read_csv_to_df(spark, azure_acc, file_path):
    """Reads the CSV file from Azure Data Lake into a Spark DataFrame."""
    df = spark.read.csv(
        f"abfss://mydataengcontainer@{azure_acc}.dfs.core.windows.net/{file_path}",
        inferSchema=True,
        header=True)
    return df.dropDuplicates(subset=["Id", "Name"])

def read_parquet_to_df(spark, azure_acc, file_path, infer_schema=True):
    """Reads parquet files from Azure Data Lake into a Spark DataFrame."""
    df = spark.read.format("parquet") \
        .option("inferSchema", str(infer_schema).lower()) \
        .option("recursiveFileLookup", "true") \
        .load(f"abfss://mydataengcontainer@{azure_acc}.dfs.core.windows.net/{file_path}")

    return df.dropDuplicates()

def geocode_missing_lat_long(df, geocoder_key):
    """Fills missing Latitude and Longitude in the DataFrame using OpenCageGeocode."""
    geocoder = OpenCageGeocode(geocoder_key)

    rows = df.filter((df.Latitude.isNull()) | (df.Latitude == "NA") |
                     (df.Longitude.isNull()) | (df.Longitude == "NA")).collect()

    for row in rows:
        address = f"{row['Address']}, {row['City']}, {row['Country']}"
        result = geocoder.geocode(address)

        if result and 'geometry' in result[0]:
            geometry = result[0]['geometry']
            df = df.withColumn('Latitude', when((df['Address'] == row['Address']) &
                                                ((df['Latitude'].isNull()) | (df['Latitude'] == "NA")),
                                                geometry['lat']).otherwise(df['Latitude']))
            df = df.withColumn('Longitude', when((df['Address'] == row['Address']) &
                                                 ((df['Longitude'].isNull()) | (df['Longitude'] == "NA")),
                                                 geometry['lng']).otherwise(df['Longitude']))
    return df

def cast_lat_long_to_float(df):
    """Casts Latitude and Longitude columns to float type."""
    df = df.withColumn("Latitude", col("Latitude").cast("float"))
    df = df.withColumn("Longitude", col("Longitude").cast("float"))
    return df

def add_geohash_column(df, lat_col="Latitude", lon_col="Longitude", precision=4):
    geohash_udf = udf(lambda lat, lon: geohash.encode(lat, lon, precision), StringType())
    return df.withColumn("Geohash", geohash_udf(col(lat_col), col(lon_col)))

# .config("spark.jars.packages", "org.apache.hadoop:hadoop-azure:3.3.4,com.microsoft.azure:azure-storage:8.6.6") \