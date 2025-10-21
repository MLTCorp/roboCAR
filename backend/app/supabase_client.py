"""
Cliente Supabase para persistência de dados
"""
from supabase import create_client, Client
from .config import settings
import logging

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Cliente singleton do Supabase"""

    _instance: Client = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("Inicializando cliente Supabase...")
            cls._instance = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            logger.info("Cliente Supabase inicializado com sucesso")
        return cls._instance


# Singleton instance
supabase_client = SupabaseClient()
