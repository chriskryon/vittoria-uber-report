"""
Entry point for Uber receipt report generation.
"""

from datetime import datetime
from data.uber_loader import carregar_recibos_pasta
from pdf.uber_builder import criar_relatorio_uber

PASTA_RECIBOS = "uber"


def main():
    print("=" * 50)
    print("Relatorio UBER - Banco Vittoria")
    print("=" * 50)

    recibos = carregar_recibos_pasta(PASTA_RECIBOS)
    if not recibos:
        print(f"Nenhum recibo encontrado em {PASTA_RECIBOS}")
        return

    data_yyyymmdd = datetime.now().strftime("%Y%m%d")
    arquivo_saida = f"Relatorio UBER - {data_yyyymmdd}.pdf"

    criar_relatorio_uber(recibos, arquivo_saida)

    print("\n" + "=" * 50)
    print(f"OK PDF gerado: {arquivo_saida}")
    print("=" * 50)


if __name__ == "__main__":
    main()
