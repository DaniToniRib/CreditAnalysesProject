"""Script de treino do modelo de Score (regressão logística).

Uso: python -m app.ml.train

Requer um dataset histórico com uma linha por cliente/período, contendo as
mesmas colunas de `FEATURE_NAMES` e uma coluna alvo `inadimplente`
(1 = ficou inadimplente no período seguinte, 0 = não). Esse dataset ainda
precisa ser levantado a partir do histórico real de pagamentos — ver
pendência no README.
"""

import argparse

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.ml.artifacts import ARTIFACT_DIR, MODEL_PATH, MODEL_VERSION
from app.ml.features import FEATURE_NAMES


def train(dataset_path: str) -> None:
    df = pd.read_csv(dataset_path)
    X = df[FEATURE_NAMES]
    y = df["inadimplente"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    print(classification_report(y_test, y_pred))
    print("AUC:", roc_auc_score(y_test, y_proba))

    ARTIFACT_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler, "version": MODEL_VERSION}, MODEL_PATH)
    print(f"Modelo salvo em {MODEL_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_path", help="CSV com histórico de clientes + coluna 'inadimplente'")
    args = parser.parse_args()
    train(args.dataset_path)
