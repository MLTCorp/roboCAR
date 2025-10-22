"""
Script de teste para WebSocket CAR
Testa o fluxo completo incluindo processamento de shapefile para GeoJSON
"""
import asyncio
import websockets
import json
import uuid
from pathlib import Path

# Configurações
BACKEND_URL = "ws://localhost:8000/ws/car"
NUMERO_CAR = "PI-2202307-333D805751534B5D8B5E124C1F010E17"
CLIENTE_ID = "9c05c52c-2a78-4ec1-82ad-c9e6d49d6a7f"  # Cliente de teste existente


async def testar_websocket_car():
    """Testa consulta CAR via WebSocket"""

    print(f"[*] Iniciando teste de consulta CAR")
    print(f"[*] Numero CAR: {NUMERO_CAR}")
    print(f"[*] Cliente ID: {CLIENTE_ID}")
    print(f"[*] Conectando em: {BACKEND_URL}/{NUMERO_CAR}")
    print("-" * 80)

    uri = f"{BACKEND_URL}/{NUMERO_CAR}"

    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] WebSocket conectado!")

            # Enviar configuração inicial
            config = {"cliente_id": CLIENTE_ID}
            await websocket.send(json.dumps(config))
            print(f"[>>] Configuracao enviada: {config}")
            print("-" * 80)

            # Loop para receber mensagens
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    msg_type = data.get("type")

                    print(f"\n[<<] Mensagem recebida: {msg_type}")

                    if msg_type == "progress":
                        etapa = data.get("etapa")
                        mensagem = data.get("mensagem")
                        print(f"   [PROGRESSO] [{etapa}] {mensagem}")

                    elif msg_type == "captcha_required":
                        print(f"   [CAPTCHA] CAPTCHA requerido!")
                        image_b64 = data.get("image")
                        print(f"   [CAPTCHA] Imagem CAPTCHA recebida ({len(image_b64)} bytes)")

                        # Salvar imagem para visualizacao
                        import base64
                        img_bytes = base64.b64decode(image_b64)
                        img_path = Path("captcha_test.png")
                        with open(img_path, "wb") as f:
                            f.write(img_bytes)
                        print(f"   [CAPTCHA] Imagem salva em: {img_path.absolute()}")

                        # Solicitar CAPTCHA ao usuario
                        print("\n" + "=" * 80)
                        print("[!] Por favor, abra o arquivo 'captcha_test.png' e digite o codigo:")
                        captcha_text = input("   Digite o CAPTCHA: ").strip().upper()
                        print("=" * 80 + "\n")

                        # Enviar resposta
                        response = {"captcha_text": captcha_text}
                        await websocket.send(json.dumps(response))
                        print(f"   [>>] CAPTCHA enviado: {captcha_text}")

                    elif msg_type == "completed":
                        print(f"   [OK] CONSULTA CONCLUIDA!")
                        print(f"\n{'=' * 80}")
                        print("RESULTADOS:")
                        print(f"{'=' * 80}")

                        consulta_id = data.get("consulta_id")
                        info_popup = data.get("info_popup", {})
                        geojson_layers = data.get("geojson_layers", {})

                        print(f"\n[ID] Consulta ID: {consulta_id}")

                        print(f"\n[INFO] Dados do Popup:")
                        for key, value in info_popup.items():
                            print(f"   - {key}: {value}")

                        print(f"\n[GEOJSON] Camadas GeoJSON:")
                        if geojson_layers:
                            for layer_name, geojson in geojson_layers.items():
                                features = geojson.get("features", [])
                                metadata = geojson.get("metadata", {})
                                print(f"   - {layer_name}:")
                                print(f"      * Features: {len(features)}")
                                print(f"      * Total features: {metadata.get('total_features')}")
                                print(f"      * Bounds: {metadata.get('bounds')}")
                                print(f"      * CRS: {metadata.get('crs')}")
                        else:
                            print("   [!] Nenhuma camada GeoJSON encontrada")

                        print(f"\n{'=' * 80}")
                        print(f"[OK] Teste concluido com sucesso!")
                        print(f"{'=' * 80}")
                        break

                    elif msg_type == "error":
                        error_msg = data.get("message")
                        error_details = data.get("details")
                        print(f"   [ERROR] ERRO: {error_msg}")
                        if error_details:
                            print(f"   [ERROR] Detalhes: {error_details}")
                        break

                    else:
                        print(f"   [?] Tipo desconhecido: {data}")

                except websockets.exceptions.ConnectionClosed:
                    print("\n[!] Conexao WebSocket fechada")
                    break
                except json.JSONDecodeError as e:
                    print(f"\n[ERROR] Erro ao decodificar JSON: {e}")
                    break

    except Exception as e:
        print(f"\n[ERROR] Erro na conexao: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TESTE DE CONSULTA CAR VIA WEBSOCKET")
    print("=" * 80 + "\n")

    asyncio.run(testar_websocket_car())

    print("\n\nPROXIMOS PASSOS:")
    print("   1. Verifique os dados no Supabase:")
    print("      https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit")
    print("   2. Tabela: duploa_consultas_car")
    print(f"   3. Procure pelo cliente_id: {CLIENTE_ID}")
    print("   4. Verifique o campo 'geojson_layers'\n")
