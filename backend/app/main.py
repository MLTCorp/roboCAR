"""
roboCAR Backend API
FastAPI application with WebSocket support for CAR automation
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import base64
import asyncio
from datetime import datetime
from typing import Optional
import tempfile
import shutil
import os

from .config import settings
from .models import (
    CarDownloadRequest,
    ProgressMessage,
    CaptchaMessage,
    CompletedMessage,
    ErrorMessage
)
from .car_downloader import download_car_websocket
from .supabase_client import supabase_client
from .utils import normalizar_numero_car, validar_formato_car

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar app
app = FastAPI(
    title="roboCAR API",
    description="API para automação de consulta de dados do CAR",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "roboCAR API",
        "version": "2.0.0",
        "status": "online"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    checks = {
        "api": "ok",
        "supabase": "unknown",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Verificar Supabase
    try:
        supabase_client.table("duploa_consultas_car").select("id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = "error"
        logger.error(f"Supabase health check failed: {e}")

    all_ok = all(v == "ok" for v in [checks["api"], checks["supabase"]])

    return JSONResponse(
        content={
            "status": "healthy" if all_ok else "degraded",
            "checks": checks
        },
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    )


@app.websocket("/ws/car/{numero_car}")
async def websocket_car_download(websocket: WebSocket, numero_car: str):
    """
    WebSocket endpoint para download de CAR com resolução de CAPTCHA remota

    Fluxo:
    1. Cliente conecta e envia { "cliente_id": "..." }
    2. Backend inicia processamento
    3. Quando CAPTCHA aparecer, envia { "type": "captcha_required", "image": "base64..." }
    4. Cliente responde { "captcha_text": "ABC123" }
    5. Backend continua e envia { "type": "completed", ... }
    """
    # NORMALIZAR número CAR (remover pontos)
    numero_car_original = numero_car
    numero_car = normalizar_numero_car(numero_car)

    print(f"\n=== [WS] Nova conexao WebSocket para CAR: {numero_car} ===")
    logger.info(f"[WS] Nova conexao WebSocket para CAR: {numero_car}")

    if numero_car_original != numero_car:
        logger.info(f"[WS] Número CAR normalizado de '{numero_car_original}' para '{numero_car}'")

    # Validar formato básico
    if not validar_formato_car(numero_car):
        logger.warning(f"[WS] Número CAR com formato suspeito: {numero_car}")

    await websocket.accept()
    print(f"=== [WS] WebSocket aceita para CAR: {numero_car} ===\n")
    logger.info(f"[WS] WebSocket aceita para CAR: {numero_car}")

    cliente_id = None
    consulta_id = None
    temp_dir = None

    try:
        # Receber configuração inicial
        print(f"=== [WS] Aguardando configuracao inicial... ===")
        logger.info(f"[WS] Aguardando configuracao inicial...")
        config = await websocket.receive_json()
        print(f"=== [WS] Configuracao recebida: {config} ===")
        logger.info(f"[WS] Configuracao recebida: {config}")
        cliente_id = config.get("cliente_id")

        if not cliente_id:
            logger.error(f"[WS] cliente_id nao fornecido!")
            raise ValueError("cliente_id não fornecido")

        logger.info(f"[WS] Cliente ID: {cliente_id}")

        # Criar registro no Supabase
        consulta = supabase_client.table("duploa_consultas_car").insert({
            "cliente_id": cliente_id,
            "numero_car": numero_car,
            "status": "processando",
            "consulta_iniciada_em": datetime.utcnow().isoformat()
        }).execute()

        consulta_id = consulta.data[0]["id"]
        logger.info(f"Consulta criada: {consulta_id}")

        # Criar diretório temporário
        temp_dir = tempfile.mkdtemp(prefix=f"car_{consulta_id}_")
        logger.info(f"Diretório temporário: {temp_dir}")

        # Callback para resolver CAPTCHA remotamente
        async def resolver_captcha_remoto(image_bytes: bytes) -> str:
            """Envia CAPTCHA para frontend e aguarda resposta"""
            logger.info(f"CAPTCHA detectado, enviando para cliente {cliente_id}...")

            # Converter para base64
            img_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Enviar para frontend
            captcha_msg = CaptchaMessage(image=img_base64)
            await websocket.send_json(captcha_msg.model_dump())

            # Aguardar resposta (timeout de 5 minutos)
            try:
                response = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=300
                )
                captcha_text = response.get("captcha_text")

                if not captcha_text:
                    raise ValueError("CAPTCHA text não fornecido")

                logger.info(f"CAPTCHA recebido do cliente {cliente_id}: {captcha_text}")
                return captcha_text

            except asyncio.TimeoutError:
                raise TimeoutError("Timeout aguardando solução do CAPTCHA")

        # Callback para enviar progresso
        async def enviar_progresso(etapa: str, mensagem: str):
            """Envia atualização de progresso para o cliente"""
            logger.info(f"Progresso - {etapa}: {mensagem}")
            progress_msg = ProgressMessage(etapa=etapa, mensagem=mensagem)
            await websocket.send_json(progress_msg.model_dump())

        # Callback para salvar dados assim que demonstrativo for extraído
        async def salvar_dados_demonstrativo(dados: dict):
            """Salva dados do popup + demonstrativo ANTES de tentar o shapefile"""
            logger.info("📊 SALVANDO dados do demonstrativo no Supabase (ANTES do shapefile)...")

            try:
                supabase_client.table("duploa_consultas_car").update({
                    "status_cadastro": dados["info_popup"].get("Status do Cadastro"),
                    "tipo_imovel": dados["info_popup"].get("Tipo de imóvel"),
                    "municipio": dados["info_popup"].get("Município"),
                    "area_total": dados["info_popup"].get("Área"),
                    "dados_demonstrativo": dados.get("dados_demonstrativo"),
                    # Status ainda é 'processando' pois falta o shapefile
                }).eq("id", consulta_id).execute()

                logger.info("✅ Dados do demonstrativo salvos com sucesso!")
                await enviar_progresso("dados_salvos", "Dados do demonstrativo salvos no banco")

            except Exception as e:
                logger.error(f"Erro ao salvar dados do demonstrativo: {e}")
                # Não falhar a consulta por erro ao salvar

        # Executar download
        logger.info("Iniciando download CAR...")
        resultados = await download_car_websocket(
            numero_car=numero_car,
            pasta_destino=temp_dir,
            resolver_captcha=resolver_captcha_remoto,
            enviar_progresso=enviar_progresso,
            callback_dados_extraidos=salvar_dados_demonstrativo,
            headless=settings.headless,
            slow_mo=settings.slow_mo
        )

        logger.info("Download concluído, processando resultados...")

        # VALIDAÇÃO CRÍTICA: Shapefile é OBRIGATÓRIO!
        if not resultados.get("arquivo_shapefile"):
            logger.error("❌ ERRO CRÍTICO: Shapefile não foi baixado!")
            logger.error(f"❌ Cliente: {cliente_id} | CAR: {numero_car}")
            raise Exception("Shapefile é obrigatório mas não foi baixado. Verifique se o CAPTCHA foi digitado corretamente.")

        # Upload do shapefile para Supabase Storage
        shapefile_url = None
        shapefile_size = None

        logger.info("Fazendo upload do shapefile para Supabase Storage...")

        try:
            with open(resultados["arquivo_shapefile"], "rb") as f:
                shapefile_bytes = f.read()

            # Path no storage: {cliente_id}/{numero_car}/shapefile.zip
            storage_path = f"{cliente_id}/{numero_car}/shapefile.zip"

            # Upload para storage
            storage = supabase_client.storage.from_("car-shapefiles")
            storage.upload(
                storage_path,
                shapefile_bytes,
                {"content-type": "application/zip", "upsert": "true"}
            )

            # Obter URL pública
            shapefile_url = storage.get_public_url(storage_path)
            shapefile_size = len(shapefile_bytes)

            logger.info(f"Shapefile uploaded: {shapefile_url}")

        except Exception as e:
            logger.error(f"Erro ao fazer upload do shapefile: {e}")
            raise Exception(f"Erro crítico ao fazer upload do shapefile: {e}")

        # VALIDAÇÃO: GeoJSON layers também são obrigatórios
        if not resultados.get("geojson_layers") or len(resultados.get("geojson_layers", {})) == 0:
            logger.error("❌ ERRO CRÍTICO: GeoJSON layers não foram extraídos do shapefile!")
            logger.error(f"❌ Cliente: {cliente_id} | CAR: {numero_car}")
            raise Exception("GeoJSON layers são obrigatórios mas não foram extraídos do shapefile")

        # Atualizar registro no Supabase (dados já foram salvos, só atualizar shapefile, geojson e status)
        logger.info("Atualizando registro no Supabase com shapefile e GeoJSON layers...")
        supabase_client.table("duploa_consultas_car").update({
            "status": "concluido",
            "shapefile_url": shapefile_url,
            "shapefile_size": shapefile_size,
            "geojson_layers": resultados.get("geojson_layers", {}),
            "consulta_concluida_em": datetime.utcnow().isoformat()
        }).eq("id", consulta_id).execute()

        logger.info("Registro atualizado com sucesso")

        # Enviar resultado final
        completed_msg = CompletedMessage(
            consulta_id=consulta_id,
            numero_car=numero_car,
            shapefile_url=shapefile_url,
            dados_extraidos=resultados
        )

        await websocket.send_json(completed_msg.model_dump())
        logger.info(f"Consulta CAR concluída com sucesso: {numero_car}")

    except WebSocketDisconnect:
        logger.warning(f"WebSocket desconectado: {numero_car}")

        # Atualizar status no Supabase
        if consulta_id:
            supabase_client.table("duploa_consultas_car").update({
                "status": "erro",
                "erro_mensagem": "Conexão WebSocket interrompida"
            }).eq("id", consulta_id).execute()

    except Exception as e:
        logger.error(f"Erro no processamento do CAR {numero_car}: {e}", exc_info=True)
        logger.error(f"🔍 INFORMAÇÕES DO ERRO - Cliente ID: {cliente_id}, CAR: {numero_car}, Consulta ID: {consulta_id}")

        # SEMPRE marcar como ERRO se não tiver shapefile
        # Shapefile é OBRIGATÓRIO para o mapa funcionar!
        erro_msg = str(e).lower()

        if consulta_id:
            # Mensagem de erro apropriada
            mensagem_erro = str(e)

            # Se for erro de CAPTCHA/shapefile, mensagem específica
            if "captcha" in erro_msg or "shapefile" in erro_msg:
                logger.error(f"⚠️ FALHA CRÍTICA SHAPEFILE - Cliente: {cliente_id} | CAR: {numero_car}")
                logger.error(f"   Erro: {str(e)}")

                # Verificar se foi erro de CAPTCHA
                if "captcha" in erro_msg:
                    mensagem_erro = "❌ ERRO: CAPTCHA incorreto ou shapefile não foi baixado. Por favor, tente novamente e digite o CAPTCHA com atenção."
                else:
                    mensagem_erro = f"❌ ERRO: Shapefile obrigatório não foi baixado. {str(e)}"

            # SEMPRE marca como ERRO (nunca "concluido_sem_shapefile")
            supabase_client.table("duploa_consultas_car").update({
                "status": "erro",
                "erro_mensagem": mensagem_erro,
                "consulta_concluida_em": datetime.utcnow().isoformat()
            }).eq("id", consulta_id).execute()

        # Enviar erro para cliente com mensagem clara
        try:
            # Mensagem amigável para o usuário
            if "captcha" in erro_msg or "shapefile" in erro_msg:
                mensagem_usuario = "❌ Falha no download do shapefile. Isso geralmente acontece quando o CAPTCHA foi digitado incorretamente. Por favor, tente novamente prestando atenção ao CAPTCHA."
            else:
                mensagem_usuario = str(e)

            error_msg = ErrorMessage(
                message=mensagem_usuario,
                details=f"CAR: {numero_car} | Cliente: {cliente_id}"
            )
            await websocket.send_json(error_msg.model_dump())
        except:
            pass  # WebSocket pode já estar fechado

    finally:
        # Copiar screenshot de debug antes de remover diretório
        if temp_dir and os.path.exists(temp_dir):
            try:
                debug_screenshot = os.path.join(temp_dir, "debug_before_shapefile.png")
                if os.path.exists(debug_screenshot):
                    # Copiar para diretório atual
                    debug_dest = f"debug_{consulta_id}.png"
                    shutil.copy2(debug_screenshot, debug_dest)
                    logger.info(f"Screenshot de debug copiado para: {debug_dest}")
            except Exception as e:
                logger.warning(f"Erro ao copiar screenshot de debug: {e}")

        # Limpar diretório temporário
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Diretório temporário removido: {temp_dir}")
            except Exception as e:
                logger.error(f"Erro ao remover diretório temporário: {e}")

        # Fechar WebSocket
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )
