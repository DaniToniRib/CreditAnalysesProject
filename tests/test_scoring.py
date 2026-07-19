from app.models.customer import Customer
from app.services.scoring import FALLBACK_MODEL_VERSION, calculate_score


def test_calculate_score_uses_heuristic_fallback_when_no_model_trained():
    customer = Customer(sap_card_code="C001", name="Cliente Teste")

    result = calculate_score(customer, None)

    assert result.model_version == FALLBACK_MODEL_VERSION
    assert 0 <= result.score <= 1000
