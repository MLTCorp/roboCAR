"""
Teste simples para normalização de números CAR
"""
import sys
sys.path.insert(0, 'backend')

from app.utils import normalizar_numero_car, validar_formato_car


def test_normalizar_numero_car():
    """Testa normalização de números CAR"""

    # Teste 1: Número com pontos (INVÁLIDO -> normalizar)
    entrada1 = "SC-4215075-3B95.B082.3AD7.4A2C.87B2.3F8B.310F.8B2D"
    esperado1 = "SC-4215075-3B95B0823AD74A2C87B23F8B310F8B2D"
    resultado1 = normalizar_numero_car(entrada1)

    print(f"Teste 1: Remover pontos")
    print(f"  Entrada: {entrada1}")
    print(f"  Esperado: {esperado1}")
    print(f"  Resultado: {resultado1}")
    print(f"  Status: {'PASSOU' if resultado1 == esperado1 else 'FALHOU'}\n")

    assert resultado1 == esperado1, f"Esperado {esperado1}, mas obteve {resultado1}"

    # Teste 2: Número sem pontos (já válido)
    entrada2 = "SC-4215075-3B95B0823AD74A2C87B23F8B310F8B2D"
    esperado2 = "SC-4215075-3B95B0823AD74A2C87B23F8B310F8B2D"
    resultado2 = normalizar_numero_car(entrada2)

    print(f"Teste 2: Número já normalizado")
    print(f"  Entrada: {entrada2}")
    print(f"  Esperado: {esperado2}")
    print(f"  Resultado: {resultado2}")
    print(f"  Status: {'OK PASSOU' if resultado2 == esperado2 else 'ERRO FALHOU'}\n")

    assert resultado2 == esperado2, f"Esperado {esperado2}, mas obteve {resultado2}"

    # Teste 3: Múltiplos pontos
    entrada3 = "SC-4211009-B4CE.1CE5.C114.4FE5.9A08.9463.A504.F0C4"
    esperado3 = "SC-4211009-B4CE1CE5C1144FE59A089463A504F0C4"
    resultado3 = normalizar_numero_car(entrada3)

    print(f"Teste 3: Múltiplos pontos")
    print(f"  Entrada: {entrada3}")
    print(f"  Esperado: {esperado3}")
    print(f"  Resultado: {resultado3}")
    print(f"  Status: {'OK PASSOU' if resultado3 == esperado3 else 'ERRO FALHOU'}\n")

    assert resultado3 == esperado3, f"Esperado {esperado3}, mas obteve {resultado3}"

    print("=" * 60)
    print("OK Todos os testes de normalização passaram!")
    print("=" * 60)


def test_validar_formato_car():
    """Testa validação de formato de números CAR"""

    # Teste 1: Formato válido
    car_valido = "SC-4215075-3B95B0823AD74A2C87B23F8B310F8B2D"
    resultado1 = validar_formato_car(car_valido)

    print(f"\nTeste Validação 1: Formato válido")
    print(f"  Entrada: {car_valido}")
    print(f"  Válido: {resultado1}")
    print(f"  Status: {'OK PASSOU' if resultado1 else 'ERRO FALHOU'}\n")

    assert resultado1, f"Número CAR válido foi rejeitado: {car_valido}"

    # Teste 2: Formato inválido (com pontos)
    car_invalido = "SC-4215075-3B95.B082.3AD7"
    resultado2 = validar_formato_car(car_invalido)

    print(f"Teste Validação 2: Formato inválido (com pontos)")
    print(f"  Entrada: {car_invalido}")
    print(f"  Válido: {resultado2}")
    print(f"  Status: {'OK PASSOU' if not resultado2 else 'ERRO FALHOU'}\n")

    assert not resultado2, f"Número CAR inválido foi aceito: {car_invalido}"

    # Teste 3: Formato curto mas válido
    car_curto = "SC-123-ABC"
    resultado3 = validar_formato_car(car_curto)

    print(f"Teste Validação 3: Formato curto mas válido")
    print(f"  Entrada: {car_curto}")
    print(f"  Válido: {resultado3}")
    print(f"  Status: {'OK PASSOU' if resultado3 else 'ERRO FALHOU'}\n")

    assert resultado3, f"Número CAR válido foi rejeitado: {car_curto}"

    print("=" * 60)
    print("OK Todos os testes de validação passaram!")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("TESTANDO NORMALIZAÇÃO DE NÚMEROS CAR")
    print("=" * 60)
    print()

    try:
        test_normalizar_numero_car()
        test_validar_formato_car()

        print("\n" + "=" * 60)
        print("OKOKOK TODOS OS TESTES PASSARAM COM SUCESSO! OKOKOK")
        print("=" * 60)

    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"ERROERROERRO TESTE FALHOU: {e}")
        print("=" * 60)
        sys.exit(1)
