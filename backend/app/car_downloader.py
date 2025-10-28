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
from .shapefile_processor import processar_shapefile_car

logger = logging.getLogger(__name__)


async def tentar_abrir_popup_com_retry(
    page,
    numero_car: str,
    max_tentativas: int = 3,
    enviar_progresso: Optional[Callable[[str, str], None]] = None
) -> dict:
    """
    Tenta abrir o popup do CAR com retry automático

    Args:
        page: Página do Playwright
        numero_car: Número do CAR a buscar
        max_tentativas: Número máximo de tentativas
        enviar_progresso: Callback para enviar progresso

    Returns:
        Dict com dados extraídos do popup

    Raises:
        Exception: Se popup não abrir após todas as tentativas
    """
    timeouts = [30000, 45000, 60000]  # Timeouts progressivos (aumentados)
    wait_times = [5, 10, 15]  # Tempos de espera entre tentativas

    info_popup = {}

    for tentativa in range(1, max_tentativas + 1):
        try:
            timeout_atual = timeouts[tentativa - 1] if tentativa <= len(timeouts) else timeouts[-1]

            logger.info(f"Tentativa {tentativa}/{max_tentativas}: Aguardando popup aparecer (timeout {timeout_atual/1000}s)...")
            if enviar_progresso:
                await enviar_progresso("extracao", f"Tentando abrir popup (tentativa {tentativa}/{max_tentativas})...")

            # Aguardar popup
            await page.wait_for_selector('.leaflet-popup-content', timeout=timeout_atual)
            logger.info(f"✓ Popup encontrado na tentativa {tentativa}!")

            # Extrair dados do popup
            popup_content = page.locator('.leaflet-popup-content').first
            list_items = await popup_content.locator('li').all()

            for item in list_items:
                text = await item.inner_text()
                if ':' in text:
                    key, value = text.split(':', 1)
                    info_popup[key.strip()] = value.strip()

            try:
                titulo = await popup_content.locator('h5, h6, strong').first.inner_text()
                info_popup['Numero CAR'] = titulo
            except:
                pass

            logger.info(f"{len(info_popup)} dados extraídos do popup")

            if enviar_progresso:
                await enviar_progresso("extracao", f"Popup aberto! {len(info_popup)} dados extraídos")

            return info_popup

        except Exception as e:
            logger.warning(f"Tentativa {tentativa}/{max_tentativas} falhou: {e}")

            # Se não for a última tentativa, tentar novamente
            if tentativa < max_tentativas:
                wait_time = wait_times[tentativa - 1] if tentativa <= len(wait_times) else wait_times[-1]

                logger.info(f"Aguardando {wait_time}s antes de tentar novamente...")
                if enviar_progresso:
                    await enviar_progresso("extracao", f"Popup não abriu, tentando novamente em {wait_time}s (tentativa {tentativa + 1}/{max_tentativas})...")

                await asyncio.sleep(wait_time)

                # Recarregar página e refazer busca
                logger.info("Recarregando página e refazendo busca...")
                await page.reload(wait_until='domcontentloaded', timeout=90000)
                await asyncio.sleep(10)

                # Refazer busca
                search_control = page.locator('.leaflet-control-search').first
                await search_control.click()
                await asyncio.sleep(2)

                input_busca = page.locator('.leaflet-control-search input').first
                await input_busca.click()
                await input_busca.fill('')  # Limpar
                await input_busca.press_sequentially(numero_car, delay=100)
                await asyncio.sleep(1)
                await input_busca.press("Enter")

                # Aguardar progressivamente mais
                await asyncio.sleep(wait_time)

                # Scroll para garantir visibilidade
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(2)
            else:
                # Última tentativa falhou
                logger.error(f"Popup não abriu após {max_tentativas} tentativas")
                raise Exception(f"Popup não abriu após {max_tentativas} tentativas. O site do CAR pode estar fora do ar ou o número CAR pode ser inválido.")

    return info_popup


async def tentar_extrair_demonstrativo_com_retry(
    page,
    context,
    max_tentativas: int = 3,
    enviar_progresso: Optional[Callable[[str, str], None]] = None
) -> dict:
    """
    Tenta extrair dados do demonstrativo com retry automático

    Args:
        page: Página principal do Playwright
        context: Contexto do navegador
        max_tentativas: Número máximo de tentativas
        enviar_progresso: Callback para enviar progresso

    Returns:
        Dict com dados extraídos do demonstrativo

    Raises:
        Exception: Se demonstrativo não abrir após todas as tentativas
    """
    timeouts_click = [15000, 20000, 30000]  # Timeouts progressivos para o click
    timeouts_load = [30000, 45000, 60000]   # Timeouts progressivos para carregar página
    wait_times = [3, 5, 8]  # Tempos de espera entre tentativas

    dados_demonstrativo = {}

    for tentativa in range(1, max_tentativas + 1):
        try:
            timeout_click = timeouts_click[tentativa - 1] if tentativa <= len(timeouts_click) else timeouts_click[-1]
            timeout_load = timeouts_load[tentativa - 1] if tentativa <= len(timeouts_load) else timeouts_load[-1]

            logger.info(f"Tentativa {tentativa}/{max_tentativas}: Procurando botão 'Demonstrativo'...")
            if enviar_progresso:
                await enviar_progresso("demonstrativo", f"Abrindo demonstrativo (tentativa {tentativa}/{max_tentativas})...")

            demonstrativo_btn = page.locator('button:has-text("Demonstrativo")').first
            count = await demonstrativo_btn.count()
            logger.info(f"Botões 'Demonstrativo' encontrados: {count}")

            if count == 0:
                logger.warning("Botão 'Demonstrativo' não encontrado")
                raise Exception("Botão Demonstrativo não encontrado")

            logger.info(f"Clicando no botão 'Demonstrativo' (timeout {timeout_click/1000}s)...")
            async with context.expect_page() as new_page_info:
                await demonstrativo_btn.click(timeout=timeout_click)

            demo_page = await new_page_info.value
            logger.info(f"Nova página aberta, aguardando carregamento (timeout {timeout_load/1000}s)...")

            # Aguardar carregamento da página
            await demo_page.wait_for_load_state('domcontentloaded', timeout=timeout_load)
            logger.info("✓ Página do demonstrativo carregada!")

            # Extrair conteúdo HTML
            html_content = await demo_page.content()

            # Extrair dados estruturados
            dados_demonstrativo = await extrair_dados_demonstrativo_html(html_content)

            logger.info(f"✓ Dados do demonstrativo extraídos com sucesso na tentativa {tentativa}")

            if enviar_progresso:
                await enviar_progresso("demonstrativo", "Demonstrativo extraído com sucesso!")

            await demo_page.close()
            return dados_demonstrativo

        except Exception as e:
            logger.warning(f"Tentativa {tentativa}/{max_tentativas} falhou: {e}")

            # Fechar página do demo se ainda estiver aberta
            try:
                if 'demo_page' in locals():
                    await demo_page.close()
            except:
                pass

            # Se não for a última tentativa, aguardar e tentar novamente
            if tentativa < max_tentativas:
                wait_time = wait_times[tentativa - 1] if tentativa <= len(wait_times) else wait_times[-1]

                logger.info(f"Aguardando {wait_time}s antes de tentar novamente...")
                if enviar_progresso:
                    await enviar_progresso("demonstrativo", f"Falha ao abrir demonstrativo, tentando novamente em {wait_time}s (tentativa {tentativa + 1}/{max_tentativas})...")

                await asyncio.sleep(wait_time)

                # Trazer página principal para frente
                await page.bring_to_front()
                await asyncio.sleep(2)
            else:
                # Última tentativa falhou
                logger.error(f"Demonstrativo não abriu após {max_tentativas} tentativas")
                raise Exception(f"Demonstrativo não abriu após {max_tentativas} tentativas: {e}")

    return dados_demonstrativo


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
    callback_dados_extraidos: Optional[Callable[[Dict[str, Any]], None]] = None,
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
        'geojson_layers': {},
        'sucesso': False
    }

    shapefile_response = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=slow_mo
        )

        context = await browser.new_context(
            viewport={'width': 2560, 'height': 1440},  # Viewport maior para garantir que todos elementos apareçam
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
                           wait_until='domcontentloaded', timeout=120000)
            await asyncio.sleep(15)

            search_control = page.locator('.leaflet-control-search').first
            await search_control.click()
            await asyncio.sleep(2)

            input_busca = page.locator('.leaflet-control-search input').first
            await input_busca.click()
            await input_busca.press_sequentially(numero_car, delay=100)
            await asyncio.sleep(1)
            await input_busca.press("Enter")

            # Aguardar network idle para garantir que página carregou completamente
            logger.info("Aguardando carregamento completo da página...")
            try:
                await page.wait_for_load_state('networkidle', timeout=20000)
            except:
                logger.warning("Timeout no networkidle, mas continuando...")

            await asyncio.sleep(5)
            logger.info("Busca concluída")

            # ETAPA 2: POPUP (com retry automático)
            logger.info("Etapa 2/4: Extraindo dados do popup...")
            if enviar_progresso:
                await enviar_progresso("extracao", "Extraindo dados básicos...")

            try:
                # Usar função com retry automático
                resultados['info_popup'] = await tentar_abrir_popup_com_retry(
                    page=page,
                    numero_car=numero_car,
                    max_tentativas=3,
                    enviar_progresso=enviar_progresso
                )
            except Exception as e:
                logger.error(f"Erro ao extrair popup após todas as tentativas: {e}")
                # Popup é crítico - se não abrir, não adianta continuar
                raise

            # ETAPA 3: DEMONSTRATIVO (com retry automático)
            logger.info("Etapa 3/4: Extraindo dados do demonstrativo...")
            if enviar_progresso:
                await enviar_progresso("demonstrativo", "Abrindo demonstrativo e extraindo dados completos...")

            try:
                # Usar função com retry automático
                resultados['dados_demonstrativo'] = await tentar_extrair_demonstrativo_com_retry(
                    page=page,
                    context=context,
                    max_tentativas=3,
                    enviar_progresso=enviar_progresso
                )
            except Exception as e:
                logger.error(f"Erro ao extrair demonstrativo após todas as tentativas: {e}")
                # Demonstrativo não é crítico - continuar mesmo se falhar
                resultados['dados_demonstrativo'] = {}

            # CALLBACK: Dados extraídos (popup + demonstrativo) ANTES do shapefile
            if callback_dados_extraidos:
                logger.info("Chamando callback com dados extraídos (antes do shapefile)...")
                await callback_dados_extraidos({
                    'numero_car': numero_car,
                    'info_popup': resultados['info_popup'],
                    'dados_demonstrativo': resultados['dados_demonstrativo']
                })

            await page.bring_to_front()
            await asyncio.sleep(2)

            # ETAPA 4: SHAPEFILE
            logger.info("Etapa 4/4: Baixando shapefile...")
            if enviar_progresso:
                await enviar_progresso("shapefile", "Iniciando download do shapefile...")

            try:
                # Debug: capturar screenshot antes de procurar botão
                logger.info("Procurando botão de download shapefile...")

                # Scroll para o final da página para garantir que botão esteja visível
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

                debug_screenshot = os.path.join(pasta_destino, "debug_before_shapefile.png")
                await page.screenshot(path=debug_screenshot, full_page=True)
                logger.info(f"Screenshot salvo em: {debug_screenshot}")

                # Tentar diferentes seletores para o botão (com case-insensitive e regex)
                button_selectors = [
                    'button:has-text("Realizar download shapefile")',
                    'button:text-is("Realizar download shapefile")',
                    'button:text-matches(".*download.*shapefile.*", "i")',
                    'button:text-matches(".*shapefile.*", "i")',
                    'button:has-text("shapefile")',
                ]

                download_shp_btn = None
                for selector in button_selectors:
                    logger.info(f"Tentando seletor: {selector}")
                    locator = page.locator(selector)
                    count = await locator.count()
                    logger.info(f"  -> Elementos encontrados: {count}")

                    if count > 0:
                        download_shp_btn = locator.first
                        logger.info(f"  -> ✓ Botão encontrado com seletor: {selector}")
                        break

                if not download_shp_btn:
                    # Listar todos os botões visíveis para debug
                    logger.error("Nenhum botão encontrado! Listando todos os botões da página...")
                    all_buttons = await page.locator('button').all()
                    for i, btn in enumerate(all_buttons[:10]):  # Primeiros 10 botões
                        try:
                            text = await btn.inner_text()
                            logger.info(f"  Botão {i+1}: '{text}'")
                        except:
                            pass

                    raise Exception("Botão de download shapefile não encontrado")

                logger.info("Clicando no botão de download...")
                await download_shp_btn.click(timeout=15000)
                logger.info("Botão clicado, aguardando modal...")
                await asyncio.sleep(3)

                # Resolver CAPTCHA via callback (com retry se errar)
                logger.info("Resolvendo CAPTCHA...")

                captcha_selectors = [
                    'img[src*="Captcha"]',
                    'img[src*="captcha"]',
                    'img[id="imagemCaptcha"]',
                ]

                max_tentativas_captcha = 3
                captcha_aceito = False

                for tentativa_captcha in range(1, max_tentativas_captcha + 1):
                    try:
                        logger.info(f"Resolvendo CAPTCHA (tentativa {tentativa_captcha}/{max_tentativas_captcha})...")
                        if enviar_progresso:
                            await enviar_progresso("captcha", f"Resolvendo CAPTCHA (tentativa {tentativa_captcha}/{max_tentativas_captcha})...")

                        captcha_texto = None
                        captcha_element = None

                        # Procurar elemento CAPTCHA
                        for selector in captcha_selectors:
                            try:
                                logger.info(f"Procurando CAPTCHA com seletor: {selector}")
                                count = await page.locator(selector).count()
                                logger.info(f"Elementos encontrados: {count}")

                                if count > 0:
                                    captcha_element = page.locator(selector).first
                                    logger.info("Aguardando CAPTCHA ficar visível...")
                                    await captcha_element.wait_for(state='visible', timeout=20000)

                                    # Capturar screenshot do CAPTCHA
                                    logger.info("Capturando screenshot do CAPTCHA...")
                                    image_bytes = await captcha_element.screenshot()
                                    logger.info(f"Screenshot capturado: {len(image_bytes)} bytes")

                                    # Chamar callback para resolver remotamente
                                    logger.info("Chamando callback resolver_captcha...")
                                    captcha_texto = await resolver_captcha(image_bytes)
                                    logger.info(f"Callback retornou: {captcha_texto}")

                                    if captcha_texto:
                                        break
                            except Exception as e:
                                logger.warning(f"Erro ao tentar seletor {selector}: {e}")
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

                        # Aguardar resposta e verificar se download começou
                        await asyncio.sleep(8)

                        # Verificar se CAPTCHA foi aceito de múltiplas formas
                        captcha_foi_aceito = False

                        # 1. Verificar se há mensagem de erro de CAPTCHA
                        erro_captcha_count = await page.locator('text=/.*captcha.*incorreto.*/i').count()
                        erro_captcha_count += await page.locator('text=/.*código.*inválido.*/i').count()
                        erro_captcha_count += await page.locator('text=/.*erro.*/i').count()

                        if erro_captcha_count > 0:
                            logger.warning(f"CAPTCHA incorreto detectado na tentativa {tentativa_captcha}")

                            if tentativa_captcha < max_tentativas_captcha:
                                logger.info("Gerando novo CAPTCHA...")
                                if enviar_progresso:
                                    await enviar_progresso("captcha", f"CAPTCHA incorreto, tentando novamente ({tentativa_captcha + 1}/{max_tentativas_captcha})...")

                                # Limpar campo de CAPTCHA
                                try:
                                    await input_captcha.fill('')
                                except:
                                    pass

                                # Recarregar CAPTCHA (clicar no botão de refresh se existir, ou reabrir modal)
                                try:
                                    # Tentar botão de atualizar CAPTCHA
                                    refresh_btn = page.locator('button:has-text("Atualizar"), a:has-text("Atualizar"), img[alt*="Atualizar"]').first
                                    if await refresh_btn.count() > 0:
                                        await refresh_btn.click()
                                        await asyncio.sleep(2)
                                        logger.info("CAPTCHA atualizado via botão")
                                    else:
                                        # Se não houver botão refresh, fechar e reabrir modal
                                        logger.info("Reabrindo modal do CAPTCHA...")
                                        try:
                                            # Fechar modal
                                            close_btn = page.locator('button.close, button:has-text("Fechar"), button:has-text("Cancelar")').first
                                            if await close_btn.count() > 0:
                                                await close_btn.click()
                                                await asyncio.sleep(2)

                                            # Reabrir
                                            await download_shp_btn.click(timeout=10000)
                                            await asyncio.sleep(3)
                                        except Exception as reopen_error:
                                            logger.warning(f"Não foi possível reabrir modal: {reopen_error}")
                                except Exception as refresh_error:
                                    logger.warning(f"Erro ao atualizar CAPTCHA: {refresh_error}")

                                continue  # Tentar novamente
                            else:
                                raise Exception(f"CAPTCHA incorreto após {max_tentativas_captcha} tentativas")

                        # 2. Verificar se o shapefile_response foi capturado (sinal de sucesso)
                        if shapefile_response is not None:
                            logger.info("✓ CAPTCHA aceito! Shapefile response capturado")
                            captcha_aceito = True
                            break

                        # 3. Verificar se modal ainda está aberto (se fechou = sucesso, se aberto = erro)
                        try:
                            modal_aberto = await page.locator('.modal.show, div[role="dialog"]').count()
                            if modal_aberto == 0:
                                # Modal fechou, provavelmente sucesso
                                logger.info("✓ CAPTCHA aceito! Modal fechou")
                                captcha_aceito = True
                                break
                            else:
                                # Modal ainda aberto, CAPTCHA provavelmente errado
                                logger.warning(f"Modal ainda aberto após tentativa {tentativa_captcha}, CAPTCHA pode estar incorreto")

                                if tentativa_captcha < max_tentativas_captcha:
                                    if enviar_progresso:
                                        await enviar_progresso("captcha", f"CAPTCHA pode estar incorreto, tentando novamente ({tentativa_captcha + 1}/{max_tentativas_captcha})...")

                                    # Aguardar mais um pouco para verificar se resposta chega
                                    await asyncio.sleep(5)

                                    # Verificar novamente se shapefile_response chegou
                                    if shapefile_response is not None:
                                        logger.info("✓ CAPTCHA aceito! Resposta chegou após espera adicional")
                                        captcha_aceito = True
                                        break

                                    # Se ainda não chegou, tentar atualizar CAPTCHA
                                    logger.info("Atualizando CAPTCHA para nova tentativa...")
                                    try:
                                        await input_captcha.fill('')
                                        refresh_btn = page.locator('button:has-text("Atualizar"), a:has-text("Atualizar")').first
                                        if await refresh_btn.count() > 0:
                                            await refresh_btn.click()
                                            await asyncio.sleep(2)
                                    except:
                                        pass

                                    continue
                                else:
                                    raise Exception(f"CAPTCHA não aceito após {max_tentativas_captcha} tentativas")
                        except Exception as modal_check_error:
                            logger.warning(f"Erro ao verificar modal: {modal_check_error}")
                            # Se houver erro ao verificar modal, assumir sucesso se shapefile_response foi capturado
                            if shapefile_response is not None:
                                captcha_aceito = True
                                break

                    except Exception as e:
                        if tentativa_captcha >= max_tentativas_captcha:
                            logger.error(f"Erro no CAPTCHA após {max_tentativas_captcha} tentativas: {e}")
                            raise
                        else:
                            logger.warning(f"Erro na tentativa {tentativa_captcha}, tentando novamente: {e}")
                            await asyncio.sleep(2)
                            continue

                if not captcha_aceito:
                    raise Exception("CAPTCHA não foi aceito após todas as tentativas")

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

                    # PROCESSAR SHAPEFILE -> GEOJSON
                    try:
                        if enviar_progresso:
                            await enviar_progresso("processamento", "Processando shapefiles e convertendo para GeoJSON...")

                        logger.info("Iniciando processamento de shapefiles...")

                        # Executar em thread separada para não bloquear o event loop
                        geojson_layers = await asyncio.to_thread(
                            processar_shapefile_car,
                            shapefile_path
                        )

                        resultados['geojson_layers'] = geojson_layers

                        logger.info(f"✓ {len(geojson_layers)} camadas GeoJSON extraídas: {list(geojson_layers.keys())}")

                    except Exception as e:
                        logger.error(f"Erro ao processar shapefile para GeoJSON: {e}", exc_info=True)
                        # Não falhar a consulta por causa disso
                        resultados['geojson_layers'] = {}

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
