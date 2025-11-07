#!/usr/bin/env python3
"""
Script de teste para a Upload CDN API
Testa todos os endpoints incluindo validações e tratamento de erros
"""

import requests
import os
import sys
from pathlib import Path
import tempfile

# Configuração da API
API_BASE_URL = "http://localhost:8080"  # Mude para sua URL do Easypanel

def test_health():
    """Testa o endpoint de health check"""
    print("🔍 Testando health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Resposta: {data}")
        
        if response.status_code == 200:
            assert data.get("status") == "healthy", "Status deve ser 'healthy'"
            print("✅ Health check OK")
        elif response.status_code == 503:
            print("⚠️ Health check retornou unhealthy (pode ser esperado se credenciais não estiverem configuradas)")
        else:
            print(f"❌ Health check falhou com status inesperado: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no health check: {e}")

def test_info():
    """Testa o endpoint de informações"""
    print("\n🔍 Testando informações da API...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            assert "message" in data, "Resposta deve conter 'message'"
            assert "endpoints" in data, "Resposta deve conter 'endpoints'"
            assert "supported_formats" in data, "Resposta deve conter 'supported_formats'"
            print("✅ Info endpoint OK")
            print(f"   Versão: {data.get('version')}")
            print(f"   Formatos suportados: {len(data.get('supported_formats', []))}")
        else:
            print(f"❌ Info endpoint falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no info endpoint: {e}")

def test_swagger_docs():
    """Testa o endpoint de documentação Swagger"""
    print("\n🔍 Testando documentação Swagger (/docs)...")
    try:
        response = requests.get(f"{API_BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ Swagger UI acessível")
        else:
            print(f"⚠️ Swagger UI retornou status: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao acessar Swagger UI: {e}")

def test_swagger_json():
    """Testa o endpoint de especificação OpenAPI"""
    print("\n🔍 Testando especificação OpenAPI (/swagger.json)...")
    try:
        response = requests.get(f"{API_BASE_URL}/swagger.json")
        if response.status_code == 200:
            data = response.json()
            assert "openapi" in data, "Deve conter campo 'openapi'"
            assert "paths" in data, "Deve conter campo 'paths'"
            assert "/upload" in data.get("paths", {}), "Deve conter endpoint /upload"
            print("✅ Swagger JSON válido")
            print(f"   Versão OpenAPI: {data.get('openapi')}")
            print(f"   Endpoints documentados: {len(data.get('paths', {}))}")
        else:
            print(f"❌ Swagger JSON falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao acessar Swagger JSON: {e}")

def create_test_file(extension="txt", size_kb=1):
    """Cria um arquivo de teste"""
    test_content = "X" * (size_kb * 1024)  # Criar arquivo com tamanho específico
    test_file = f"teste.{extension}"
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    return test_file

def test_upload_success():
    """Testa o upload de arquivo válido"""
    print("\n🔍 Testando upload de arquivo válido...")
    
    # Criar arquivo de teste válido (imagem)
    test_file = create_test_file("jpg", size_kb=10)
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": (test_file, f, "image/jpeg")}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Resposta deve ter success=True"
            assert "url" in data, "Resposta deve conter 'url'"
            assert "filename" in data, "Resposta deve conter 'filename'"
            assert "size" in data, "Resposta deve conter 'size'"
            print("✅ Upload realizado com sucesso!")
            print(f"   URL: {data.get('url')}")
            print(f"   Filename: {data.get('filename')}")
            print(f"   Size: {data.get('size')} bytes")
        else:
            print(f"⚠️ Upload retornou status: {response.status_code}")
            print(f"   Resposta: {response.json()}")
    
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
    
    finally:
        # Limpar arquivo de teste
        if os.path.exists(test_file):
            os.remove(test_file)

def test_upload_no_file():
    """Testa upload sem arquivo"""
    print("\n🔍 Testando upload sem arquivo...")
    
    try:
        response = requests.post(f"{API_BASE_URL}/upload")
        
        if response.status_code == 400:
            data = response.json()
            assert data.get("success") == False, "Resposta deve ter success=False"
            assert "error" in data, "Resposta deve conter 'error'"
            assert "detail" in data, "Resposta deve conter 'detail'"
            print("✅ Validação de arquivo ausente funcionando")
            print(f"   Erro: {data.get('error')}")
        else:
            print(f"❌ Validação não funcionou: {response.status_code}")
            print(f"   Resposta: {response.text}")
    
    except Exception as e:
        print(f"❌ Erro no teste de validação: {e}")

def test_upload_invalid_type():
    """Testa upload com tipo de arquivo inválido"""
    print("\n🔍 Testando upload com tipo de arquivo inválido...")
    
    # Criar arquivo com extensão não permitida
    test_file = create_test_file("exe", size_kb=1)
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": (test_file, f, "application/x-msdownload")}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        if response.status_code == 400:
            data = response.json()
            assert data.get("success") == False, "Resposta deve ter success=False"
            assert "error" in data, "Resposta deve conter 'error'"
            assert "tipo de arquivo" in data.get("error", "").lower(), "Erro deve mencionar tipo de arquivo"
            print("✅ Validação de tipo de arquivo funcionando")
            print(f"   Erro: {data.get('error')}")
        else:
            print(f"⚠️ Retornou status: {response.status_code}")
            print(f"   Resposta: {response.json()}")
    
    except Exception as e:
        print(f"❌ Erro no teste de tipo inválido: {e}")
    
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_upload_empty_filename():
    """Testa upload com arquivo sem nome"""
    print("\n🔍 Testando upload com arquivo sem nome...")
    
    try:
        # Criar arquivo temporário sem nome
        files = {"file": ("", b"conteudo", "text/plain")}
        response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        if response.status_code == 400:
            data = response.json()
            assert data.get("success") == False, "Resposta deve ter success=False"
            print("✅ Validação de arquivo sem nome funcionando")
            print(f"   Erro: {data.get('error')}")
        else:
            print(f"⚠️ Retornou status: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Erro no teste de arquivo sem nome: {e}")

def test_404_handler():
    """Testa o handler de erro 404"""
    print("\n🔍 Testando handler de erro 404...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/rota-inexistente")
        
        if response.status_code == 404:
            data = response.json()
            assert data.get("success") == False, "Resposta deve ter success=False"
            assert "error" in data, "Resposta deve conter 'error'"
            assert "detail" in data, "Resposta deve conter 'detail'"
            print("✅ Handler de 404 funcionando")
            print(f"   Erro: {data.get('error')}")
        else:
            print(f"⚠️ Retornou status: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Erro no teste de 404: {e}")

def test_405_handler():
    """Testa o handler de erro 405 (Method Not Allowed)"""
    print("\n🔍 Testando handler de erro 405...")
    
    try:
        # Tentar usar método não permitido (DELETE no /upload)
        response = requests.delete(f"{API_BASE_URL}/upload")
        
        if response.status_code == 405:
            data = response.json()
            assert data.get("success") == False, "Resposta deve ter success=False"
            assert "error" in data, "Resposta deve conter 'error'"
            print("✅ Handler de 405 funcionando")
            print(f"   Erro: {data.get('error')}")
        else:
            print(f"⚠️ Retornou status: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Erro no teste de 405: {e}")

def main():
    """Função principal"""
    print("🚀 Iniciando testes da Upload CDN API")
    print(f"   URL base: {API_BASE_URL}")
    print("=" * 50)
    
    # Verificar se a API está rodando
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code not in [200, 503]:
            print("❌ API não está respondendo corretamente. Verifique se está rodando.")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Não foi possível conectar à API. Verifique a URL e se está rodando.")
        print("   Para testar localmente, execute: python app.py")
        sys.exit(1)
    
    # Executar testes
    test_health()
    test_info()
    test_swagger_docs()
    test_swagger_json()
    test_upload_no_file()
    test_upload_empty_filename()
    test_upload_invalid_type()
    test_404_handler()
    test_405_handler()
    
    # Teste de upload real (pode falhar se credenciais não estiverem configuradas)
    print("\n" + "-" * 50)
    print("⚠️ Teste de upload real (requer credenciais configuradas):")
    test_upload_success()
    
    print("\n" + "=" * 50)
    print("✅ Testes concluídos!")
    print("\n💡 Dica: Acesse /docs no navegador para ver a documentação interativa")

if __name__ == "__main__":
    main()
