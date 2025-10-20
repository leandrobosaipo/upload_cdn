#!/bin/bash

# Script de inicialização robusto para Upload CDN API
echo "🚀 Iniciando Upload CDN API..."

# Configurar variáveis de ambiente
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app

# Verificar se as credenciais estão definidas
if [ -z "$SPACES_KEY" ] || [ -z "$SPACES_SECRET" ]; then
    echo "❌ ERRO: SPACES_KEY e SPACES_SECRET devem estar definidas"
    echo "   SPACES_KEY: ${SPACES_KEY:+✅ Definida}${SPACES_KEY:-❌ Não definida}"
    echo "   SPACES_SECRET: ${SPACES_SECRET:+✅ Definida}${SPACES_SECRET:-❌ Não definida}"
    exit 1
fi

echo "✅ Credenciais verificadas"
echo "🔧 Configurações:"
echo "   - PORT: ${PORT:-8080}"
echo "   - WORKERS: ${WORKERS:-2}"
echo "   - TIMEOUT: ${TIMEOUT:-120}"

# Aguardar um pouco para garantir que tudo está pronto
sleep 2

echo "🚀 Iniciando Gunicorn..."

# Executar Gunicorn com configurações otimizadas
exec gunicorn \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers "${WORKERS:-2}" \
    --timeout "${TIMEOUT:-120}" \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    app:app
