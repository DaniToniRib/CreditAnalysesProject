from fastapi import FastAPI

from app.api.routes import customers, dashboard, health, orders
from app.logging_config import configure_logging

configure_logging()

app = FastAPI(
    title="Análise de Crédito de Clientes",
    description="Integração SAP Business One + Serasa Experian para análise e limite de crédito.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(customers.router)
app.include_router(orders.router)
app.include_router(dashboard.router)
