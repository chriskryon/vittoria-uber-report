"""
PDF builder for Uber receipt summary.
"""

from __future__ import annotations
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from svglib.svglib import svg2rlg


def _fmt_currency(value) -> str:
    if value is None:
        return "-"
    try:
        v = float(value)
    except Exception:
        return "-"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sort_key(recibo: dict) -> str:
    data = recibo.get("data_yyyymmdd") or "00000000"
    hora = recibo.get("hora") or "00:00"
    return f"{data}_{hora}"


def _fmt_date_range(recibos: list[dict]) -> str:
    datas = [r.get("data_yyyymmdd") for r in recibos if r.get("data_yyyymmdd")]
    if not datas:
        return "-"
    datas_sorted = sorted(datas)
    start = datas_sorted[0]
    end = datas_sorted[-1]
    def _to_br(d: str) -> str:
        if len(d) != 8:
            return d
        return f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
    return f"{_to_br(start)}–{_to_br(end)}"


def _date_from_yyyymmdd(value: str) -> datetime | None:
    if not value or len(value) != 8:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d")
    except Exception:
        return None


def criar_relatorio_uber(recibos: list[dict], arquivo_saida: str) -> None:
    doc = SimpleDocTemplate(
        arquivo_saida,
        pagesize=A4,
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Relatório de Reembolso - Uber",
        author="Banco Vittoria",
    )

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "Titulo",
        parent=estilos["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor("#1F2A37"),
    )
    normal = ParagraphStyle(
        "Normal",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#111827"),
    )
    meta = ParagraphStyle(
        "Meta",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        textColor=colors.HexColor("#4B5563"),
    )
    resumo = ParagraphStyle(
        "Resumo",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#111827"),
        alignment=1,
    )
    separator = ParagraphStyle(
        "Separator",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=colors.HexColor("#D1D5DB"),
    )

    elementos = []
    # Logo (opcional)
    logo_path = "assets/logo.svg"
    if os.path.exists(logo_path):
        try:
            drawing = svg2rlg(logo_path)
            scale = 2 * cm / drawing.height
            drawing.width = drawing.width * scale
            drawing.height = 2 * cm
            drawing.scale(scale, scale)
            drawing.hAlign = "CENTER"
            elementos.append(drawing)
            elementos.append(Spacer(1, 0.3 * cm))
        except Exception:
            elementos.append(Spacer(1, 0.5 * cm))
    else:
        elementos.append(Spacer(1, 0.5 * cm))

    elementos.append(Paragraph("Relatório de Reembolso - Uber", titulo))
    elementos.append(Spacer(1, 0.3 * cm))
    recibos_ordenados = sorted(recibos, key=_sort_key)
    total_viagens = len(recibos_ordenados)
    total_valor = sum((r.get("total") or 0.0) for r in recibos_ordenados)

    # Sumario compacto
    resumo_tabela = Table(
        [[f"{total_viagens} viagens", f"Total {_fmt_currency(total_valor)}"]],
        colWidths=[5.5 * cm, 7.0 * cm],
    )
    resumo_tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2F7")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    resumo_tabela.hAlign = "CENTER"
    periodo = _fmt_date_range(recibos_ordenados)
    elementos.append(Paragraph("Resumo geral", resumo))
    elementos.append(Spacer(1, 0.15 * cm))
    elementos.append(resumo_tabela)
    elementos.append(Spacer(1, 0.15 * cm))
    elementos.append(Paragraph(f"Período: {periodo}", meta))
    elementos.append(Spacer(1, 0.25 * cm))

    # Estatisticas por mes e semana
    month_totals = {}
    week_totals = {}
    for r in recibos_ordenados:
        d = _date_from_yyyymmdd(r.get("data_yyyymmdd"))
        if not d:
            continue
        month_key = d.strftime("%m/%Y")
        total = float(r.get("total") or 0.0)
        month_totals[month_key] = month_totals.get(month_key, 0.0) + total
        week_idx = ((d.day - 1) // 7) + 1
        week_key = f"{month_key} • Semana {week_idx}"
        week_totals[week_key] = week_totals.get(week_key, 0.0) + total

    if month_totals:
        elementos.append(Spacer(1, 0.15 * cm))
        elementos.append(Paragraph("Totais por mês", meta))
        month_rows = [["Mês", "Total"]]
        for mes in sorted(month_totals.keys()):
            month_rows.append([mes, _fmt_currency(month_totals[mes])])
        tabela_mes = Table(month_rows, colWidths=[4.0 * cm, 4.5 * cm])
        tabela_mes.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementos.append(tabela_mes)

    if week_totals:
        elementos.append(Spacer(1, 0.2 * cm))
        elementos.append(Paragraph("Totais por semana (do mês)", meta))
        week_rows = [["Mês/Semana", "Total"]]
        for semana in sorted(week_totals.keys()):
            week_rows.append([semana, _fmt_currency(week_totals[semana])])
        tabela_semana = Table(week_rows, colWidths=[6.2 * cm, 2.3 * cm])
        tabela_semana.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementos.append(tabela_semana)

    elementos.append(Spacer(1, 0.35 * cm))

    for recibo in recibos_ordenados:
        data_txt = recibo.get("data_texto") or "-"
        hora_txt = recibo.get("hora") or "-"
        total_txt = _fmt_currency(recibo.get("total"))
        elementos.append(Paragraph(f"{data_txt} {hora_txt} • Total {total_txt}", normal))
        elementos.append(Spacer(1, 0.1 * cm))

        preco = _fmt_currency(recibo.get("preco_viagem"))
        taxa = _fmt_currency(recibo.get("taxa_intermediacao"))
        custo = _fmt_currency(recibo.get("custo_fixo"))
        promo_val = recibo.get("promocao")
        promo_fmt = _fmt_currency(promo_val)
        if promo_fmt != "-" and not str(promo_fmt).startswith("-"):
            promo_fmt = f"-{promo_fmt}"
        pagamento = recibo.get("pagamento_linha") or "-"

        elementos.append(Paragraph(f"Preço: {preco} • Taxa: {taxa} • Custo: {custo}", meta))
        elementos.append(Paragraph(f"Promoção: {promo_fmt} • Pagamento: {pagamento}", meta))
        elementos.append(Spacer(1, 0.16 * cm))

        categoria = recibo.get("categoria") or "-"
        distancia = recibo.get("distancia_km") or "-"
        duracao = recibo.get("duracao_min") or "-"
        origem = recibo.get("origem") or {}
        destino = recibo.get("destino") or {}

        viagem_info = f"{categoria} • {distancia} km • {duracao} minutos"
        elementos.append(Paragraph(viagem_info, meta))
        elementos.append(Paragraph(f"Origem ({origem.get('hora','-')}): {origem.get('endereco','-')}", meta))
        elementos.append(Paragraph(f"Destino ({destino.get('hora','-')}): {destino.get('endereco','-')}", meta))
        elementos.append(Spacer(1, 0.16 * cm))

        elementos.append(Paragraph("-" * 100, separator))
        elementos.append(Spacer(1, 0.22 * cm))

    doc.build(elementos)
