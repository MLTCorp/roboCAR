#!/usr/bin/env python3
"""
Script de teste para WebSocket do roboCAR
"""

import asyncio
import websockets
import json
import sys

async def test_car_websocket(numero_car: str, cliente_id: str = "00000000-0000-0000-0000-000000000000"):
    """
    Testa a conexão WebSocket e o fluxo de consulta CAR
    """
    uri = f"ws://localhost:8000/ws/car/{numero_car}"

    print(f"\n{'='*60}")
    print(f"TESTE WEBSOCKET - roboCAR")
    print(f"{'='*60}")
    print(f"Conectando em: {uri}")
    print(f"Cliente ID: {cliente_id}")
    print(f"{'='*60}\n")

    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] Conexao WebSocket estabelecida!")

            # Enviar cliente_id
            inicial_msg = {"cliente_id": cliente_id}
            await websocket.send(json.dumps(inicial_msg))
            print(f"[->] Enviado: {inicial_msg}\n")

            # Receber mensagens
            print("Aguardando mensagens do servidor...\n")

            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=120.0)
                    data = json.loads(message)

                    msg_type = data.get('type', 'unknown')

                    if msg_type == 'progress':
                        etapa = data.get('etapa', '')
                        mensagem = data.get('mensagem', '')
                        print(f"[PROGRESSO] {etapa}")
                        print(f"    {mensagem}\n")

                    elif msg_type == 'captcha_required':
                        print(f"[CAPTCHA] CAPTCHA NECESSARIO!")
                        print(f"    Imagem base64 recebida (tamanho: {len(data.get('image', ''))} chars)")

                        # Solicitar resolução do CAPTCHA
                        captcha_text = input("\n    Digite o texto do CAPTCHA: ").strip()
                        captcha_msg = {"captcha_text": captcha_text}
                        await websocket.send(json.dumps(captcha_msg))
                        print(f"    [->] CAPTCHA enviado: {captcha_text}\n")

                    elif msg_type == 'completed':
                        print(f"\n[OK] CONSULTA CONCLUIDA COM SUCESSO!")
                        print(f"\n{'='*60}")
                        print("RESULTADO:")
                        print(f"{'='*60}")
                        print(json.dumps(data, indent=2, ensure_ascii=False))
                        print(f"{'='*60}\n")
                        break

                    elif msg_type == 'error':
                        erro = data.get('erro', 'Erro desconhecido')
                        print(f"\n[ERRO] {erro}\n")
                        break

                    else:
                        print(f"[?] Mensagem desconhecida: {data}\n")

                except asyncio.TimeoutError:
                    print("[!] Timeout aguardando resposta do servidor")
                    break

    except websockets.exceptions.ConnectionClosed:
        print("[ERRO] Conexao WebSocket fechada pelo servidor")

    except Exception as e:
        print(f"[ERRO] Erro: {type(e).__name__}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_websocket.py <NUMERO_CAR> [CLIENTE_ID]")
        print("\nExemplo:")
        print("  python test_websocket.py MS-5007901-C252AF6443F04FC3BDCFC7AFD3357053")
        sys.exit(1)

    numero_car = sys.argv[1]
    cliente_id = sys.argv[2] if len(sys.argv) > 2 else "00000000-0000-0000-0000-000000000000"

    asyncio.run(test_car_websocket(numero_car, cliente_id))
