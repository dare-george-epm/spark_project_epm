from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, DoubleType
import uuid
from unittest.mock import patch
import pytest
from src.main.myfunctions import (initialize_spark, read_csv_to_df, cast_lat_long_to_float,
                                  add_geohash_column, set_azure_configuration, geocode_missing_lat_long)


# Fixture for creating and tearing down a Spark session for tests
@pytest.fixture(scope="session")
def spark():
    spark_session = initialize_spark(app_name="TestSparkApp")
    yield spark_session
    spark_session.stop()


# Test Spark session initialization
def test_initialize_spark():
    spark = initialize_spark(app_name="TestSparkApp")
    assert isinstance(spark, SparkSession), "Spark session should be of type SparkSession"
    assert spark.sparkContext is not None, "SparkContext should be initialized"


# Test setting Azure configuration in Spark
def test_set_azure_configuration(spark):
    set_azure_configuration(spark, "test_acc", "test_client_id", "test_client_secret", "test_tenant_id")
    assert spark.conf.get("fs.azure.account.auth.type.test_acc.dfs.core.windows.net") == "OAuth"


# Test casting latitude and longitude columns to float
def test_cast_lat_long_to_float(spark):
    data = [(1, "52.5200", "13.4050"), (2, "48.8566", "2.3522")]
    df = spark.createDataFrame(data, ["Id", "Latitude", "Longitude"])
    df_casted = cast_lat_long_to_float(df)
    assert df_casted.schema["Latitude"].dataType.typeName() == "float", "Latitude should be casted to float"
    assert df_casted.schema["Longitude"].dataType.typeName() == "float", "Longitude should be casted to float"


# Sample data for testing CSV reading
SAMPLE_DATA = "id,name\n1,Alice\n2,Bob"


# Fixture for initializing a Spark session for CSV tests
@pytest.fixture(scope="module")
def spark_csv():
    spark_session = SparkSession.builder.appName("test_read_csv").getOrCreate()
    yield spark_session
    spark_session.stop()


# Function to read a CSV file into a Spark DataFrame
def read_csv_to_df(spark, file_path, header=True):
    return spark.read.csv(file_path, header=header)


# Test reading a CSV into a DataFrame and checking the schema and data
def test_read_csv_to_df(spark_csv):
    csv_string = f"data_{uuid.uuid4()}.csv"
    spark_csv.sparkContext.parallelize([SAMPLE_DATA]).saveAsTextFile(csv_string)

    df = read_csv_to_df(spark_csv, csv_string)

    assert df.schema.fieldNames() == ["id", "name"], "Schema should match the expected fields"
    assert df.count() == 2, "DataFrame should contain two rows"
    assert int(df.collect()[0]["id"]) == 1, "First row ID should be 1"
    assert df.collect()[1]["name"] == "Bob", "Second row name should be Bob"


# Test for the geocode_missing_lat_long function
@patch("src.main.myfunctions.OpenCageGeocode.geocode")
def test_geocode_missing_lat_long(mock_geocode, spark):
    """Test geocode_missing_lat_long function by mocking OpenCage API response."""

    # Mock OpenCage API response: return result for the first row, and no result for the second row
    def mock_geocode_func(address):
        if "Eiffel Tower" in address:
            return [{
                'geometry': {
                    'lat': 48.8588443,
                    'lng': 2.2943506
                }
            }]
        else:
            return []  # No geocode result for the second row

    mock_geocode.side_effect = mock_geocode_func

    # Define schema for the DataFrame
    schema = StructType([
        StructField("Id", IntegerType(), True),
        StructField("Address", StringType(), True),
        StructField("City", StringType(), True),
        StructField("Country", StringType(), True),
        StructField("Latitude", DoubleType(), True),
        StructField("Longitude", DoubleType(), True)
    ])

    # Create sample data with missing Latitude and Longitude
    data = [(1, "Eiffel Tower", "Paris", "France", None, None),
            (2, "Colosseum", "Rome", "Italy", None, None)]

    # Create DataFrame using explicit schema
    df = spark.createDataFrame(data, schema=schema)

    # Call the function to test
    df_geocoded = geocode_missing_lat_long(df, "fake-api-key")

    # Verify the mock was called
    mock_geocode.assert_called()

    # Collect results
    result = df_geocoded.collect()

    # Assert that Latitude and Longitude are filled in for the first row
    assert result[0]["Latitude"] == 48.8588443, "Latitude should be filled with geocoded value for the first row"
    assert result[0]["Longitude"] == 2.2943506, "Longitude should be filled with geocoded value for the first row"

    # Ensure the second row still has None for Latitude and Longitude
    assert result[1]["Latitude"] is None, "Second row should still have missing Latitude"
    assert result[1]["Longitude"] is None, "Second row should still have missing Longitude"

    print(df_geocoded.show())

# Test adding a Geohash column to the DataFrame
def test_add_geohash_column(spark):
    data = [(52.5200, 13.4050), (48.8566, 2.3522)]
    df = spark.createDataFrame(data, ["Latitude", "Longitude"])
    df_with_geohash = add_geohash_column(df)
    assert "Geohash" in df_with_geohash.columns, "Geohash column should be added"
    assert df_with_geohash.count() == 2, "DataFrame should still contain the same number of rows"
    assert df_with_geohash.select("Geohash").distinct().count() == 2, "Geohash values should be distinct"

    print(df_with_geohash.show())

