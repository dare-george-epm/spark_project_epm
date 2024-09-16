from pydantic import BaseSettings

class Settings(BaseSettings):
    SPARK_MASTER: str
    azure_storage_account: str
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    storage_container: str
    geocode_key: str
    output_file_path: str
    sampling_fraction: float
    hotels_path: str
    weather_path: str

    class Config:
        env_file = ".env"  # Optional for local development, not required in GitLab
        case_sensitive = True

# Instantiate the settings object
my_config = Settings()
