#!/bin/bash

# Script de inicialização robusto para Upload CDN API
echo "🚀 Iniciando Upload CDN API..."

# Configurar variáveis de ambiente essenciais
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app

# Verificar credenciais obrigatórias do Spaces
if [ -z "$SPACES_KEY" ] || [ -z "$SPACES_SECRET" ]; then
    echo "❌ ERRO: SPACES_KEY e SPACES_SECRET devem estar definidas"
    echo "   SPACES_KEY: ${SPACES_KEY:+✅ Definida}${SPACES_KEY:-❌ Não definida}"
    echo "   SPACES_SECRET: ${SPACES_SECRET:+✅ Definida}${SPACES_SECRET:-❌ Não definida}"
    exit 1
fi

echo "✅ Credenciais verificadas"
echo "🔧 Configurações do ambiente:"
echo "   - PORT: ${PORT:-80}"
echo "   - WORKERS: ${WORKERS:-2}"
echo "   - THREADS: 4"
echo "   - TIMEOUT: ${TIMEOUT:-180}"

# Calcular o tamanho máximo do upload (padrão: 100MB)
MAX_SIZE_MB=${MAX_CONTENT_LENGTH_MB:-100}
if [[ "$MAX_SIZE_MB" =~ ^[0-9]+$ ]]; then
  MAX_SIZE_BYTES=$((MAX_SIZE_MB * 1024 * 1024))
else
  echo "⚠️ Valor inválido para MAX_CONTENT_LENGTH_MB ('$MAX_CONTENT_LENGTH_MB'), usando padrão de 100MB."
  MAX_SIZE_BYTES=$((100 * 1024 * 1024))
fi

echo "   - MAX_FILE_SIZE: ${MAX_SIZE_MB}MB (${MAX_SIZE_BYTES} bytes)"

# Esperar um pouco para garantir que dependências estejam prontas
sleep 2

echo "🚀 Iniciando Gunicorn na porta 80..."

# Executar Gunicorn com configurações otimizadas
exec gunicorn \
    --bind "0.0.0.0:80" \
    --workers "${WORKERS:-2}" \
    --threads 4 \
    --timeout "${TIMEOUT:-180}" \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    --preload \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    app:app