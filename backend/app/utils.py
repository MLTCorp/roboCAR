"""
Utilidades gerais para o roboCAR
"""
import re
import logging

logger = logging.getLogger(__name__)


def normalizar_numero_car(numero_car: str) -> str:
    """
    Normaliza o número CAR removendo pontos e caracteres inválidos.

    Formato esperado: SC-4215075-3B95B0823AD74A2C87B23F8B310F8B2D
    Formato INVÁLIDO: SC-4215075-3B95.B082.3AD7.4A2C.87B2.3F8B.310F.8B2D

    Args:
        numero_car: Número do CAR (pode conter pontos)

    Returns:
        Número do CAR normalizado (sem pontos)

    Examples:
        >>> normalizar_numero_car("SC-4215075-3B95.B082.3AD7")
        "SC-4215075-3B95B0823AD7"

        >>> normalizar_numero_car("SC-4215075-3B95B0823AD7")
        "SC-4215075-3B95B0823AD7"
    """
    numero_original = numero_car

    # Remover todos os pontos
    numero_normalizado = numero_car.replace(".", "")

    # Log se houve modificação
    if numero_original != numero_normalizado:
        logger.info(f"Número CAR normalizado:")
        logger.info(f"  Original: {numero_original}")
        logger.info(f"  Normalizado: {numero_normalizado}")
        logger.info(f"  Pontos removidos: {numero_original.count('.')}")

    return numero_normalizado


def validar_formato_car(numero_car: str) -> bool:
    """
    Valida o formato básico do número CAR.

    Formato esperado: UF-NUMERO-HASH
    Exemplo: SC-4215075-3B95B0823AD74A2C87B23F8B310F8B2D

    Args:
        numero_car: Número do CAR para validar

    Returns:
        True se formato é válido, False caso contrário
    """
    # Padrão básico: XX-NUMEROS-HASH (mínimo)
    # UF: 2 letras
    # Hífen
    # Número: pelo menos 1 dígito
    # Hífen
    # Hash: pelo menos 1 caractere alfanumérico
    pattern = r'^[A-Z]{2}-\d+-[A-Z0-9]+$'

    is_valid = bool(re.match(pattern, numero_car))

    if not is_valid:
        logger.warning(f"Número CAR com formato inválido: {numero_car}")
        logger.warning(f"  Formato esperado: UF-NUMERO-HASH (ex: SC-4215075-3B95B0823AD7...)")

    return is_valid
