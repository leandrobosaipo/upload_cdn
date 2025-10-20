#!/usr/bin/env python3
"""
Script de teste final para validar todas as correções da API de upload
"""

import os
import tempfile
import requests
import json
import time
from pathlib import Path

def create_test_file(size_mb=1, filename="test.txt"):
    """Cria um arquivo de teste com tamanho específico"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{filename}') as f:
        data = b'X' * (size_mb * 1024 * 1024)
        f.write(data)
        return f.name

def test_file_validation():
    """Testa a validação de arquivos"""
    print("🧪 Testando validação de arquivos...")
    
    # Teste 1: Arquivo válido
    test_file = create_test_file(0.1, "test.mp4")
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f, 'video/mp4')}
            response = requests.post('http://localhost:8080/upload', files=files)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload de arquivo válido funcionando")
            print(f"   Tamanho retornado: {data.get('size')} bytes")
            return True
        else:
            print(f"❌ Erro no upload: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ API não está rodando. Execute 'python app.py' primeiro.")
        return False
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_file_size_calculation():
    """Testa o cálculo correto do tamanho do arquivo"""
    print("\n🧪 Testando cálculo do tamanho do arquivo...")
    
    sizes_to_test = [0.1, 0.5, 1, 2]  # MB
    results = []
    
    for size_mb in sizes_to_test:
        test_file = create_test_file(size_mb, f"test_{size_mb}mb.mp4")
        expected_size = os.path.getsize(test_file)
        
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (os.path.basename(test_file), f, 'video/mp4')}
                response = requests.post('http://localhost:8080/upload', files=files)
            
            if response.status_code == 200:
                data = response.json()
                returned_size = data.get('size', 0)
                
                if returned_size == expected_size:
                    print(f"✅ {size_mb}MB - Tamanho correto: {returned_size} bytes")
                    results.append(True)
                else:
                    print(f"❌ {size_mb}MB - Tamanho incorreto. Esperado: {expected_size}, Recebido: {returned_size}")
                    results.append(False)
            else:
                print(f"❌ {size_mb}MB - Erro HTTP: {response.status_code}")
                results.append(False)
        
        except Exception as e:
            print(f"❌ {size_mb}MB - Erro: {e}")
            results.append(False)
        
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
    
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Resultado do cálculo de tamanho: {passed}/{total} testes passaram")
    return passed == total

def test_large_file_support():
    """Testa suporte a arquivos grandes"""
    print("\n🧪 Testando suporte a arquivos grandes...")
    
    # Teste com arquivo de 5MB (dentro do limite de 100MB)
    test_file = create_test_file(5, "large_test.mp4")
    expected_size = os.path.getsize(test_file)
    
    try:
        print(f"📁 Testando arquivo de {expected_size / 1024 / 1024:.1f}MB...")
        
        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f, 'video/mp4')}
            response = requests.post('http://localhost:8080/upload', files=files)
        
        if response.status_code == 200:
            data = response.json()
            returned_size = data.get('size', 0)
            
            if returned_size == expected_size:
                print(f"✅ Arquivo grande processado com sucesso: {returned_size} bytes")
                return True
            else:
                print(f"❌ Tamanho incorreto para arquivo grande. Esperado: {expected_size}, Recebido: {returned_size}")
                return False
        else:
            print(f"❌ Erro no upload de arquivo grande: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Erro no teste de arquivo grande: {e}")
        return False
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_error_handling():
    """Testa o tratamento de erros"""
    print("\n🧪 Testando tratamento de erros...")
    
    # Teste 1: Sem arquivo
    try:
        response = requests.post('http://localhost:8080/upload')
        if response.status_code == 400:
            data = response.json()
            if "Nenhum arquivo fornecido" in data.get('error', ''):
                print("✅ Erro 'sem arquivo' tratado corretamente")
            else:
                print("❌ Mensagem de erro incorreta para 'sem arquivo'")
                return False
        else:
            print(f"❌ Status code incorreto para 'sem arquivo': {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro no teste de 'sem arquivo': {e}")
        return False
    
    # Teste 2: Arquivo sem nome
    try:
        files = {'file': ('', b'content', 'text/plain')}
        response = requests.post('http://localhost:8080/upload', files=files)
        if response.status_code == 400:
            data = response.json()
            if "Arquivo sem nome" in data.get('error', ''):
                print("✅ Erro 'arquivo sem nome' tratado corretamente")
                return True
            else:
                print("❌ Mensagem de erro incorreta para 'arquivo sem nome'")
                return False
        else:
            print(f"❌ Status code incorreto para 'arquivo sem nome': {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro no teste de 'arquivo sem nome': {e}")
        return False

def test_health_endpoint():
    """Testa o endpoint de health check"""
    print("\n🧪 Testando endpoint de health check...")
    
    try:
        response = requests.get('http://localhost:8080/health')
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print("✅ Health check funcionando")
                return True
            else:
                print("❌ Status de health check incorreto")
                return False
        else:
            print(f"❌ Erro no health check: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro no teste de health check: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Teste Final da Upload CDN API")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Validação de Arquivos", test_file_validation),
        ("Cálculo de Tamanho", test_file_size_calculation),
        ("Arquivos Grandes", test_large_file_support),
        ("Tratamento de Erros", test_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
            print(f"✅ {test_name} - PASSOU")
        else:
            print(f"❌ {test_name} - FALHOU")
    
    print("\n" + "=" * 50)
    print(f"📊 Resultado Final: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ API está pronta para produção!")
        print("\n📋 Próximos passos:")
        print("1. git add .")
        print("2. git commit -m 'fix: melhorar robustez do upload e cálculo de tamanho'")
        print("3. git push")
        print("4. Redeploy no Easypanel")
    else:
        print("❌ Alguns testes falharam. Verifique os erros acima.")
        return False
    
    return True

if __name__ == "__main__":
    main()
