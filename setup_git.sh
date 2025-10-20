#!/bin/bash

# Script para configurar o repositório Git
echo "🚀 Configurando repositório Git para Upload CDN API"

# Inicializar repositório Git
echo "📁 Inicializando repositório Git..."
git init

# Adicionar todos os arquivos
echo "📝 Adicionando arquivos ao Git..."
git add .

# Fazer commit inicial
echo "💾 Fazendo commit inicial..."
git commit -m "feat: API de upload para DigitalOcean Spaces

- Flask app com endpoint /upload
- Suporte a múltiplos formatos de arquivo
- Upload direto para DigitalOcean Spaces
- Validação de tipos de arquivo
- Health check endpoint
- Dockerfile para deploy no Easypanel
- Script de teste incluído"

# Configurar branch main
echo "🌿 Configurando branch main..."
git branch -M main

# Adicionar remote origin
echo "🔗 Adicionando remote origin..."
git remote add origin https://github.com/leandrobosaipo/upload_cdn.git

echo "✅ Repositório Git configurado!"
echo ""
echo "📋 Próximos passos:"
echo "1. git push -u origin main"
echo "2. Configurar no Easypanel:"
echo "   - Tipo: Dockerfile"
echo "   - Porta: 8080"
echo "   - Variáveis: SPACES_KEY e SPACES_SECRET"
echo "3. Testar com: python test_api.py"
echo ""
echo "🎉 Pronto para deploy!"
