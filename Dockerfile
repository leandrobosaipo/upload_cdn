FROM python:3.10-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Configurar variáveis de ambiente
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expor porta
EXPOSE 8080

# Comando para executar a aplicação
CMD ["python", "app.py"]
