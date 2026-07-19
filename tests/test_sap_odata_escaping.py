from app.connectors.sap_service_layer import _escape_odata_literal


def test_escape_odata_literal_doubles_single_quotes():
    assert _escape_odata_literal("O'Brien") == "O''Brien"


def test_escape_odata_literal_neutralizes_filter_injection_attempt():
    # Cada aspa simples vira uma aspa dupla ('') — a forma OData de
    # representar uma aspa literal dentro de uma string, em vez de fechar
    # o literal e deixar o restante ser interpretado como sintaxe de filtro.
    malicious = "X' or CardCode eq 'Y"
    escaped = _escape_odata_literal(malicious)

    assert escaped == "X'' or CardCode eq ''Y"
    assert escaped.count("'") == malicious.count("'") * 2


def test_escape_odata_literal_leaves_normal_codes_untouched():
    assert _escape_odata_literal("C10234") == "C10234"
