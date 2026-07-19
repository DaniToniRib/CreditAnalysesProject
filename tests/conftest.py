import os

# Valores dummy para satisfazer app.config.Settings em ambiente de teste,
# sem depender de um .env real (nenhuma conexão de rede é feita nos testes).
os.environ.setdefault("DB_SERVER", "localhost")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("SAP_SERVICE_LAYER_URL", "https://sap.local/b1s/v1")
os.environ.setdefault("SAP_COMPANY_DB", "TEST")
os.environ.setdefault("SAP_USERNAME", "test")
os.environ.setdefault("SAP_PASSWORD", "test")
os.environ.setdefault("SERASA_API_URL", "https://serasa.local")
os.environ.setdefault("SERASA_CLIENT_ID", "test")
os.environ.setdefault("SERASA_CLIENT_SECRET", "test")
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("API_KEY", "test")
