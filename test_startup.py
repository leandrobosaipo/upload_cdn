#!/usr/bin/env python3
"""
Script para testar a inicialização da aplicação
"""

import os
import sys
import time
import subprocess
import requests
import signal
from pathlib import Path

def test_import():
    """Testa se o app pode ser importado sem erros"""
    print("🔍 Testando importação do app...")
    try:
        import app
        print("✅ App importado com sucesso")
        print(f"   Objeto app: {app.app}")
        print(f"   Função get_s3_client: {hasattr(app, 'get_s3_client')}")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar app: {e}")
        return False

def test_gunicorn_start():
    """Testa se o Gunicorn consegue iniciar"""
    print("\n🔍 Testando inicialização do Gunicorn...")
    
    # Configurar variáveis de ambiente
    env = os.environ.copy()
    env['SPACES_KEY'] = 'test-key'
    env['SPACES_SECRET'] = 'test-secret'
    env['PORT'] = '8082'
    
    try:
        # Iniciar Gunicorn em background
        cmd = [
            'gunicorn',
            '--bind', '127.0.0.1:8082',
            '--workers', '1',
            '--timeout', '10',
            '--log-level', 'info',
            'app:app'
        ]
        
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Aguardar um pouco para o Gunicorn inicializar
        time.sleep(3)
        
        # Verificar se o processo ainda está rodando
        if process.poll() is None:
            print("✅ Gunicorn iniciado com sucesso")
            
            # Testar endpoint de health
            try:
                response = requests.get('http://127.0.0.1:8082/health', timeout=5)
                if response.status_code == 200:
                    print("✅ Health check funcionando")
                else:
                    print(f"❌ Health check falhou: {response.status_code}")
            except Exception as e:
                print(f"❌ Erro no health check: {e}")
            
            # Finalizar processo
            process.terminate()
            process.wait(timeout=5)
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Gunicorn falhou ao iniciar")
            print(f"   STDOUT: {stdout.decode()}")
            print(f"   STDERR: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar Gunicorn: {e}")
        return False

def test_script_start():
    """Testa se o script de inicialização funciona"""
    print("\n🔍 Testando script de inicialização...")
    
    # Verificar se o script existe
    if not os.path.exists('start.sh'):
        print("❌ Script start.sh não encontrado")
        return False
    
    # Verificar se é executável
    if not os.access('start.sh', os.X_OK):
        print("❌ Script start.sh não é executável")
        return False
    
    print("✅ Script start.sh encontrado e executável")
    return True

def test_dockerfile():
    """Testa se o Dockerfile está correto"""
    print("\n🔍 Verificando Dockerfile...")
    
    try:
        with open('Dockerfile', 'r') as f:
            content = f.read()
        
        checks = [
            ('FROM python:3.10-slim', 'Imagem base Python'),
            ('WORKDIR /app', 'Diretório de trabalho'),
            ('COPY requirements.txt', 'Cópia do requirements.txt'),
            ('RUN pip install', 'Instalação de dependências'),
            ('COPY .', 'Cópia do código'),
            ('EXPOSE 8080', 'Exposição da porta'),
            ('CMD ["./start.sh"]', 'Comando de inicialização')
        ]
        
        all_good = True
        for check, description in checks:
            if check in content:
                print(f"   ✅ {description}")
            else:
                print(f"   ❌ {description}")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"❌ Erro ao verificar Dockerfile: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Testando inicialização da Upload CDN API")
    print("=" * 60)
    
    tests = [
        ("Importação do app", test_import),
        ("Script de inicialização", test_script_start),
        ("Dockerfile", test_dockerfile),
        ("Gunicorn", test_gunicorn_start)
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
    
    print("\n" + "=" * 60)
    print(f"📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("✅ Todos os testes passaram! A aplicação está pronta para deploy.")
        print("\n📋 Próximos passos:")
        print("1. git add .")
        print("2. git commit -m 'fix: inicialização robusta com logs'")
        print("3. git push")
        print("4. Redeploy no Easypanel")
        print("5. Verificar logs no Easypanel")
    else:
        print("❌ Alguns testes falharam. Verifique os erros acima.")
        sys.exit(1)

if __name__ == "__main__":
    main()
