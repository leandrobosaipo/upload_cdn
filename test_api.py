#!/usr/bin/env python3
"""
Script de teste para a Upload CDN API
"""

import requests
import os
import sys
from pathlib import Path

# Configuração da API
API_BASE_URL = "http://localhost:8080"  # Mude para sua URL do Easypanel

def test_health():
    """Testa o endpoint de health check"""
    print("🔍 Testando health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check OK")
            print(f"   Resposta: {response.json()}")
        else:
            print(f"❌ Health check falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no health check: {e}")

def test_info():
    """Testa o endpoint de informações"""
    print("\n🔍 Testando informações da API...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            print("✅ Info endpoint OK")
            print(f"   Resposta: {response.json()}")
        else:
            print(f"❌ Info endpoint falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no info endpoint: {e}")

def create_test_file():
    """Cria um arquivo de teste"""
    test_content = "Este é um arquivo de teste para a API de upload"
    test_file = "teste.txt"
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    return test_file

def test_upload():
    """Testa o upload de arquivo"""
    print("\n🔍 Testando upload de arquivo...")
    
    # Criar arquivo de teste
    test_file = create_test_file()
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": (test_file, f, "text/plain")}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload realizado com sucesso!")
            print(f"   URL: {data.get('url')}")
            print(f"   Filename: {data.get('filename')}")
            print(f"   Original: {data.get('original_filename')}")
        else:
            print(f"❌ Upload falhou: {response.status_code}")
            print(f"   Erro: {response.text}")
    
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
    
    finally:
        # Limpar arquivo de teste
        if os.path.exists(test_file):
            os.remove(test_file)

def test_invalid_file():
    """Testa upload com arquivo inválido"""
    print("\n🔍 Testando upload com arquivo inválido...")
    
    try:
        # Tentar upload sem arquivo
        response = requests.post(f"{API_BASE_URL}/upload")
        
        if response.status_code == 400:
            print("✅ Validação de arquivo funcionando")
            print(f"   Erro esperado: {response.json()}")
        else:
            print(f"❌ Validação não funcionou: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Erro no teste de validação: {e}")

def main():
    """Função principal"""
    print("🚀 Iniciando testes da Upload CDN API")
    print(f"   URL base: {API_BASE_URL}")
    print("-" * 50)
    
    # Verificar se a API está rodando
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API não está respondendo. Verifique se está rodando.")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Não foi possível conectar à API. Verifique a URL e se está rodando.")
        print("   Para testar localmente, execute: python app.py")
        sys.exit(1)
    
    # Executar testes
    test_health()
    test_info()
    test_upload()
    test_invalid_file()
    
    print("\n" + "=" * 50)
    print("✅ Testes concluídos!")

if __name__ == "__main__":
    main()
