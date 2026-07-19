"""Calcula o Score interno (0-1000) via regressão logística."""

import joblib

from app.ml.features import FEATURE_NAMES, build_features
from app.ml.train import MODEL_PATH
from app.models.customer import Customer
from app.models.serasa import SerasaQuery

FALLBACK_MODEL_VERSION = "v0-fallback-sem-treino"


class ScoreResult:
    def __init__(self, score: int, default_probability: float, model_version: str, features: dict):
        self.score = score
        self.default_probability = default_probability
        self.model_version = model_version
        self.features = features


def _probability_to_score(probability_of_default: float) -> int:
    """Converte probabilidade de inadimplência em Score na escala 0-1000
    (quanto maior o score, menor o risco)."""
    return round((1 - probability_of_default) * 1000)


def calculate_score(customer: Customer, serasa_query: SerasaQuery | None) -> ScoreResult:
    features = build_features(customer, serasa_query)

    if MODEL_PATH.exists():
        artifact = joblib.load(MODEL_PATH)
        model, scaler, version = artifact["model"], artifact["scaler"], artifact["version"]
        X = [[features[name] for name in FEATURE_NAMES]]
        X_scaled = scaler.transform(X)
        probability_of_default = model.predict_proba(X_scaled)[0][1]
    else:
        # Sem modelo treinado ainda: regra heurística simples como placeholder,
        # para o sistema não ficar bloqueado enquanto o dataset de treino não existe.
        probability_of_default = _heuristic_default_probability(features)
        version = FALLBACK_MODEL_VERSION

    score = _probability_to_score(probability_of_default)
    return ScoreResult(score, probability_of_default, version, features)


def _heuristic_default_probability(features: dict) -> float:
    risk = 0.05
    risk += features["pct_paid_late"] * 0.3
    risk += min(features["avg_days_late"] / 60, 1.0) * 0.2
    risk += 0.25 if features["has_overdue_open_balance"] else 0.0
    risk += min(features["serasa_pefin_count"], 5) * 0.05
    risk += min(features["serasa_protests_count"], 5) * 0.05
    risk += min(features["serasa_lawsuits_count"], 5) * 0.03
    return min(risk, 0.95)
