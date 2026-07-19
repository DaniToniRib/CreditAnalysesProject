"""Localização/versão do modelo treinado — separado de `train.py` para que o
caminho de scoring em produção (`app/services/scoring.py`) não precise
importar `pandas`/`scikit-learn` só para resolver uma constante."""

from pathlib import Path

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "credit_score_model.joblib"
MODEL_VERSION = "v0-skeleton"
