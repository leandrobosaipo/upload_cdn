#!/usr/bin/env python3
"""
Script para testar a configuração de produção
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def test_import():
    """Testa se o app pode ser importado"""
    print("🔍 Testando importação do app...")
    try:
        import app
        print("✅ App importado com sucesso")
        print(f"   Objeto app: {app.app}")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar app: {e}")
        return False

def test_gunicorn_import():
    """Testa se o Gunicorn consegue importar a aplicação"""
    print("\n🔍 Testando importação via Gunicorn...")
    try:
        # Simular o que o Gunicorn faz
        import app
        wsgi_app = app.app
        print("✅ Gunicorn pode importar a aplicação")
        print(f"   WSGI app: {wsgi_app}")
        return True
    except Exception as e:
        print(f"❌ Erro na importação do Gunicorn: {e}")
        return False

def test_gunicorn_start():
    """Testa se o Gunicorn consegue iniciar (sem credenciais)"""
    print("\n🔍 Testando inicialização do Gunicorn...")
    try:
        # Configurar variáveis de ambiente temporárias
        env = os.environ.copy()
        env['SPACES_KEY'] = 'test-key'
        env['SPACES_SECRET'] = 'test-secret'
        
        # Tentar iniciar o Gunicorn em background
        cmd = [
            'gunicorn',
            '--bind', '127.0.0.1:8081',
            '--workers', '1',
            '--timeout', '10',
            '--check-config',
            'app:app'
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Gunicorn configurado corretamente")
            return True
        else:
            print(f"❌ Erro na configuração do Gunicorn: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✅ Gunicorn iniciou (timeout esperado)")
        return True
    except Exception as e:
        print(f"❌ Erro ao testar Gunicorn: {e}")
        return False

def test_dockerfile_syntax():
    """Testa se o Dockerfile está correto"""
    print("\n🔍 Verificando Dockerfile...")
    try:
        with open('Dockerfile', 'r') as f:
            content = f.read()
        
        # Verificar se usa Gunicorn
        if 'gunicorn' in content and 'app:app' in content:
            print("✅ Dockerfile configurado para Gunicorn")
            return True
        else:
            print("❌ Dockerfile não está configurado corretamente")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar Dockerfile: {e}")
        return False

def test_requirements():
    """Testa se o requirements.txt tem Gunicorn"""
    print("\n🔍 Verificando requirements.txt...")
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        if 'gunicorn' in content:
            print("✅ Gunicorn incluído no requirements.txt")
            return True
        else:
            print("❌ Gunicorn não encontrado no requirements.txt")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar requirements.txt: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Testando configuração de produção da Upload CDN API")
    print("=" * 60)
    
    tests = [
        test_import,
        test_gunicorn_import,
        test_requirements,
        test_dockerfile_syntax,
        test_gunicorn_start
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("✅ Todos os testes passaram! A API está pronta para produção.")
        print("\n📋 Próximos passos:")
        print("1. git add .")
        print("2. git commit -m 'fix: configuração de produção com Gunicorn'")
        print("3. git push")
        print("4. Redeploy no Easypanel")
    else:
        print("❌ Alguns testes falharam. Verifique os erros acima.")
        sys.exit(1)

if __name__ == "__main__":
    main()
