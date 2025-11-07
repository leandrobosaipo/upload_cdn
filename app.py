import os
import boto3
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from flask_swagger_ui import get_swaggerui_blueprint
import uuid
from datetime import datetime
import logging
import botocore.exceptions

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
    try:
        # Verificar se as credenciais estão configuradas
        if not SPACES_KEY or not SPACES_SECRET:
            return jsonify({
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "service": "upload-cdn-api",
                "error": "Credenciais do Spaces não configuradas"
            }), 503
        
        # Tentar inicializar o cliente S3 para verificar conectividade
        try:
            test_client = get_s3_client()
            # Fazer uma operação simples para verificar conectividade
            test_client.head_bucket(Bucket=SPACES_BUCKET)
        except Exception as e:
            logger.warning(f"Erro ao verificar conectividade com Spaces: {e}")
            return jsonify({
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "service": "upload-cdn-api",
                "error": "Não foi possível conectar ao serviço de armazenamento",
                "detail": str(e)
            }), 503
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "upload-cdn-api"
        })
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "service": "upload-cdn-api",
            "error": "Erro interno no health check",
            "detail": str(e)
        }), 503

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
            logger.warning("Tentativa de upload sem arquivo")
            return jsonify({
                "success": False,
                "error": "Nenhum arquivo fornecido",
                "detail": "É necessário enviar um arquivo no campo 'file' usando multipart/form-data"
            }), 400
        
        file = request.files['file']
        
        # Verificar se arquivo tem nome
        if not file or file.filename == '':
            print("❌ Arquivo sem nome ou vazio")
            logger.warning("Tentativa de upload com arquivo sem nome ou vazio")
            return jsonify({
                "success": False,
                "error": "Arquivo sem nome ou vazio",
                "detail": "O arquivo enviado não possui nome ou está vazio. Verifique se o arquivo foi selecionado corretamente."
            }), 400
        
        # Verificar se tipo de arquivo é permitido
        if not allowed_file(file.filename):
            print(f"❌ Tipo de arquivo não permitido: {file.filename}")
            logger.warning(f"Tentativa de upload com tipo não permitido: {file.filename}")
            return jsonify({
                "success": False,
                "error": f"Tipo de arquivo não permitido. Tipos aceitos: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                "detail": "O arquivo enviado não está em um formato suportado. Use apenas os tipos listados."
            }), 400
        
        print(f"✅ Arquivo válido: {file.filename}")
        
        # Capturar o tamanho real do arquivo
        file.stream.seek(0, 2)  # Ir até o final do arquivo
        size = file.stream.tell()
        file.stream.seek(0)     # Voltar para o começo
        
        print(f"📏 Tamanho do arquivo: {size} bytes ({size / 1024 / 1024:.2f} MB)")
        logger.info(f"Tamanho do arquivo: {size} bytes")
        
        # Verificar tamanho do arquivo manualmente (backup caso o Flask não capture)
        max_size_bytes = max_content_length_mb * 1024 * 1024
        if size > max_size_bytes:
            print(f"❌ Arquivo muito grande: {size} bytes (limite: {max_size_bytes} bytes)")
            logger.warning(f"Arquivo excede tamanho máximo: {size} bytes")
            return jsonify({
                "success": False,
                "error": "Arquivo muito grande",
                "detail": f"O tamanho do arquivo excede o limite máximo permitido. Tamanho máximo configurado: {max_content_length_mb}MB. Tamanho do arquivo enviado: {size / 1024 / 1024:.2f}MB"
            }), 413
        
        # Gerar nome único para o arquivo
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        print(f"🔄 Iniciando upload: {unique_filename}")
        logger.info(f"Iniciando upload: {unique_filename}")
        
        # Obter cliente S3 (inicializa se necessário)
        try:
            s3_client = get_s3_client()
        except ValueError as e:
            # Credenciais não configuradas
            print(f"❌ Erro de configuração: {e}")
            logger.error(f"Credenciais não configuradas: {e}")
            return jsonify({
                "success": False,
                "error": "Credenciais do Spaces não configuradas",
                "detail": "As variáveis de ambiente SPACES_KEY e SPACES_SECRET não estão configuradas corretamente."
            }), 503
        except Exception as e:
            # Outros erros de inicialização
            print(f"❌ Erro ao inicializar cliente S3: {e}")
            logger.error(f"Erro ao inicializar cliente S3: {e}")
            return jsonify({
                "success": False,
                "error": "Erro ao conectar ao serviço de armazenamento",
                "detail": "Não foi possível inicializar a conexão com o DigitalOcean Spaces. Verifique as configurações."
            }), 503
        
        # Upload para o Spaces
        try:
            s3_client.upload_fileobj(
                Fileobj=file,
                Bucket=SPACES_BUCKET,
                Key=unique_filename,
                ExtraArgs={
                    'ACL': 'public-read', 
                    'ContentType': file.content_type or 'application/octet-stream'
                }
            )
        except botocore.exceptions.ClientError as e:
            # Erros específicos do boto3/S3
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            print(f"❌ Erro no upload para Spaces: {error_code} - {e}")
            logger.error(f"Erro no upload para Spaces: {error_code} - {e}")
            
            if error_code in ['NoSuchBucket', 'AccessDenied', 'InvalidAccessKeyId']:
                return jsonify({
                    "success": False,
                    "error": "Erro de configuração do serviço de armazenamento",
                    "detail": f"Não foi possível acessar o bucket. Verifique as credenciais e configurações. Código do erro: {error_code}"
                }), 503
            else:
                return jsonify({
                    "success": False,
                    "error": "Erro ao fazer upload para o serviço de armazenamento",
                    "detail": f"Ocorreu um erro ao tentar fazer upload do arquivo. Tente novamente em alguns instantes. Código do erro: {error_code}"
                }), 503
        except botocore.exceptions.EndpointConnectionError as e:
            # Erro de conexão com o endpoint
            print(f"❌ Erro de conexão com Spaces: {e}")
            logger.error(f"Erro de conexão com Spaces: {e}")
            return jsonify({
                "success": False,
                "error": "Serviço de armazenamento temporariamente indisponível",
                "detail": "Não foi possível conectar ao DigitalOcean Spaces. Tente novamente em alguns instantes."
            }), 503
        except Exception as e:
            # Outros erros de upload
            print(f"❌ Erro inesperado no upload: {e}")
            logger.error(f"Erro inesperado no upload: {e}")
            return jsonify({
                "success": False,
                "error": "Erro ao fazer upload do arquivo",
                "detail": f"Ocorreu um erro inesperado durante o upload. Tente novamente ou entre em contato com o suporte se o problema persistir."
            }), 500
        
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
        
    except RequestEntityTooLarge:
        # Este erro já é tratado pelo handler específico, mas incluímos aqui como backup
        raise
    except Exception as e:
        print(f"❌ Erro inesperado no upload: {e}")
        logger.error(f"Erro inesperado no upload: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Erro interno do servidor",
            "detail": "Ocorreu um erro inesperado durante o processamento. Entre em contato com o suporte se o problema persistir."
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
print("   - GET  /docs (Swagger UI)")
print("   - GET  /swagger.json (OpenAPI spec)")
print("🚀 Aplicação pronta para receber requisições!")

logger.info("Flask app configurado com sucesso")
logger.info("Aplicação pronta para receber requisições")

# Configuração do Swagger UI
SWAGGER_URL = '/docs'
API_URL = '/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Upload CDN API",
        'docExpansion': 'list',
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'displayRequestDuration': True,
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'supportedSubmitMethods': ['get', 'post', 'put', 'delete', 'patch']
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/swagger.json')
def swagger_json():
    """Serve o arquivo swagger.json para a documentação"""
    response = send_from_directory('docs', 'swagger.json')
    # Adicionar headers CORS para permitir acesso do Swagger UI
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Handler para arquivos muito grandes
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handler para quando o arquivo excede o tamanho máximo permitido"""
    print("❌ Arquivo muito grande")
    logger.error("Arquivo muito grande")
    
    max_size_mb = max_content_length_mb
    return jsonify({
        "success": False,
        "error": "Arquivo muito grande",
        "detail": f"O tamanho do arquivo excede o limite máximo permitido. Tamanho máximo configurado: {max_size_mb}MB"
    }), 413

# Handler para erros 404
@app.errorhandler(404)
def handle_not_found(e):
    """Handler para rotas não encontradas"""
    return jsonify({
        "success": False,
        "error": "Rota não encontrada",
        "detail": "A rota solicitada não existe. Consulte a documentação em /docs para ver os endpoints disponíveis."
    }), 404

# Handler para erros 405 (Method Not Allowed)
@app.errorhandler(405)
def handle_method_not_allowed(e):
    """Handler para métodos HTTP não permitidos"""
    return jsonify({
        "success": False,
        "error": "Método não permitido",
        "detail": "O método HTTP utilizado não é permitido para esta rota. Consulte a documentação em /docs."
    }), 405

# Aplicação configurada para produção com Gunicorn
# O Gunicorn irá importar o objeto 'app' diretamente
