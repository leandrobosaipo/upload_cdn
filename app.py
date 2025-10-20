import os
import boto3
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

app = Flask(__name__)

# Configurações do Spaces
SPACES_REGION = "nyc3"
SPACES_ENDPOINT = "https://nyc3.digitaloceanspaces.com"
SPACES_BUCKET = "cod5"
SPACES_KEY = os.environ.get("SPACES_KEY")
SPACES_SECRET = os.environ.get("SPACES_SECRET")

# Validação das variáveis de ambiente (apenas em produção)
if not SPACES_KEY or not SPACES_SECRET:
    print("⚠️  AVISO: SPACES_KEY e SPACES_SECRET não definidas. Configure as variáveis de ambiente.")
    # Em desenvolvimento, permite continuar sem as credenciais
    # Em produção, o Gunicorn falhará se não estiverem definidas

# Cliente S3 (Spaces)
s3 = boto3.client('s3',
    region_name=SPACES_REGION,
    endpoint_url=SPACES_ENDPOINT,
    aws_access_key_id=SPACES_KEY,
    aws_secret_access_key=SPACES_SECRET
)

# Tipos de arquivo permitidos
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "upload-cdn-api"
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint principal para upload de arquivos"""
    try:
        # Verificar se as credenciais estão configuradas
        if not SPACES_KEY or not SPACES_SECRET:
            return jsonify({"error": "Credenciais do Spaces não configuradas"}), 500
        
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({"error": "Nenhum arquivo fornecido"}), 400
        
        file = request.files['file']
        
        # Verificar se arquivo tem nome
        if file.filename == '':
            return jsonify({"error": "Arquivo sem nome"}), 400
        
        # Verificar se tipo de arquivo é permitido
        if not allowed_file(file.filename):
            return jsonify({
                "error": f"Tipo de arquivo não permitido. Tipos aceitos: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Gerar nome único para o arquivo
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Upload para o Spaces
        s3.upload_fileobj(
            Fileobj=file,
            Bucket=SPACES_BUCKET,
            Key=unique_filename,
            ExtraArgs={
                'ACL': 'public-read', 
                'ContentType': file.content_type or 'application/octet-stream'
            }
        )
        
        # URL pública do arquivo
        file_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{unique_filename}"
        
        return jsonify({
            "success": True, 
            "url": file_url,
            "filename": unique_filename,
            "original_filename": original_filename,
            "size": file.content_length,
            "content_type": file.content_type
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Erro interno do servidor: {str(e)}"
        }), 500

@app.route('/', methods=['GET'])
def index():
    """Página inicial com informações da API"""
    return jsonify({
        "message": "Upload CDN API",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload": "Upload de arquivos",
            "GET /health": "Status da API",
            "GET /": "Informações da API"
        },
        "supported_formats": list(ALLOWED_EXTENSIONS)
    })

# Aplicação configurada para produção com Gunicorn
# O Gunicorn irá importar o objeto 'app' diretamente
