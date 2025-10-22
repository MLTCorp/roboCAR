"""Teste direto do processador de shapefile"""
import sys
sys.path.insert(0, 'backend')

from app.shapefile_processor import processar_shapefile_car
import json

print("[*] Testando processador de shapefile...")
print("[*] Arquivo: test_shapefile.zip")

try:
    geojson_layers = processar_shapefile_car("test_shapefile.zip")

    print(f"\n[OK] Processamento concluido!")
    print(f"[OK] {len(geojson_layers)} camadas encontradas")
    print(f"\n[INFO] Camadas:")

    for layer_name, geojson in geojson_layers.items():
        features = geojson.get("features", [])
        metadata = geojson.get("metadata", {})
        print(f"  - {layer_name}:")
        print(f"      Features: {len(features)}")
        print(f"      Total: {metadata.get('total_features')}")
        print(f"      Bounds: {metadata.get('bounds')}")

    # Salvar em arquivo para inspecao
    with open("geojson_result.json", "w") as f:
        json.dump(geojson_layers, f, indent=2)
    print(f"\n[OK] Resultado salvo em: geojson_result.json")

except Exception as e:
    print(f"\n[ERROR] Erro no processamento: {e}")
    import traceback
    traceback.print_exc()
