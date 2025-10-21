# roboCAR - Download Automatizado de Dados do CAR

Sistema automatizado para download de dados do Cadastro Ambiental Rural (CAR).

## Estrutura do Projeto

```
roboCAR/
├── download_car.py          # Script principal funcional
├── captcha_interface.py     # Interface para resolução de CAPTCHA
├── teste_final/             # Resultados do último teste
│   ├── demonstrativo_*.html (25.94 KB)
│   ├── *.zip (shapefile - 73.95 KB)
│   └── resultado_*.json (1.10 KB)
└── README.md
```

## Como Usar

```python
from download_car import download_car
import asyncio

async def main():
    resultados = await download_car(
        numero_car="MS-5007901-C252AF6443F04FC3BDCFC7AFD3357053",
        pasta_destino="./meus_downloads"
    )

asyncio.run(main())
```

## Dados Extraídos

- **Popup**: 6 campos (status, tipo, município, área, data)
- **Demonstrativo**: 12 campos (áreas, coordenadas, datas, etc.)
- **Shapefile**: ZIP com 4 arquivos shapefile

## Instalação

```bash
pip install playwright
playwright install chromium
```

## Tecnologia Principal

Captura direta da resposta HTTP ao invés de download tradicional do navegador.

```python
# Monitora resposta HTTP
if 'exportShapeFile' in response.url:
    if 'application/zip' in content_type:
        file_bytes = await response.body()
        # Salva diretamente
```

Veja `teste_final/resultado_*.json` para exemplo completo de dados extraídos.
