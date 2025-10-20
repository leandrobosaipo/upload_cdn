import os
import boto3
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("🚀 Iniciando Upload CDN API...")
logger.info("Iniciando Upload CDN API")

app = Flask(__name__)

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
        logger.info("Recebendo requisição de upload")
        
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            print("❌ Nenhum arquivo fornecido")
            return jsonify({"error": "Nenhum arquivo fornecido"}), 400
        
        file = request.files['file']
        
        # Verificar se arquivo tem nome
        if file.filename == '':
            print("❌ Arquivo sem nome")
            return jsonify({"error": "Arquivo sem nome"}), 400
        
        # Verificar se tipo de arquivo é permitido
        if not allowed_file(file.filename):
            print(f"❌ Tipo de arquivo não permitido: {file.filename}")
            return jsonify({
                "error": f"Tipo de arquivo não permitido. Tipos aceitos: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        print(f"✅ Arquivo válido: {file.filename}")
        
        # Capturar o tamanho real do arquivo
        file.stream.seek(0, 2)  # Vai para o fim do arquivo
        file_size = file.stream.tell()
        file.stream.seek(0)     # Volta ao início para permitir o upload
        
        print(f"📏 Tamanho do arquivo: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        logger.info(f"Tamanho do arquivo: {file_size} bytes")
        
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
            "size": file_size,
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

# Aplicação configurada para produção com Gunicorn
# O Gunicorn irá importar o objeto 'app' diretamente
