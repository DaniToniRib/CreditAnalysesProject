from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco de dados próprio
    db_server: str
    db_port: int = 1433
    db_name: str
    db_user: str
    db_password: str
    db_driver: str = "ODBC Driver 18 for SQL Server"

    # SAP Business One Service Layer
    sap_service_layer_url: str
    sap_company_db: str
    sap_username: str
    sap_password: str
    sap_verify_ssl: bool = True

    # Serasa Experian API
    serasa_api_url: str
    serasa_client_id: str
    serasa_client_secret: str
    serasa_query_cache_ttl_hours: int = 24

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str

    # Chave usada por integrações (SAP, sistemas internos) para chamar a API
    # via header `X-API-Key`
    api_key: str

    @property
    def sqlalchemy_database_uri(self) -> str:
        driver = self.db_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://{self.db_user}:{self.db_password}"
            f"@{self.db_server}:{self.db_port}/{self.db_name}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
