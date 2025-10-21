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
        supabase_client.table("consultas_car").select("id").limit(1).execute()
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
    await websocket.accept()
    logger.info(f"WebSocket conectado para CAR: {numero_car}")

    cliente_id = None
    consulta_id = None
    temp_dir = None

    try:
        # Receber configuração inicial
        config = await websocket.receive_json()
        cliente_id = config.get("cliente_id")

        if not cliente_id:
            raise ValueError("cliente_id não fornecido")

        logger.info(f"Cliente ID: {cliente_id}")

        # Criar registro no Supabase
        consulta = supabase_client.table("consultas_car").insert({
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
            logger.info("CAPTCHA detectado, enviando para cliente...")

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

                logger.info(f"CAPTCHA recebido: {captcha_text}")
                return captcha_text

            except asyncio.TimeoutError:
                raise TimeoutError("Timeout aguardando solução do CAPTCHA")

        # Callback para enviar progresso
        async def enviar_progresso(etapa: str, mensagem: str):
            """Envia atualização de progresso para o cliente"""
            logger.info(f"Progresso - {etapa}: {mensagem}")
            progress_msg = ProgressMessage(etapa=etapa, mensagem=mensagem)
            await websocket.send_json(progress_msg.model_dump())

        # Executar download
        logger.info("Iniciando download CAR...")
        resultados = await download_car_websocket(
            numero_car=numero_car,
            pasta_destino=temp_dir,
            resolver_captcha=resolver_captcha_remoto,
            enviar_progresso=enviar_progresso,
            headless=settings.headless,
            slow_mo=settings.slow_mo
        )

        logger.info("Download concluído, processando resultados...")

        # Upload do shapefile para Supabase Storage
        shapefile_url = None
        shapefile_size = None

        if resultados.get("arquivo_shapefile"):
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
                # Não falhar a consulta se o upload falhar

        # Atualizar registro no Supabase
        logger.info("Atualizando registro no Supabase...")
        supabase_client.table("consultas_car").update({
            "status": "concluido",
            "status_cadastro": resultados["info_popup"].get("Status do Cadastro"),
            "tipo_imovel": resultados["info_popup"].get("Tipo de imóvel"),
            "municipio": resultados["info_popup"].get("Município"),
            "area_total": resultados["info_popup"].get("Área"),
            "dados_demonstrativo": resultados.get("dados_demonstrativo"),
            "shapefile_url": shapefile_url,
            "shapefile_size": shapefile_size,
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
            supabase_client.table("consultas_car").update({
                "status": "erro",
                "erro_mensagem": "Conexão WebSocket interrompida"
            }).eq("id", consulta_id).execute()

    except Exception as e:
        logger.error(f"Erro no processamento do CAR {numero_car}: {e}", exc_info=True)

        # Salvar erro no Supabase
        if consulta_id:
            supabase_client.table("consultas_car").update({
                "status": "erro",
                "erro_mensagem": str(e),
                "consulta_concluida_em": datetime.utcnow().isoformat()
            }).eq("id", consulta_id).execute()

        # Enviar erro para cliente
        try:
            error_msg = ErrorMessage(
                message=str(e),
                details=f"Erro ao processar CAR: {numero_car}"
            )
            await websocket.send_json(error_msg.model_dump())
        except:
            pass  # WebSocket pode já estar fechado

    finally:
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
