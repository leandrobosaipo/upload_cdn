# Variáveis de Ambiente - Upload CDN API
# Copie e cole estas variáveis no Easypanel ou seu arquivo .env

# ============================================
# CONFIGURAÇÕES OBRIGATÓRIAS DO DIGITALOCEAN SPACES
# ============================================

# Chave de acesso do Spaces
SPACES_KEY=sua_chave_aqui

# Secret de acesso do Spaces
SPACES_SECRET=seu_secret_aqui

# Nome do bucket no Spaces
SPACES_BUCKET=seu_bucket_aqui

# Região do Spaces (ex: nyc3, sfo3, ams3)
SPACES_REGION=nyc3

# Endpoint do Spaces (geralmente https://REGIAO.digitaloceanspaces.com)
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# ============================================
# CONFIGURAÇÃO DE DIRETÓRIO PADRÃO
# ============================================

# Diretório padrão onde os arquivos serão armazenados
# Se não fornecer o parâmetro 'folder' na requisição, usará este valor
DEFAULT_UPLOAD_DIR=uploads

# ============================================
# CONFIGURAÇÕES OPCIONAIS DA APLICAÇÃO
# ============================================

# Porta onde a aplicação irá rodar (padrão: 8080)
PORT=8080

# Tamanho máximo de upload em MB (padrão: 100MB)
MAX_CONTENT_LENGTH_MB=100

# ============================================
# EXEMPLO DE CONFIGURAÇÃO COMPLETA
# ============================================
# 
# SPACES_KEY=LZQAHCBDGFOLQR5UUHFR
# SPACES_SECRET=QVrgE+F/Rr0IDkZF5y0AdPtnnh2VMuPo8cCVrdxKzX4
# SPACES_BUCKET=cod5
# SPACES_REGION=nyc3
# SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
# DEFAULT_UPLOAD_DIR=uploads
# PORT=8080
# MAX_CONTENT_LENGTH_MB=100

