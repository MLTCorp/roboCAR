"""
Script de teste para verificar conexão com Supabase
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Configurar encoding UTF-8 no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Carregar .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print("=" * 60)
print("TESTE DE CONEXAO SUPABASE")
print("=" * 60)
print(f"URL: {SUPABASE_URL}")
print(f"Key: {SUPABASE_KEY[:20]}...")
print("=" * 60)

# Criar cliente
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("[OK] Cliente Supabase criado com sucesso!")
except Exception as e:
    print(f"[ERRO] Erro ao criar cliente: {e}")
    exit(1)

# Teste 1: Verificar se tabela existe
print("\n[TESTE 1] Verificando tabela consultas_car...")
try:
    result = supabase.table("consultas_car").select("id").limit(1).execute()
    print(f"[OK] Tabela existe! Registros encontrados: {len(result.data)}")
except Exception as e:
    print(f"[ERRO] Tabela nao existe ou erro de acesso: {e}")
    print("\n[INFO] Execute o SQL em supabase-setup.sql no SQL Editor do Supabase!")

# Teste 2: Inserir registro de teste
print("\n[TESTE 2] Inserindo registro de teste...")
try:
    test_data = {
        "cliente_id": "00000000-0000-0000-0000-000000000000",
        "numero_car": "TESTE-CONEXAO-123",
        "status": "processando"
    }

    result = supabase.table("consultas_car").insert(test_data).execute()

    if result.data:
        print(f"[OK] Insert realizado com sucesso!")
        print(f"   ID criado: {result.data[0]['id']}")
        test_id = result.data[0]['id']
    else:
        print(f"[ERRO] Insert falhou: sem dados retornados")
        test_id = None

except Exception as e:
    print(f"[ERRO] Erro ao inserir: {e}")
    test_id = None

# Teste 3: Atualizar registro
if test_id:
    print("\n[TESTE 3] Atualizando registro de teste...")
    try:
        result = supabase.table("consultas_car").update({
            "status": "concluido",
            "status_cadastro": "Teste OK"
        }).eq("id", test_id).execute()

        print(f"[OK] Update realizado com sucesso!")

    except Exception as e:
        print(f"[ERRO] Erro ao atualizar: {e}")

# Teste 4: Buscar registro
if test_id:
    print("\n[TESTE 4] Buscando registro de teste...")
    try:
        result = supabase.table("consultas_car").select("*").eq("id", test_id).execute()

        if result.data:
            print(f"[OK] Select realizado com sucesso!")
            print(f"   Dados: {result.data[0]}")
        else:
            print(f"[ERRO] Nenhum dado encontrado")

    except Exception as e:
        print(f"[ERRO] Erro ao buscar: {e}")

# Teste 5: Deletar registro de teste
if test_id:
    print("\n[TESTE 5] Deletando registro de teste...")
    try:
        result = supabase.table("consultas_car").delete().eq("id", test_id).execute()
        print(f"[OK] Delete realizado com sucesso!")

    except Exception as e:
        print(f"[ERRO] Erro ao deletar: {e}")

# Teste 6: Verificar storage bucket
print("\n[TESTE 6] Verificando storage bucket 'car-shapefiles'...")
try:
    buckets = supabase.storage.list_buckets()

    car_bucket = next((b for b in buckets if b.name == "car-shapefiles"), None)

    if car_bucket:
        print(f"[OK] Bucket 'car-shapefiles' existe!")
        print(f"   ID: {car_bucket.id}")
        print(f"   Publico: {car_bucket.public}")
    else:
        print(f"[ERRO] Bucket 'car-shapefiles' nao encontrado")
        print(f"\n[INFO] Crie o bucket no Supabase Storage:")
        print(f"   https://supabase.com/dashboard/project/{SUPABASE_URL.split('//')[1].split('.')[0]}/storage/buckets")

except Exception as e:
    print(f"[ERRO] Erro ao verificar storage: {e}")

print("\n" + "=" * 60)
print("RESUMO DOS TESTES")
print("=" * 60)
print("[OK] = Passou | [ERRO] = Falhou | [INFO] = Acao necessaria")
print("=" * 60)
