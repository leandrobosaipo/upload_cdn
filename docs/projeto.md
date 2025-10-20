Perfeito! Você quer:

> 🔧 **Criar um app dentro do Easypanel que exponha uma API pública para fazer upload de arquivos (ex: vídeos)** — para usá-la dentro do seu pipeline de geração de Shorts.

Isso é 100% possível e relativamente simples com **Python + Flask**, rodando como um app no **Easypanel**. Vou te guiar passo a passo.

---

## ✅ Objetivo Final

* Criar uma API com um endpoint:

  ```
  POST /upload
  ```
* Aceita um arquivo `multipart/form-data`
* Faz upload desse arquivo para o **Spaces (DigitalOcean)**
* Retorna o link público do vídeo

---

## 🧱 Stack que vamos usar

* **Linguagem:** Python
* **Framework:** Flask
* **Upload para Spaces:** `boto3` (client S3)
* **Hospedagem:** Easypanel (Docker container com Python app)

---

## 🧰 Etapas para criar a API pública de upload

### 1. 📁 Estrutura básica do projeto

Dentro do app, crie:

```
/upload-api
├── app.py
├── requirements.txt
└── Dockerfile
```

---

### 2. 📜 `app.py` (o app Flask com upload para Spaces)

```python
import os
import boto3
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações do Spaces
SPACES_REGION = "nyc3"
SPACES_ENDPOINT = "https://nyc3.digitaloceanspaces.com"
SPACES_BUCKET = "cod5"
SPACES_KEY = os.environ.get("SPACES_KEY")
SPACES_SECRET = os.environ.get("SPACES_SECRET")

# Cliente S3 (Spaces)
s3 = boto3.client('s3',
    region_name=SPACES_REGION,
    endpoint_url=SPACES_ENDPOINT,
    aws_access_key_id=SPACES_KEY,
    aws_secret_access_key=SPACES_SECRET
)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)

    # Upload para o Spaces
    s3.upload_fileobj(
        Fileobj=file,
        Bucket=SPACES_BUCKET,
        Key=filename,
        ExtraArgs={'ACL': 'public-read', 'ContentType': file.content_type}
    )

    file_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{filename}"

    return jsonify({"success": True, "url": file_url})
```

---

### 3. 📦 `requirements.txt`

```txt
flask
boto3
```

---

### 4. 🐳 `Dockerfile`

```Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
```

---

### 5. ⚙️ Variáveis de ambiente no Easypanel

Quando for criar o app no Easypanel:

* Tipo: Dockerfile
* Porta: `8080` (ou o que definiu no `ENV`)
* Variáveis:

```
SPACES_KEY=LZQAHCBDGFOLQR5UUHFR
SPACES_SECRET=QVrgE+F/Rr0IDkZF5y0AdPtnnh2VMuPo8cCVrdxKzX4
```

---

### 6. 🚀 Deploy no Easypanel

* Vá no **Easypanel > Apps > Add App**
* Escolha **Dockerfile**
* Suba o repositório ou use Git
* Adicione as variáveis `SPACES_KEY`, `SPACES_SECRET`
* Rode o container

---

### 7. ✅ Testando o endpoint `/upload`

Você pode usar este `curl`:

```bash
curl -X POST https://seu-dominio-ou-ip/upload \
  -F "file=@/Users/leandrobosaipo/Downloads/Gravacao_Comprimida.mp4"
```

**Resposta esperada:**

```json
{
  "success": true,
  "url": "https://cod5.nyc3.digitaloceanspaces.com/Gravacao_Comprimida.mp4"
}
```

---

## 🔁 Usando no pipeline

Depois disso, sempre que quiser legendar:

1. Faz `POST /upload` com o vídeo local
2. Pega a URL retornada
3. Envia para a API `/v1/video/caption`

---

## Segue github criado para esse projeto:
echo "# upload_cdn" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/leandrobosaipo/upload_cdn.git
git push -u origin main
