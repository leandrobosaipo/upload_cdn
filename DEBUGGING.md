# 🐛 Guia de Debugging - Upload CDN API

## 🚨 Problema Original
- **Erro**: "Service is not reachable" no Easypanel
- **Causa**: Cliente S3 inicializado durante importação do módulo
- **Sintoma**: Falha silenciosa na inicialização

## ✅ Correções Implementadas

### 1. **Lazy Loading do Cliente S3**
```python
# ANTES: Inicialização durante importação
s3 = boto3.client('s3', ...)  # ❌ Pode falhar silenciosamente

# DEPOIS: Inicialização sob demanda
def get_s3_client():
    global s3
    if s3 is None:
        s3 = boto3.client('s3', ...)  # ✅ Inicializa apenas quando necessário
    return s3
```

### 2. **Logs Detalhados**
```python
print("🚀 Iniciando Upload CDN API...")
print(f"🔧 Configurações carregadas:")
print(f"   - SPACES_KEY: {'✅ Definida' if SPACES_KEY else '❌ Não definida'}")
logger.info("Iniciando Upload CDN API")
```

### 3. **Script de Inicialização Robusto**
```bash
#!/bin/bash
# start.sh - Valida credenciais antes de iniciar
if [ -z "$SPACES_KEY" ] || [ -z "$SPACES_SECRET" ]; then
    echo "❌ ERRO: Credenciais não definidas"
    exit 1
fi
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" ...
```

### 4. **Dockerfile Otimizado**
```dockerfile
# ANTES: Comando direto
CMD ["gunicorn", "--bind", "0.0.0.0:8080", ...]

# DEPOIS: Script de inicialização
CMD ["./start.sh"]
```

## 🔍 Como Diagnosticar no Easypanel

### 1. **Verificar Logs de Inicialização**
No Easypanel, vá em **Logs** e procure por:
```
🚀 Iniciando Upload CDN API...
🔧 Configurações carregadas:
   - SPACES_KEY: ✅ Definida
   - SPACES_SECRET: ✅ Definida
✅ Flask app configurado com sucesso
🚀 Aplicação pronta para receber requisições!
```

### 2. **Verificar Logs do Gunicorn**
Procure por:
```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:8080
[INFO] Booting worker with pid: X
```

### 3. **Testar Endpoints**
```bash
# Health check
curl https://sua-api.com/health

# Upload de teste
curl -X POST https://sua-api.com/upload \
  -F "file=@teste.txt"
```

## 🚨 Possíveis Problemas e Soluções

### Problema: "Credenciais não configuradas"
**Solução**: Verificar variáveis de ambiente no Easypanel
```
SPACES_KEY=LZQAHCBDGFOLQR5UUHFR
SPACES_SECRET=QVrgE+F/Rr0IDkZF5y0AdPtnnh2VMuPo8cCVrdxKzX4
```

### Problema: "Cliente S3 não inicializado"
**Solução**: Verificar logs para erro específico do boto3

### Problema: "Gunicorn não inicia"
**Solução**: Verificar se o script start.sh é executável

### Problema: "Porta não disponível"
**Solução**: Verificar se a porta 8080 está configurada no Easypanel

## 📊 Logs Esperados

### ✅ Inicialização Bem-sucedida
```
🚀 Iniciando Upload CDN API...
🔧 Configurações carregadas:
   - SPACES_REGION: nyc3
   - SPACES_ENDPOINT: https://nyc3.digitaloceanspaces.com
   - SPACES_BUCKET: cod5
   - SPACES_KEY: ✅ Definida
   - SPACES_SECRET: ✅ Definida
✅ Flask app configurado com sucesso
✅ Rotas registradas:
   - GET  /
   - GET  /health
   - POST /upload
🚀 Aplicação pronta para receber requisições!
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:8080
[INFO] Booting worker with pid: 123
```

### ❌ Inicialização com Erro
```
🚀 Iniciando Upload CDN API...
🔧 Configurações carregadas:
   - SPACES_KEY: ❌ Não definida
   - SPACES_SECRET: ❌ Não definida
❌ ERRO: SPACES_KEY e SPACES_SECRET devem estar definidas
```

## 🧪 Testes Locais

Execute para testar localmente:
```bash
# Teste completo
python test_startup.py

# Teste de importação
python -c "import app; print('OK')"

# Teste com credenciais
SPACES_KEY=test SPACES_SECRET=test python -c "import app; print('OK')"
```

## 📞 Suporte

Se ainda houver problemas:
1. Verifique os logs no Easypanel
2. Confirme as variáveis de ambiente
3. Teste localmente com `python test_startup.py`
4. Verifique se o repositório foi atualizado
