"""
Reprocessa uma consulta existente para adicionar GeoJSON
Baixa o shapefile do Storage e processa localmente
"""
import sys
sys.path.insert(0, 'backend')

from app.shapefile_processor import processar_shapefile_car
from supabase import create_client
import os
from dotenv import load_dotenv
import requests

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ID da consulta que queremos reprocessar
CONSULTA_ID = "b2b17225-42ec-45b4-9cba-caf9f181d8b7"

print(f"[*] Reprocessando consulta: {CONSULTA_ID}")

# Buscar consulta
consulta = supabase.table("duploa_consultas_car").select("*").eq("id", CONSULTA_ID).single().execute()

if not consulta.data:
    print("[ERROR] Consulta não encontrada!")
    sys.exit(1)

shapefile_url = consulta.data.get("shapefile_url")
if not shapefile_url:
    print("[ERROR] Consulta não tem shapefile_url!")
    sys.exit(1)

print(f"[*] Shapefile URL: {shapefile_url}")

# Baixar shapefile
print("[*] Baixando shapefile...")
response = requests.get(shapefile_url)
shapefile_path = "temp_shapefile.zip"

with open(shapefile_path, "wb") as f:
    f.write(response.content)

print(f"[OK] Shapefile baixado: {len(response.content)} bytes")

# Processar
print("[*] Processando shapefile...")
try:
    geojson_layers = processar_shapefile_car(shapefile_path)
    print(f"[OK] {len(geojson_layers)} camadas processadas")

    for layer_name, geojson in geojson_layers.items():
        features = geojson.get("features", [])
        print(f"  - {layer_name}: {len(features)} features")

    # Atualizar no banco
    print("[*] Atualizando banco de dados...")
    supabase.table("duploa_consultas_car").update({
        "geojson_layers": geojson_layers
    }).eq("id", CONSULTA_ID).execute()

    print("[OK] Consulta atualizada com sucesso!")
    print(f"\n[INFO] Verifique no Supabase:")
    print(f"  https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit")
    print(f"  Tabela: duploa_consultas_car")
    print(f"  ID: {CONSULTA_ID}")

except Exception as e:
    print(f"[ERROR] Erro no processamento: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Limpar arquivo temporário
    if os.path.exists(shapefile_path):
        os.remove(shapefile_path)
