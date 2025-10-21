"""
Configurações da aplicação
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configurações do backend"""

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # WebSocket
    websocket_timeout: int = 900  # 15 minutos

    # Rate Limiting
    enable_rate_limit: bool = False
    max_consultas_por_dia: int = 100

    # Logging
    log_level: str = "INFO"

    # Playwright
    headless: bool = True
    slow_mo: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origins(self) -> List[str]:
        """Retorna lista de origens permitidas"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


# Singleton
settings = Settings()
