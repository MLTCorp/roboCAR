"""Teste simples de conexao"""
import requests

# Testar HTTP
print("[*] Testando endpoint HTTP...")
response = requests.get("http://localhost:8000/")
print(f"[OK] Status: {response.status_code}")
print(f"[OK] Response: {response.json()}")

#Testar health
print("\n[*] Testando /health...")
response = requests.get("http://localhost:8000/health")
print(f"[OK] Status: {response.status_code}")
print(f"[OK] Response: {response.json()}")
