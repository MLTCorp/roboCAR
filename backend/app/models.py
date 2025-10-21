"""
Modelos Pydantic para validação de dados
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class CarDownloadRequest(BaseModel):
    """Request para iniciar download de CAR"""
    numero_car: str = Field(..., description="Número do CAR", min_length=10)
    cliente_id: str = Field(..., description="ID do cliente no Supabase")


class CaptchaSolution(BaseModel):
    """Solução do CAPTCHA enviada pelo frontend"""
    captcha_text: str = Field(..., min_length=1, max_length=20)


class WebSocketMessage(BaseModel):
    """Mensagem genérica do WebSocket"""
    type: str
    data: Optional[Dict[str, Any]] = None


class ProgressMessage(WebSocketMessage):
    """Mensagem de progresso"""
    type: str = "progress"
    etapa: str
    mensagem: str


class CaptchaMessage(WebSocketMessage):
    """Mensagem de CAPTCHA necessário"""
    type: str = "captcha_required"
    image: str  # Base64


class CompletedMessage(WebSocketMessage):
    """Mensagem de conclusão"""
    type: str = "completed"
    consulta_id: str
    numero_car: str
    shapefile_url: Optional[str] = None
    dados_extraidos: Dict[str, Any]


class ErrorMessage(WebSocketMessage):
    """Mensagem de erro"""
    type: str = "error"
    message: str
    details: Optional[str] = None


class ConsultaCAR(BaseModel):
    """Modelo de consulta CAR no Supabase"""
    id: Optional[str] = None
    cliente_id: str
    numero_car: str
    status: str = "processando"
    status_cadastro: Optional[str] = None
    tipo_imovel: Optional[str] = None
    municipio: Optional[str] = None
    area_total: Optional[str] = None
    dados_demonstrativo: Optional[Dict[str, Any]] = None
    shapefile_url: Optional[str] = None
    shapefile_size: Optional[int] = None
    erro_mensagem: Optional[str] = None
    consulta_iniciada_em: Optional[datetime] = None
    consulta_concluida_em: Optional[datetime] = None
