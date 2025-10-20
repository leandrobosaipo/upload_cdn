import os
import boto3
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import uuid
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("🚀 Iniciando Upload CDN API...")
logger.info("Iniciando Upload CDN API")

app = Flask(__name__)

# Configuração para uploads maiores
# app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
# app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB
# Configuração para uploads maiores (permitindo sobrescrita via variável de ambiente)
DEFAULT_MAX_CONTENT_LENGTH_MB = 100
max_content_length_env = os.environ.get("MAX_CONTENT_LENGTH_MB")

try:
    if max_content_length_env is None:
        raise ValueError
    max_content_length_mb = int(max_content_length_env)
    if max_content_length_mb <= 0:
        raise ValueError
except ValueError:
    max_content_length_mb = DEFAULT_MAX_CONTENT_LENGTH_MB
    if max_content_length_env is not None:
        print(
            f"⚠️ Valor inválido para MAX_CONTENT_LENGTH_MB ('{max_content_length_env}'). "
            f"Usando padrão de {DEFAULT_MAX_CONTENT_LENGTH_MB}MB."
        )
        logger.warning(
            "MAX_CONTENT_LENGTH_MB inválido fornecido. Utilizando valor padrão de %sMB",
            DEFAULT_MAX_CONTENT_LENGTH_MB,
        )

app.config['MAX_CONTENT_LENGTH'] = max_content_length_mb * 1024 * 1024

# Configurações do Spaces
SPACES_REGION = "nyc3"
SPACES_ENDPOINT = "https://nyc3.digitaloceanspaces.com"
SPACES_BUCKET = "cod5"
SPACES_KEY = os.environ.get("SPACES_KEY")
SPACES_SECRET = os.environ.get("SPACES_SECRET")

print(f"🔧 Configurações carregadas:")
print(f"   - SPACES_REGION: {SPACES_REGION}")
print(f"   - SPACES_ENDPOINT: {SPACES_ENDPOINT}")
print(f"   - SPACES_BUCKET: {SPACES_BUCKET}")
print(f"   - SPACES_KEY: {'✅ Definida' if SPACES_KEY else '❌ Não definida'}")
print(f"   - SPACES_SECRET: {'✅ Definida' if SPACES_SECRET else '❌ Não definida'}")

logger.info(f"SPACES_KEY definida: {bool(SPACES_KEY)}")
logger.info(f"SPACES_SECRET definida: {bool(SPACES_SECRET)}")

# Cliente S3 será inicializado apenas quando necessário
s3 = None

def get_s3_client():
    """Inicializa o cliente S3 apenas quando necessário"""
    global s3
    if s3 is None:
        try:
            print("🔗 Inicializando cliente S3...")
            logger.info("Inicializando cliente S3")
            
            if not SPACES_KEY or not SPACES_SECRET:
                raise ValueError("Credenciais do Spaces não configuradas")
            
            s3 = boto3.client('s3',
                region_name=SPACES_REGION,
                endpoint_url=SPACES_ENDPOINT,
                aws_access_key_id=SPACES_KEY,
                aws_secret_access_key=SPACES_SECRET
            )
            
            print("✅ Cliente S3 inicializado com sucesso")
            logger.info("Cliente S3 inicializado com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar cliente S3: {e}")
            logger.error(f"Erro ao inicializar cliente S3: {e}")
            raise
    
    return s3

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
        print("📤 Recebendo requisição de upload")
        print(f"🔍 Content-Type: {request.content_type}")
        print(f"🔍 Files keys: {list(request.files.keys())}")
        logger.info("Recebendo requisição de upload")
        
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            print("❌ Nenhum arquivo fornecido")
            print(f"   Files disponíveis: {list(request.files.keys())}")
            return jsonify({"error": "Nenhum arquivo fornecido"}), 400
        
        file = request.files['file']
        
        # Verificar se arquivo tem nome
        if not file or file.filename == '':
            print("❌ Arquivo sem nome ou vazio")
            return jsonify({"error": "Arquivo sem nome ou vazio"}), 400
        
        # Verificar se tipo de arquivo é permitido
        if not allowed_file(file.filename):
            print(f"❌ Tipo de arquivo não permitido: {file.filename}")
            return jsonify({
                "error": f"Tipo de arquivo não permitido. Tipos aceitos: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        print(f"✅ Arquivo válido: {file.filename}")
        
        # Capturar o tamanho real do arquivo
        file.stream.seek(0, 2)  # Ir até o final do arquivo
        size = file.stream.tell()
        file.stream.seek(0)     # Voltar para o começo
        
        print(f"📏 Tamanho do arquivo: {size} bytes ({size / 1024 / 1024:.2f} MB)")
        logger.info(f"Tamanho do arquivo: {size} bytes")
        
        # Gerar nome único para o arquivo
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        print(f"🔄 Iniciando upload: {unique_filename}")
        logger.info(f"Iniciando upload: {unique_filename}")
        
        # Obter cliente S3 (inicializa se necessário)
        s3_client = get_s3_client()
        
        # Upload para o Spaces
        s3_client.upload_fileobj(
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
        
        print(f"✅ Upload concluído: {file_url}")
        logger.info(f"Upload concluído: {file_url}")
        
        return jsonify({
            "success": True, 
            "url": file_url,
            "filename": unique_filename,
            "original_filename": original_filename,
            "size": size,
            "content_type": file.content_type
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        logger.error(f"Erro no upload: {e}")
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

# Logs de inicialização
print("✅ Flask app configurado com sucesso")
print("✅ Rotas registradas:")
print("   - GET  /")
print("   - GET  /health")
print("   - POST /upload")
print("🚀 Aplicação pronta para receber requisições!")

logger.info("Flask app configurado com sucesso")
logger.info("Aplicação pronta para receber requisições")

# Handler para arquivos muito grandes
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    print("❌ Arquivo muito grande")
    logger.error("Arquivo muito grande")
    return jsonify({
        "error": "Arquivo muito grande. Tamanho máximo permitido: 100MB"
    }), 413

# Aplicação configurada para produção com Gunicorn
# O Gunicorn irá importar o objeto 'app' diretamente
