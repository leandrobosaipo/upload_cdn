# 🚀 Upload CDN API

API simples para upload de arquivos para DigitalOcean Spaces, otimizada para uso no Easypanel.

## ✨ Funcionalidades

- ✅ Upload de arquivos via `POST /upload`
- ✅ Suporte a múltiplos formatos (vídeo, imagem, documento)
- ✅ Geração automática de nomes únicos
- ✅ URLs públicas diretas
- ✅ Validação de tipos de arquivo
- ✅ Health check endpoint
- ✅ Tratamento de erros robusto

## 🛠️ Tecnologias

- **Python 3.10**
- **Flask** - Framework web
- **Boto3** - Cliente AWS S3 (compatível com DigitalOcean Spaces)
- **Docker** - Containerização

## 📁 Estrutura do Projeto

```
upload_cdn/
├── app.py              # Aplicação Flask principal
├── requirements.txt    # Dependências Python
├── Dockerfile         # Configuração do container
├── .gitignore         # Arquivos ignorados pelo Git
├── test_api.py        # Script de teste da API
└── README.md          # Este arquivo
```

## 🚀 Deploy no Easypanel

### 1. Clone o repositório

```bash
git clone https://github.com/leandrobosaipo/upload_cdn.git
cd upload_cdn
```

### 2. Configure no Easypanel

1. Acesse o **Easypanel**
2. Vá em **Apps > Add App**
3. Escolha **Dockerfile**
4. Conecte o repositório Git ou faça upload dos arquivos
5. Configure as variáveis de ambiente:

```
SPACES_KEY=LZQAHCBDGFOLQR5UUHFR
SPACES_SECRET=QVrgE+F/Rr0IDkZF5y0AdPtnnh2VMuPo8cCVrdxKzX4
```

6. Defina a porta: `8080`
7. Deploy!

## 📡 Endpoints da API

### `POST /upload`
Upload de arquivos para o Spaces.

**Request:**
```bash
curl -X POST https://sua-api.com/upload \
  -F "file=@/caminho/para/arquivo.mp4"
```

**Response:**
```json
{
  "success": true,
  "url": "https://cod5.nyc3.digitaloceanspaces.com/arquivo-unico.mp4",
  "filename": "arquivo-unico.mp4",
  "original_filename": "meu-video.mp4",
  "size": 1024000,
  "content_type": "video/mp4"
}
```

### `GET /health`
Verificar status da API.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "service": "upload-cdn-api"
}
```

### `GET /`
Informações sobre a API.

## 📋 Tipos de Arquivo Suportados

- **Vídeos:** mp4, avi, mov, mkv, webm
- **Imagens:** jpg, jpeg, png, gif
- **Documentos:** pdf, doc, docx

## 🧪 Testando Localmente

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
export SPACES_KEY="sua-chave-aqui"
export SPACES_SECRET="seu-secret-aqui"
```

### 3. Executar a aplicação

```bash
python app.py
```

### 4. Testar com o script

```bash
python test_api.py
```

## 🔧 Configurações

### Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `SPACES_KEY` | Chave de acesso do DigitalOcean Spaces | ✅ |
| `SPACES_SECRET` | Secret de acesso do DigitalOcean Spaces | ✅ |
| `PORT` | Porta da aplicação (padrão: 8080) | ❌ |

### Configurações do Spaces

- **Região:** nyc3
- **Bucket:** cod5
- **Endpoint:** https://nyc3.digitaloceanspaces.com

## 🐛 Troubleshooting

### Erro: "SPACES_KEY e SPACES_SECRET devem estar definidas"
- Verifique se as variáveis de ambiente estão configuradas no Easypanel

### Erro: "Tipo de arquivo não permitido"
- Verifique se o arquivo tem uma extensão suportada

### Erro: "Erro interno do servidor"
- Verifique os logs do container no Easypanel
- Confirme se as credenciais do Spaces estão corretas

## 📝 Logs

Para visualizar logs em tempo real no Easypanel:
1. Acesse o app no painel
2. Vá na aba "Logs"
3. Monitore em tempo real

## 🔄 Atualizações

Para atualizar a aplicação:
1. Faça push das alterações para o repositório
2. No Easypanel, clique em "Redeploy"
3. Aguarde o build e restart automático

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs no Easypanel
2. Confirme as variáveis de ambiente
3. Teste localmente primeiro
4. Verifique a conectividade com o DigitalOcean Spaces

---

**Desenvolvido para pipeline de geração de Shorts** 🎬
