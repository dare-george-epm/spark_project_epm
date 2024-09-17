import geohash
from pyspark.sql.functions import col, udf
from pyspark.sql.types import StringType
from my_config import my_config
from myfunctions import (
    add_geohash_column, read_csv_to_df, set_azure_configuration,
    cast_lat_long_to_float, geocode_missing_lat_long, initialize_spark,
    read_parquet_to_df
)

def main():
    # Initializing Spark session
    spark = initialize_spark()

    # Setting Azure configuration
    set_azure_configuration(
        spark,
        my_config.azure_storage_account,
        my_config.azure_client_id,
        my_config.azure_client_secret,
        my_config.azure_tenant_id
    )

    # Reading and processing hotel data
    df_hotels = read_csv_to_df(spark, my_config.azure_storage_account, my_config.hotels_path)
    df_hotels = df_hotels.sample(my_config.sampling_fraction)
    df_hotels = geocode_missing_lat_long(df_hotels, {my_config.geocode_key})
    df_hotels = cast_lat_long_to_float(df_hotels)
    df_hotels = add_geohash_column(df_hotels)
    df_hotels.show(11)

    # Reading and processing weather data
    df_weather = read_parquet_to_df(spark, my_config.azure_storage_account, my_config.weather_path)
    df_weather = df_weather.sample(my_config.sampling_fraction)

    # UDF to generate geohash from latitude and longitude
    geohash_udf = udf(lambda lat, lon: geohash.encode(lat, lon, precision=4), StringType())
    df_weather = df_weather.withColumn("Geohash", geohash_udf(col("lat"), col("lng")))
    df_weather = df_weather.dropDuplicates(["Geohash"])

    # Joining hotels and weather data on Geohash
    df_combined = df_hotels.join(df_weather, on="Geohash", how="left")

    # Displaying sample result
    # df_combined.show(10)

    # Writing the combined DataFrame to Azure storage
    output_path = f"abfss://{my_config.storage_container}@{my_config.azure_storage_account}.dfs.core.windows.net/{my_config.azure_storage_account}"
    df_combined.write.mode("overwrite").parquet(output_path)

    # Reading the combined DataFrame back from storage and display
    read_df_combined = spark.read.parquet(output_path)
    read_df_combined.show(11)

    # Stop the Spark session
    spark.stop()

if __name__ == "__main__":
    main()