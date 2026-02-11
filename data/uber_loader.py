"""
Loader for Uber receipt PDF (recibo).
Extracts key fields from text for reporting.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Dict, List, Optional
import os
from pypdf import PdfReader


def _norm_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.replace("\ufffd", "")
    value = value.lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _clean_text(value: str) -> str:
    text = str(value or "")
    text = text.replace("\ufffd", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_currency(text: str) -> Optional[float]:
    if text is None:
        return None
    s = str(text)
    s = s.replace("\ufffd", "")
    s = re.sub(r"[^0-9,.-]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _extract_currency_from_line(line: str) -> Optional[float]:
    match = re.search(r"-?R\$\s*([0-9.,]+)", line)
    if match:
        return _parse_currency(match.group(1))
    return _parse_currency(line)


def _find_value_after_keyword(lines: List[str], key: str) -> Optional[float]:
    for i, line in enumerate(lines):
        if key in _norm_text(line):
            value = _extract_currency_from_line(line)
            if value is not None:
                return value
            if i + 1 < len(lines):
                value = _extract_currency_from_line(lines[i + 1])
                if value is not None:
                    return value
    return None


def _parse_date_pt(date_text: str) -> Optional[str]:
    """Return date as YYYYMMDD if possible."""
    months = {
        "jan": "01",
        "fev": "02",
        "mar": "03",
        "abr": "04",
        "mai": "05",
        "jun": "06",
        "jul": "07",
        "ago": "08",
        "set": "09",
        "out": "10",
        "nov": "11",
        "dez": "12",
    }
    m = re.match(r"(\d{1,2}) de ([a-zA-Z\.]+) de (\d{4})", date_text)
    if not m:
        return None
    day = m.group(1).zfill(2)
    mon_raw = m.group(2).strip(".")
    mon = months.get(mon_raw[:3].lower())
    if not mon:
        return None
    year = m.group(3)
    return f"{year}{mon}{day}"


def carregar_recibo_uber(pdf_path: str) -> Dict:
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    lines = [_clean_text(line) for line in text.splitlines() if _clean_text(line)]

    # Data e hora (topo)
    data_str = None
    hora_str = None
    for i, line in enumerate(lines):
        if re.match(r"^\d{1,2} de ", _norm_text(line)) and " de " in _norm_text(line):
            data_str = _clean_text(line)
            if i + 1 < len(lines) and re.match(r"^\d{1,2}:\d{2}$", lines[i + 1]):
                hora_str = _clean_text(lines[i + 1])
            break

    # Totais e itens
    total = _find_value_after_keyword(lines, "total")
    preco_viagem = _find_value_after_keyword(lines, "preco da viagem")
    taxa_inter = _find_value_after_keyword(lines, "taxa de intermediacao")
    custo_fixo = _find_value_after_keyword(lines, "custo fixo")
    promocao = _find_value_after_keyword(lines, "promocao")

    # Pagamentos
    pagamento_linha = None
    for i, line in enumerate(lines):
        if _norm_text(line) == "pagamentos":
            if i + 1 < len(lines):
                pagamento_linha = _clean_text(lines[i + 1])
            break

    # Informacoes da viagem
    categoria = None
    distancia = None
    duracao = None
    for i, line in enumerate(lines):
        if _norm_text(line) == "informacoes da viagem":
            if i + 1 < len(lines):
                categoria = _clean_text(lines[i + 1])
            if i + 2 < len(lines):
                info = lines[i + 2]
                m = re.search(r"([0-9.]+)\s*quilometros,\s*(\d+)\s*minutes", _norm_text(info))
                if m:
                    distancia = m.group(1)
                    duracao = m.group(2)
            break

    # Origem e destino (pegando os dois primeiros horarios apos informacoes da viagem)
    pontos = []
    time_re = re.compile(r"^\d{1,2}:\d{2}$")
    start_idx = 0
    for i, line in enumerate(lines):
        if _norm_text(line) == "informacoes da viagem":
            start_idx = i + 1
            break

    i = start_idx
    while i < len(lines):
        if time_re.match(lines[i]):
            hora = _clean_text(lines[i])
            addr_lines = []
            j = i + 1
            while j < len(lines) and not time_re.match(lines[j]):
                if _norm_text(lines[j]).startswith("voce viajou"):
                    break
                addr_lines.append(_clean_text(lines[j]))
                j += 1
            pontos.append({"hora": hora, "endereco": " ".join(addr_lines).strip()})
            i = j
            if len(pontos) >= 2:
                break
        else:
            i += 1

    return {
        "arquivo": os.path.basename(pdf_path),
        "data_texto": data_str,
        "hora": hora_str,
        "data_yyyymmdd": _parse_date_pt(_norm_text(data_str or "")),
        "total": total,
        "preco_viagem": preco_viagem,
        "taxa_intermediacao": taxa_inter,
        "custo_fixo": custo_fixo,
        "promocao": promocao,
        "pagamento_linha": pagamento_linha,
        "categoria": categoria,
        "distancia_km": distancia,
        "duracao_min": duracao,
        "origem": pontos[0] if len(pontos) > 0 else None,
        "destino": pontos[1] if len(pontos) > 1 else None,
    }


def carregar_recibos_pasta(pasta_path: str) -> List[Dict]:
    recibos = []
    if not os.path.isdir(pasta_path):
        return recibos
    for nome in os.listdir(pasta_path):
        if not nome.lower().endswith(".pdf"):
            continue
        caminho = os.path.join(pasta_path, nome)
        try:
            recibos.append(carregar_recibo_uber(caminho))
        except Exception:
            continue
    return recibos
