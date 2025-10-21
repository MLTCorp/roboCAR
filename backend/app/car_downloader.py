"""
CAR Downloader - Versão adaptada para WebSocket
Captura dados do CAR com suporte a resolução remota de CAPTCHA
"""
import asyncio
import json
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright
from typing import Callable, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


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


async def download_car_websocket(
    numero_car: str,
    pasta_destino: str,
    resolver_captcha: Callable[[bytes], str],
    enviar_progresso: Optional[Callable[[str, str], None]] = None,
    headless: bool = True,
    slow_mo: int = 100
) -> Dict[str, Any]:
    """
    Download automatizado do CAR com callbacks para WebSocket

    Args:
        numero_car: Número do CAR
        pasta_destino: Pasta para salvar arquivos
        resolver_captcha: Função assíncrona que recebe bytes da imagem e retorna texto do CAPTCHA
        enviar_progresso: Função opcional para enviar atualizações de progresso
        headless: Executar navegador em modo headless
        slow_mo: Delay entre ações (ms)

    Returns:
        Dict com resultados da consulta
    """
    logger.info(f"Iniciando download CAR: {numero_car}")

    if enviar_progresso:
        await enviar_progresso("inicio", f"Iniciando consulta CAR: {numero_car}")

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
            headless=headless,
            slow_mo=slow_mo
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
                    logger.info("Arquivo ZIP capturado!")
                    shapefile_response = response

        page.on("response", lambda response: asyncio.create_task(capture_shapefile_response(response)))

        try:
            # ETAPA 1: BUSCAR
            logger.info("Etapa 1/4: Buscando CAR...")
            if enviar_progresso:
                await enviar_progresso("busca", "Acessando site do CAR e buscando número...")

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
            logger.info("Busca concluída")

            # ETAPA 2: POPUP
            logger.info("Etapa 2/4: Extraindo dados do popup...")
            if enviar_progresso:
                await enviar_progresso("extracao", "Extraindo dados básicos...")

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

                logger.info(f"{len(resultados['info_popup'])} dados extraídos do popup")
            except Exception as e:
                logger.error(f"Erro ao extrair popup: {e}")

            # ETAPA 3: DEMONSTRATIVO
            logger.info("Etapa 3/4: Extraindo dados do demonstrativo...")
            if enviar_progresso:
                await enviar_progresso("demonstrativo", "Abrindo demonstrativo e extraindo dados completos...")

            try:
                demonstrativo_btn = page.locator('button:has-text("Demonstrativo")').first
                async with context.expect_page() as new_page_info:
                    await demonstrativo_btn.click()

                demo_page = await new_page_info.value
                await demo_page.wait_for_load_state('networkidle', timeout=30000)

                html_content = await demo_page.content()

                # Extrair dados estruturados
                dados_extraidos = await extrair_dados_demonstrativo_html(html_content)
                resultados['dados_demonstrativo'] = dados_extraidos

                logger.info(f"Dados do demonstrativo extraídos com sucesso")

                await demo_page.close()
            except Exception as e:
                logger.error(f"Erro ao extrair demonstrativo: {e}")

            await page.bring_to_front()
            await asyncio.sleep(2)

            # ETAPA 4: SHAPEFILE
            logger.info("Etapa 4/4: Baixando shapefile...")
            if enviar_progresso:
                await enviar_progresso("shapefile", "Iniciando download do shapefile...")

            try:
                download_shp_btn = page.locator('button:has-text("Realizar download shapefile")').first
                await download_shp_btn.click()
                await asyncio.sleep(3)

                # Resolver CAPTCHA via callback
                logger.info("Resolvendo CAPTCHA...")
                if enviar_progresso:
                    await enviar_progresso("captcha", "Aguardando resolução do CAPTCHA...")

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
                            captcha_element = page.locator(selector).first
                            await captcha_element.wait_for(state='visible', timeout=10000)

                            # Capturar screenshot do CAPTCHA
                            image_bytes = await captcha_element.screenshot()

                            # Chamar callback para resolver remotamente
                            captcha_texto = await resolver_captcha(image_bytes)

                            if captcha_texto:
                                break
                    except:
                        continue

                if not captcha_texto:
                    raise Exception("CAPTCHA não resolvido")

                logger.info(f"CAPTCHA resolvido: {captcha_texto}")

                # Preencher campo
                await asyncio.sleep(1)
                input_captcha = page.locator('input[type="text"]').first
                await input_captcha.fill(captcha_texto)

                await asyncio.sleep(1)

                # Clicar no botão Download
                if enviar_progresso:
                    await enviar_progresso("download", "Baixando shapefile...")

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
                await asyncio.sleep(5)

                # Verificar se capturamos a resposta
                if shapefile_response:
                    logger.info("Resposta capturada! Salvando arquivo...")

                    # Ler conteúdo binário
                    file_bytes = await shapefile_response.body()
                    file_size = len(file_bytes) / 1024

                    # Salvar arquivo
                    shapefile_path = os.path.join(pasta_destino, f"{numero_car}.zip")
                    with open(shapefile_path, 'wb') as f:
                        f.write(file_bytes)

                    resultados['arquivo_shapefile'] = shapefile_path
                    resultados['shapefile_size'] = int(file_size)

                    logger.info(f"Shapefile salvo: {shapefile_path} ({file_size:.2f} KB)")
                else:
                    logger.warning("Resposta do shapefile não capturada")

            except Exception as e:
                logger.error(f"Erro ao baixar shapefile: {e}")
                raise

            resultados['sucesso'] = True
            logger.info("Download CAR concluído com sucesso!")

        except Exception as e:
            logger.error(f"Erro geral no download CAR: {e}")
            raise

        finally:
            await asyncio.sleep(2)
            await browser.close()

    return resultados
