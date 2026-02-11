# Relatorio Uber

## Como executar
1) Coloque os PDFs dos recibos na pasta `uber/` (na raiz do projeto).
2) Execute a partir da raiz do projeto:

```bash
pip install -r requirements.txt
```

```bash
python -m uber_report.main_uber
```

Opcional (sem `-m`):
```bash
python uber_report/main_uber.py
```

## Saida
O PDF gerado fica na raiz com o nome:
`Relatorio UBER - YYYYMMDD.pdf`
