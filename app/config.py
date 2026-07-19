from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco de dados próprio
    db_server: str
    db_port: int = 1433
    db_name: str
    db_user: str
    db_password: str
    db_driver: str = "ODBC Driver 18 for SQL Server"
    # Em produção, com um certificado válido configurado no SQL Server,
    # trocar para False para que a conexão valide o certificado de verdade
    # (evita ataques man-in-the-middle na conexão com o banco).
    db_trust_server_certificate: bool = True

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

    # Limite de requisições por IP por minuto (todas as rotas, exceto /health)
    rate_limit_per_minute: int = 120

    @property
    def sqlalchemy_database_uri(self) -> URL:
        # Usa URL.create em vez de montar a string manualmente: senhas com
        # caracteres especiais (@, :, /, ?, #) quebrariam (ou, pior,
        # alterariam silenciosamente) uma URL construída por f-string.
        return URL.create(
            "mssql+pyodbc",
            username=self.db_user,
            password=self.db_password,
            host=self.db_server,
            port=self.db_port,
            database=self.db_name,
            query={
                "driver": self.db_driver,
                "TrustServerCertificate": "yes" if self.db_trust_server_certificate else "no",
            },
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
