#!/usr/bin/env python3
"""
Script para testar a correção do tamanho do arquivo
"""

import os
import tempfile
import requests
import json
from pathlib import Path

def create_test_file(size_mb=1):
    """Cria um arquivo de teste com tamanho específico"""
    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
        # Escrever dados para atingir o tamanho desejado
        data = b'X' * (size_mb * 1024 * 1024)
        f.write(data)
        return f.name

def test_file_size_correction():
    """Testa se a correção do tamanho do arquivo está funcionando"""
    print("🧪 Testando correção do tamanho do arquivo...")
    
    # Criar arquivo de teste de 1MB
    test_file = create_test_file(1)
    file_size = os.path.getsize(test_file)
    
    print(f"📁 Arquivo de teste criado: {test_file}")
    print(f"📏 Tamanho real do arquivo: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
    
    try:
        # Testar upload
        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f, 'text/plain')}
            
            # Usar URL local para teste
            response = requests.post('http://localhost:8080/upload', files=files)
        
        if response.status_code == 200:
            data = response.json()
            returned_size = data.get('size', 0)
            
            print(f"✅ Upload realizado com sucesso!")
            print(f"📊 Tamanho retornado pela API: {returned_size} bytes")
            print(f"📊 Tamanho real do arquivo: {file_size} bytes")
            
            if returned_size == file_size:
                print("✅ CORREÇÃO FUNCIONANDO! Tamanho correto retornado.")
                return True
            else:
                print(f"❌ ERRO: Tamanho incorreto. Esperado: {file_size}, Recebido: {returned_size}")
                return False
        else:
            print(f"❌ Erro no upload: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar à API. Execute 'python app.py' primeiro.")
        return False
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False
    
    finally:
        # Limpar arquivo de teste
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"🗑️  Arquivo de teste removido: {test_file}")

def test_different_sizes():
    """Testa com diferentes tamanhos de arquivo"""
    print("\n🧪 Testando com diferentes tamanhos...")
    
    sizes = [0.1, 0.5, 1, 2]  # MB
    results = []
    
    for size_mb in sizes:
        print(f"\n📁 Testando arquivo de {size_mb}MB...")
        
        test_file = create_test_file(size_mb)
        expected_size = os.path.getsize(test_file)
        
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (os.path.basename(test_file), f, 'text/plain')}
                response = requests.post('http://localhost:8080/upload', files=files)
            
            if response.status_code == 200:
                data = response.json()
                returned_size = data.get('size', 0)
                
                if returned_size == expected_size:
                    print(f"✅ {size_mb}MB - OK")
                    results.append(True)
                else:
                    print(f"❌ {size_mb}MB - FALHOU (Esperado: {expected_size}, Recebido: {returned_size})")
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
    
    print(f"\n📊 Resultado: {passed}/{total} testes passaram")
    return passed == total

def main():
    """Função principal"""
    print("🚀 Testando correção do tamanho do arquivo")
    print("=" * 50)
    
    # Teste básico
    basic_test = test_file_size_correction()
    
    if basic_test:
        # Teste com diferentes tamanhos
        size_test = test_different_sizes()
        
        if size_test:
            print("\n✅ TODOS OS TESTES PASSARAM!")
            print("🎉 A correção do tamanho do arquivo está funcionando perfeitamente!")
        else:
            print("\n❌ Alguns testes de tamanho falharam")
    else:
        print("\n❌ Teste básico falhou")
    
    print("\n📋 Próximos passos:")
    print("1. git add app.py")
    print("2. git commit -m 'fix: corrigir tamanho do arquivo na resposta do upload'")
    print("3. git push")
    print("4. Redeploy no Easypanel")

if __name__ == "__main__":
    main()
