"""
CAR Downloader - Versão FUNCIONAL
Captura o arquivo diretamente da resposta HTTP
"""

import asyncio
import json
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright
from captcha_interface import capturar_e_resolver_captcha


async def extrair_dados_demonstrativo_html(html_content: str) -> dict:
    """Extrai todos os dados do demonstrativo organizados por tópicos"""

    def extrair_valor(pattern):
        """Helper para extrair valor com regex"""
        match = re.search(pattern, html_content)
        return match.group(1).strip() if match else None

    dados = {
        "situacao_cadastro": extrair_valor(r'Situação do Cadastro:.*?<span class="status-imovel status(\w+)">'),
        "registro_inscricao_car": extrair_valor(r'Registro de Inscrição no CAR:</p><b[^>]*>([^<]+)</b>'),
        "condicao_externa": extrair_valor(r'Condição Externa:</p><b[^>]*>([^<]+)</b>'),

        "dados_imovel_rural": {
            "area_imovel_rural": extrair_valor(r'Área do Imóvel Rural:</p><b[^>]*>([^<]+)</b>'),
            "modulos_fiscais": extrair_valor(r'Módulos fiscais:</p><b[^>]*>([^<]+)</b>'),
            "municipio_uf": extrair_valor(r'Município / UF:</p><b[^>]*>([^<]+)</b>'),
            "coordenadas_geograficas": {
                "latitude": extrair_valor(r'Lat: ([^<]+)</b>'),
                "longitude": extrair_valor(r'Long: ([^<]+)</b>')
            },
            "data_inscricao": extrair_valor(r'Data da Inscrição:</p><b[^>]*>([^<]+)</b>'),
            "data_ultima_retificacao": extrair_valor(r'Data da Última Retificação:</p><b[^>]*>([^<]+)</b>')
        },

        "cobertura_solo": {
            "area_remanescente_vegetacao_nativa": extrair_valor(r'Área de Remanescente de Vegetação Nativa</p><b[^>]*>([^<]+)</b>'),
            "area_rural_consolidada": extrair_valor(r'Área Rural Consolidada</p><b[^>]*>([^<]+)</b>'),
            "area_servidao_administrativa": extrair_valor(r'Área de Servidão Administrativa</p><b[^>]*>([^<]+)</b>')
        },

        "reserva_legal": {
            "localizacao_reserva_legal": extrair_valor(r'<b ng-style[^>]*class="reserva-legal[^"]*">([^<]+)</b>'),
            "informacao_documental": {
                "area_reserva_legal_averbada_art30": extrair_valor(r'Área de Reserva Legal Averbada, referente ao Art\. 30[^<]*</p><b[^>]*>([^<]+)</b>')
            },
            "informacao_georreferenciada": {
                "area_reserva_legal_averbada": extrair_valor(r'Área de Reserva Legal Averbada</p><b[^>]*>([^<]+)</b>'),
                "area_reserva_legal_aprovada_nao_averbada": extrair_valor(r'Área de Reserva Legal Aprovada não Averbada</p><b[^>]*>([^<]+)</b>'),
                "area_reserva_legal_proposta": extrair_valor(r'Área de Reserva Legal Proposta</p><b[^>]*>([^<]+)</b>'),
                "total_reserva_legal_declarada": extrair_valor(r'Total de Reserva Legal Declarada pelo Proprietário/Possuidor</p><b[^>]*>([^<]+)</b>')
            }
        },

        "areas_preservacao_permanente_app": {
            "app_total": extrair_valor(r'<p class="col-xs-7 no-padding">APP</p><b[^>]*>([^<]+)</b>'),
            "app_area_rural_consolidada": extrair_valor(r'APP em Área Rural Consolidada</p><b[^>]*>([^<]+)</b>'),
            "app_area_remanescente_vegetacao_nativa": extrair_valor(r'APP em Área de Remanescente de Vegetação Nativa</p><b[^>]*>([^<]+)</b>')
        },

        "uso_restrito": {
            "area_uso_restrito": extrair_valor(r'<p class="col-xs-5 no-padding">Área de uso restrito</p><b[^>]*>([^<]+)</b>')
        },

        "regularidade_ambiental": {
            "passivo_excedente_reserva_legal": extrair_valor(r'Passivo / Excedente de Reserva Legal</p><b[^>]*>([^<]+)</b>'),
            "area_reserva_legal_recompor": extrair_valor(r'Área de Reserva Legal a recompor</p><b[^>]*>([^<]+)</b>'),
            "area_app_recompor": extrair_valor(r'Área de Preservação Permanente a recompor</p><b[^>]*>([^<]+)</b>'),
            "area_uso_restrito_recompor": extrair_valor(r'Área de Uso Restrito a recompor</p><b[^>]*>([^<]+)</b>')
        }
    }

    return dados


async def download_car(numero_car: str, pasta_destino: str = "./downloads_car"):
    """Download automatizado do CAR com captura direta do arquivo"""

    print("\n" + "="*80)
    print("CAR DOWNLOADER - CAPTURA DIRETA")
    print("="*80)
    print(f"CAR: {numero_car}")
    print(f"Pasta: {pasta_destino}")
    print("="*80 + "\n")

    Path(pasta_destino).mkdir(parents=True, exist_ok=True)

    resultados = {
        'numero_car': numero_car,
        'info_popup': {},
        'dados_demonstrativo': {},
        'arquivo_shapefile': None,
        'sucesso': False
    }

    shapefile_response = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            accept_downloads=True
        )

        page = await context.new_page()

        # Capturar resposta do shapefile
        async def capture_shapefile_response(response):
            nonlocal shapefile_response
            if 'exportShapeFile' in response.url:
                content_type = response.headers.get('content-type', '')
                if 'application/zip' in content_type:
                    print(f"    [OK] Arquivo ZIP capturado!")
                    shapefile_response = response

        page.on("response", lambda response: asyncio.create_task(capture_shapefile_response(response)))

        try:
            # ETAPA 1: BUSCAR
            print("[1/4] Buscando CAR...")
            await page.goto("https://consultapublica.car.gov.br/publico/imoveis/index",
                           wait_until='domcontentloaded', timeout=90000)
            await asyncio.sleep(15)

            search_control = page.locator('.leaflet-control-search').first
            await search_control.click()
            await asyncio.sleep(2)

            input_busca = page.locator('.leaflet-control-search input').first
            await input_busca.click()
            await input_busca.press_sequentially(numero_car, delay=100)
            await asyncio.sleep(1)
            await input_busca.press("Enter")
            await asyncio.sleep(5)
            print("    [OK] Busca concluida")

            # ETAPA 2: POPUP
            print("\n[2/4] Extraindo dados...")
            try:
                await page.wait_for_selector('.leaflet-popup-content', timeout=10000)
                popup_content = page.locator('.leaflet-popup-content').first
                list_items = await popup_content.locator('li').all()

                for item in list_items:
                    text = await item.inner_text()
                    if ':' in text:
                        key, value = text.split(':', 1)
                        resultados['info_popup'][key.strip()] = value.strip()

                try:
                    titulo = await popup_content.locator('h5, h6, strong').first.inner_text()
                    resultados['info_popup']['Numero CAR'] = titulo
                except:
                    pass

                print(f"    [OK] {len(resultados['info_popup'])} dados extraidos")
            except Exception as e:
                print(f"    [ERRO] {e}")

            # ETAPA 3: DEMONSTRATIVO
            print("\n[3/4] Extraindo dados do demonstrativo...")
            try:
                demonstrativo_btn = page.locator('button:has-text("Demonstrativo")').first
                async with context.expect_page() as new_page_info:
                    await demonstrativo_btn.click()

                demo_page = await new_page_info.value
                await demo_page.wait_for_load_state('networkidle', timeout=30000)

                html_content = await demo_page.content()

                # Extrair dados estruturados (sem salvar HTML)
                dados_extraidos = await extrair_dados_demonstrativo_html(html_content)
                resultados['dados_demonstrativo'] = dados_extraidos

                # Contar total de campos (incluindo nested)
                def contar_campos(obj):
                    count = 0
                    if isinstance(obj, dict):
                        for v in obj.values():
                            if isinstance(v, dict):
                                count += contar_campos(v)
                            elif v is not None:
                                count += 1
                    return count

                total_campos = contar_campos(dados_extraidos)
                print(f"    [OK] {total_campos} campos extraídos e estruturados por tópicos")

                await demo_page.close()
            except Exception as e:
                print(f"    [ERRO] {e}")

            await page.bring_to_front()
            await asyncio.sleep(2)

            # ETAPA 4: SHAPEFILE
            print("\n[4/4] Baixando shapefile...")
            try:
                download_shp_btn = page.locator('button:has-text("Realizar download shapefile")').first
                await download_shp_btn.click()
                await asyncio.sleep(3)

                # Resolver CAPTCHA
                print("    Resolvendo CAPTCHA...")
                captcha_selectors = [
                    'img[src*="Captcha"]',
                    'img[src*="captcha"]',
                    'img[id="imagemCaptcha"]',
                ]

                captcha_texto = None
                for selector in captcha_selectors:
                    try:
                        count = await page.locator(selector).count()
                        if count > 0:
                            captcha_texto = await capturar_e_resolver_captcha(page, selector)
                            if captcha_texto:
                                break
                    except:
                        continue

                if not captcha_texto:
                    raise Exception("CAPTCHA nao resolvido")

                print(f"    [OK] CAPTCHA: {captcha_texto}")

                # Preencher campo
                await asyncio.sleep(1)
                input_captcha = page.locator('input[type="text"]').first
                await input_captcha.fill(captcha_texto)
                print("    [OK] Campo preenchido")

                await asyncio.sleep(1)

                # Clicar no botao Download (dentro da modal)
                print("    Clicando no botao download...")
                await page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const downloadBtn = buttons.find(btn =>
                            btn.textContent.trim().toLowerCase() === 'download'
                        );
                        if (downloadBtn) downloadBtn.click();
                    }
                """)

                # Aguardar resposta
                print("    Aguardando resposta do servidor...")
                await asyncio.sleep(5)

                # Verificar se capturamos a resposta
                if shapefile_response:
                    print("    [OK] Resposta capturada! Salvando arquivo...")

                    # Ler conteudo binario
                    file_bytes = await shapefile_response.body()
                    file_size = len(file_bytes) / 1024

                    # Salvar arquivo
                    shapefile_path = os.path.join(pasta_destino, f"{numero_car}.zip")
                    with open(shapefile_path, 'wb') as f:
                        f.write(file_bytes)

                    resultados['arquivo_shapefile'] = shapefile_path

                    print(f"    [OK] Shapefile salvo: {shapefile_path}")
                    print(f"    [OK] Tamanho: {file_size:.2f} KB")
                else:
                    print("    [ERRO] Resposta nao capturada")

            except Exception as e:
                print(f"    [ERRO] {e}")
                import traceback
                traceback.print_exc()

            resultados['sucesso'] = True

        except Exception as e:
            print(f"\n[ERRO GERAL] {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Salvar JSON
            json_path = os.path.join(pasta_destino, f"resultado_{numero_car}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(resultados, f, indent=2, ensure_ascii=False)

            print(f"\n[OK] Dados salvos: {json_path}")

            await asyncio.sleep(3)
            await browser.close()

    return resultados


async def main():
    numero_car = "MS-5007901-C252AF6443F04FC3BDCFC7AFD3357053"

    # Criar pasta com nome do CAR dentro de teste_final
    pasta_destino = f"./teste_final/{numero_car}"

    resultados = await download_car(
        numero_car=numero_car,
        pasta_destino=pasta_destino
    )

    print("\n" + "="*80)
    print("RESULTADO FINAL")
    print("="*80)

    if resultados['arquivo_shapefile']:
        size = os.path.getsize(resultados['arquivo_shapefile']) / 1024
        print(f"\n[SHAPEFILE] {resultados['arquivo_shapefile']}")
        print(f"            {size:.2f} KB")
    else:
        print("\n[AVISO] Shapefile nao baixado")

    # Contar total de campos extraídos
    def contar_campos(obj):
        count = 0
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, dict):
                    count += contar_campos(v)
                elif v is not None:
                    count += 1
        return count

    total_campos = contar_campos(resultados.get('dados_demonstrativo', {}))
    print(f"\n[DADOS ESTRUTURADOS] {total_campos} campos extraídos organizados por tópicos")
    print(f"[JSON] {pasta_destino}/resultado_{numero_car}.json")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
