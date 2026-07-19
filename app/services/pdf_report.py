"""Relatório em PDF com histórico financeiro e evolução do Score do cliente.

Pensado para casos em que a análise de crédito precisa ser compartilhada
com outras partes (diretoria, jurídico, o próprio cliente em negociação)
fora do painel do sistema.
"""

from datetime import date, datetime, timedelta
from io import BytesIO

from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.customer import Customer
from app.services.financial_summary import (
    FinancialSummary,
    ScoreTrend,
    summarize_financial_history,
    summarize_score_trend,
)

DEFAULT_PERIOD_MONTHS = 12

_TREND_LABELS = {
    "melhora": "Melhora",
    "piora": "Piora",
    "estavel": "Estável",
    "sem_historico_suficiente": "Histórico insuficiente",
}


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _days(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f} dias"


def _build_score_chart(trend: ScoreTrend) -> Drawing | None:
    if len(trend.points) < 2:
        return None

    drawing = Drawing(440, 160)
    chart = HorizontalLineChart()
    chart.x = 35
    chart.y = 25
    chart.width = 390
    chart.height = 115
    chart.data = [[p.score for p in trend.points]]
    chart.categoryAxis.categoryNames = [
        p.computed_at.strftime("%d/%m/%y") for p in trend.points
    ]
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.dy = -8
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 1000
    chart.valueAxis.valueStep = 250
    chart.lines[0].strokeColor = colors.HexColor("#1a4dab")
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = None
    drawing.add(chart)
    return drawing


def _financial_summary_table(summary: FinancialSummary) -> Table:
    data = [
        ["Categoria", "Qtde", "Valor total", "Atraso médio"],
        [
            "Pago no vencimento",
            str(summary.paid_on_time_count),
            _money(summary.paid_on_time_amount),
            "—",
        ],
        [
            "Pago em atraso",
            str(summary.paid_late_count),
            _money(summary.paid_late_amount),
            _days(summary.avg_days_late_paid),
        ],
        [
            "Em aberto dentro do prazo",
            str(summary.open_on_time_count),
            _money(summary.open_on_time_amount),
            "—",
        ],
        [
            "Em aberto vencido",
            str(summary.open_overdue_count),
            _money(summary.open_overdue_amount),
            _days(summary.avg_days_late_open),
        ],
        [
            "Total",
            str(summary.total_count),
            _money(summary.total_amount),
            "",
        ],
    ]
    table = Table(data, colWidths=[6.5 * cm, 2 * cm, 3.5 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    return table


def _score_history_table(trend: ScoreTrend) -> Table:
    data = [["Data", "Score", "Variação"]]
    previous: int | None = None
    for point in trend.points:
        variation = "—" if previous is None else f"{point.score - previous:+d}"
        data.append([point.computed_at.strftime("%d/%m/%Y %H:%M"), str(point.score), variation])
        previous = point.score

    table = Table(data, colWidths=[5 * cm, 2.5 * cm, 2.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    return table


def _financial_detail_table(records: list) -> Table:
    data = [["Doc", "Emissão", "Vencimento", "Pagamento", "Valor", "Status", "Atraso"]]
    for r in sorted(records, key=lambda r: r.due_date, reverse=True):
        data.append(
            [
                r.sap_doc_num or "—",
                r.issue_date.strftime("%d/%m/%Y"),
                r.due_date.strftime("%d/%m/%Y"),
                r.payment_date.strftime("%d/%m/%Y") if r.payment_date else "—",
                _money(float(r.amount)),
                r.status.value.replace("_", " "),
                str(r.days_late) if r.days_late else "—",
            ]
        )

    table = Table(
        data,
        colWidths=[2 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2.7 * cm, 3.5 * cm, 1.9 * cm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                ("ALIGN", (4, 0), (4, -1), "RIGHT"),
            ]
        )
    )
    return table


def generate_customer_report_pdf(customer: Customer, months: int = DEFAULT_PERIOD_MONTHS) -> bytes:
    since = date.today() - timedelta(days=months * 30)

    records = [r for r in customer.financial_records if r.due_date >= since]
    financial_summary = summarize_financial_history(records)

    score_points_in_period = [
        s for s in customer.score_history if s.computed_at.date() >= since
    ]
    trend = summarize_score_trend(score_points_in_period)

    latest_score = max(customer.score_history, key=lambda s: s.computed_at, default=None)
    latest_limit = max(customer.credit_limit_history, key=lambda c: c.computed_at, default=None)
    latest_serasa = max(customer.serasa_queries, key=lambda q: q.queried_at, default=None)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=16, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"], fontSize=9, textColor=colors.grey
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=14,
        spaceAfter=6,
    )

    elements = [
        Paragraph(f"Relatório de Análise de Crédito — {customer.name}", title_style),
        Paragraph(
            f"Código SAP: {customer.sap_card_code} | CNPJ/CPF: {customer.cnpj_cpf or '—'} | "
            f"Emitido em {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
            f"Período analisado: últimos {months} meses",
            subtitle_style,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("Resumo atual", heading_style),
        Table(
            [
                ["Score interno", str(latest_score.score) if latest_score else "—"],
                [
                    "Tendência do Score no período",
                    f"{_TREND_LABELS[trend.direction]}"
                    + (f" ({trend.delta:+d} pontos)" if trend.delta is not None else ""),
                ],
                [
                    "Limite de crédito calculado",
                    _money(float(latest_limit.calculated_limit)) if latest_limit else "—",
                ],
                [
                    "Limite cadastrado no SAP",
                    _money(
                        float(customer.sap_credit_limit)
                        if customer.sap_credit_limit is not None
                        else None
                    ),
                ],
            ],
            colWidths=[7 * cm, 7 * cm],
            style=TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                ]
            ),
        ),
        Paragraph("Histórico financeiro (resumo do período)", heading_style),
        _financial_summary_table(financial_summary),
        Paragraph("Evolução do Score no período", heading_style),
    ]

    chart = _build_score_chart(trend)
    if chart is not None:
        elements.append(chart)
    else:
        elements.append(Paragraph("Histórico insuficiente para gerar gráfico.", styles["Normal"]))

    if trend.points:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(_score_history_table(trend))

    elements.append(Paragraph("Última consulta Serasa", heading_style))
    if latest_serasa:
        elements.append(
            Table(
                [
                    ["Score Serasa", "PEFIN", "REFIN", "Protestos", "Ações judiciais", "Cheques devolvidos"],
                    [
                        str(latest_serasa.score) if latest_serasa.score is not None else "—",
                        f"{latest_serasa.pefin_count} ({_money(float(latest_serasa.pefin_total_amount))})",
                        f"{latest_serasa.refin_count} ({_money(float(latest_serasa.refin_total_amount))})",
                        str(latest_serasa.protests_count),
                        str(latest_serasa.lawsuits_count),
                        str(latest_serasa.checks_returned_count),
                    ],
                ],
                colWidths=[2.3 * cm, 3.2 * cm, 3.2 * cm, 2.5 * cm, 2.9 * cm, 2.9 * cm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                    ]
                ),
            )
        )
        elements.append(
            Paragraph(
                f"Consultado em {latest_serasa.queried_at.strftime('%d/%m/%Y %H:%M')}",
                subtitle_style,
            )
        )
    else:
        elements.append(Paragraph("Nenhuma consulta Serasa registrada.", styles["Normal"]))

    elements.append(Paragraph("Detalhamento dos títulos no período", heading_style))
    if records:
        elements.append(_financial_detail_table(records))
    else:
        elements.append(Paragraph("Nenhum título no período selecionado.", styles["Normal"]))

    elements.append(Spacer(1, 0.6 * cm))
    elements.append(
        Paragraph(
            "Documento de uso interno — gerado automaticamente pelo sistema de "
            "Análise de Crédito. Os valores refletem a última sincronização com "
            "o SAP Business One e a Serasa disponível no momento da emissão.",
            subtitle_style,
        )
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        title=f"Relatorio de Credito - {customer.name}",
    )
    doc.build(elements)
    return buffer.getvalue()
