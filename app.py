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
import hashlib
import time
import json
import subprocess
import tempfile
import re
from typing import Dict, Any, Optional

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

# Configuração de diretório padrão para uploads
DEFAULT_UPLOAD_DIR = os.environ.get("DEFAULT_UPLOAD_DIR", "uploads")

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

def format_size_human(size_bytes: int) -> Dict[str, Any]:
    """Formata tamanho do arquivo em diferentes unidades com descrição em pt-BR"""
    size_kb = size_bytes / 1024
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_bytes / (1024 * 1024 * 1024)
    
    if size_gb >= 1:
        size_str = f"{size_gb:.2f} GB"
        size_desc = f"{size_gb:.2f} gigabytes"
    elif size_mb >= 1:
        size_str = f"{size_mb:.2f} MB"
        size_desc = f"{size_mb:.2f} megabytes"
    elif size_kb >= 1:
        size_str = f"{size_kb:.2f} KB"
        size_desc = f"{size_kb:.2f} kilobytes"
    else:
        size_str = f"{size_bytes} bytes"
        size_desc = f"{size_bytes} bytes"
    
    return {
        "bytes": size_bytes,
        "kilobytes": round(size_kb, 2),
        "megabytes": round(size_mb, 2),
        "gigabytes": round(size_gb, 4),
        "formatted": size_str,
        "descricao_humana": size_desc
    }

def format_duration_human(seconds: float) -> Dict[str, Any]:
    """Formata duração em formato humano em pt-BR"""
    if seconds < 1:
        ms = seconds * 1000
        return {
            "segundos": round(seconds, 3),
            "milissegundos": round(ms, 0),
            "formatted": f"{round(ms, 0)} ms",
            "descricao_humana": f"{round(ms, 0)} milissegundos"
        }
    elif seconds < 60:
        return {
            "segundos": round(seconds, 2),
            "formatted": f"{round(seconds, 2)} s",
            "descricao_humana": f"{round(seconds, 2)} segundos"
        }
    else:
        mins = seconds / 60
        secs = seconds % 60
        return {
            "segundos": round(seconds, 2),
            "minutos": round(mins, 2),
            "formatted": f"{int(mins)}m {int(secs)}s",
            "descricao_humana": f"{int(mins)} minutos e {int(secs)} segundos"
        }

def calculate_hash(file_obj) -> str:
    """Calcula hash MD5 do arquivo"""
    file_obj.seek(0)
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: file_obj.read(4096), b""):
        hash_md5.update(chunk)
    file_obj.seek(0)
    return hash_md5.hexdigest()

def get_client_info() -> Dict[str, Any]:
    """Extrai informações do cliente da requisição"""
    ip = request.remote_addr
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    real_ip = request.headers.get('X-Real-IP', '')
    
    # Usar IP real se disponível (atrás de proxy)
    client_ip = forwarded_for.split(',')[0].strip() if forwarded_for else (real_ip if real_ip else ip)
    
    user_agent = request.headers.get('User-Agent', 'Desconhecido')
    referer = request.headers.get('Referer', '')
    accept_language = request.headers.get('Accept-Language', '')
    
    return {
        "ip": client_ip,
        "ip_original": ip,
        "user_agent": user_agent,
        "referer": referer,
        "accept_language": accept_language,
        "headers": {
            "x_forwarded_for": forwarded_for,
            "x_real_ip": real_ip,
            "host": request.headers.get('Host', ''),
            "content_type": request.content_type
        }
    }

def get_file_category(content_type: str, extension: str) -> Dict[str, Any]:
    """Categoriza o arquivo por tipo"""
    video_extensions = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    image_extensions = {'jpg', 'jpeg', 'png', 'gif'}
    document_extensions = {'pdf', 'doc', 'docx'}
    
    extension_lower = extension.lower()
    
    if extension_lower in video_extensions or 'video' in content_type.lower():
        categoria = "video"
        categoria_desc = "Vídeo"
        tipo_midia = "Áudio e Vídeo"
    elif extension_lower in image_extensions or 'image' in content_type.lower():
        categoria = "imagem"
        categoria_desc = "Imagem"
        tipo_midia = "Imagem"
    elif extension_lower in document_extensions or 'application' in content_type.lower():
        categoria = "documento"
        categoria_desc = "Documento"
        tipo_midia = "Documento"
    else:
        categoria = "outro"
        categoria_desc = "Outro"
        tipo_midia = "Outro"
    
    return {
        "categoria": categoria,
        "categoria_descricao": categoria_desc,
        "tipo_midia": tipo_midia,
        "extensao": extension_lower
    }

def validate_and_sanitize_folder(folder: Optional[str]) -> str:
    """Valida e sanitiza o nome do diretório, prevenindo path traversal"""
    if not folder:
        return DEFAULT_UPLOAD_DIR
    
    # Remover espaços e caracteres perigosos
    folder = folder.strip()
    
    # Prevenir path traversal
    if '..' in folder or folder.startswith('/') or '\\' in folder:
        logger.warning(f"Tentativa de path traversal detectada: {folder}")
        return DEFAULT_UPLOAD_DIR
    
    # Permitir apenas letras, números, hífen, underscore e barras
    folder = re.sub(r'[^a-zA-Z0-9\-_/]', '', folder)
    
    # Remover barras duplicadas e barras no início/fim
    folder = re.sub(r'/+', '/', folder)
    folder = folder.strip('/')
    
    # Limitar tamanho
    if len(folder) > 200:
        folder = folder[:200]
    
    return folder if folder else DEFAULT_UPLOAD_DIR

def extract_media_metadata(file_path: str, content_type: str) -> Optional[Dict[str, Any]]:
    """Extrai metadados de mídia usando ffprobe"""
    # Só tentar extrair metadados para vídeos e áudios
    if not content_type or ('video' not in content_type.lower() and 'audio' not in content_type.lower()):
        return None
    
    try:
        # Comando ffprobe para extrair metadados em JSON
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.warning(f"ffprobe retornou código {result.returncode}: {result.stderr}")
            return None
        
        data = json.loads(result.stdout)
        
        # Extrair informações dos streams
        video_stream = None
        audio_stream = None
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and not video_stream:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and not audio_stream:
                audio_stream = stream
        
        # Extrair informações do formato
        format_info = data.get('format', {})
        duration = float(format_info.get('duration', 0))
        bitrate = int(format_info.get('bit_rate', 0))
        size = int(format_info.get('size', 0))
        
        # Processar informações de vídeo
        video_info = {}
        if video_stream:
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            codec = video_stream.get('codec_name', 'unknown')
            fps_str = video_stream.get('r_frame_rate', '0/1')
            
            # Calcular FPS
            fps = 0
            if '/' in fps_str:
                num, den = map(int, fps_str.split('/'))
                fps = num / den if den > 0 else 0
            
            # Estimar número de frames
            frames_estimated = int(duration * fps) if fps > 0 else 0
            
            video_info = {
                "codec_video": codec,
                "resolucao": f"{width}x{height}",
                "largura": width,
                "altura": height,
                "fps": round(fps, 2),
                "frames_estimados": frames_estimated,
                "proporcao_aspecto": video_stream.get('display_aspect_ratio', ''),
                "pixel_format": video_stream.get('pix_fmt', '')
            }
        
        # Processar informações de áudio
        audio_info = {}
        if audio_stream:
            audio_info = {
                "codec_audio": audio_stream.get('codec_name', 'unknown'),
                "sample_rate": int(audio_stream.get('sample_rate', 0)),
                "canais": int(audio_stream.get('channels', 0)),
                "bitrate_audio": int(audio_stream.get('bit_rate', 0))
            }
        
        # Formatar duração
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        milliseconds = int((duration % 1) * 1000)
        duracao_formatada = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        
        # Determinar tipo de compressão (CBR/VBR)
        compressao = "VBR"  # Padrão VBR
        if bitrate > 0:
            # Tentar determinar se é CBR verificando variação de bitrate
            compressao = "CBR"  # Simplificado, pode ser melhorado
        
        # Calcular bitrate em Mbps
        bitrate_mbps = (bitrate / 1000000) if bitrate > 0 else 0
        
        # Montar descrição humana
        desc_parts = []
        if video_info:
            desc_parts.append(f"Vídeo {video_info.get('resolucao', '')} em {video_info.get('codec_video', '')}")
        if audio_info:
            desc_parts.append(f"áudio {audio_info.get('codec_audio', '')}")
        if duration > 0:
            desc_parts.append(f"{duracao_formatada}")
        if bitrate_mbps > 0:
            desc_parts.append(f"{bitrate_mbps:.2f} Mbps")
        
        descricao_humana = ", ".join(desc_parts) if desc_parts else "Metadados de mídia disponíveis"
        
        return {
            "duracao_segundos": round(duration, 3),
            "duracao_formatada": duracao_formatada,
            "bitrate_total_bps": bitrate,
            "bitrate_total_mbps": round(bitrate_mbps, 2),
            "compressao": compressao,
            "tamanho_bytes": size,
            **video_info,
            **audio_info,
            "descricao_humana": descricao_humana
        }
        
    except subprocess.TimeoutExpired:
        logger.warning("Timeout ao extrair metadados com ffprobe")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao decodificar JSON do ffprobe: {e}")
        return None
    except Exception as e:
        logger.warning(f"Erro ao extrair metadados: {e}")
        return None

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
    # Timestamp de início da requisição
    timestamp_inicio = datetime.now()
    timestamp_inicio_iso = timestamp_inicio.isoformat()
    timestamp_inicio_unix = time.time()
    
    try:
        print("📤 Recebendo requisição de upload")
        print(f"🔍 Content-Type: {request.content_type}")
        print(f"🔍 Files keys: {list(request.files.keys())}")
        logger.info("Recebendo requisição de upload")
        
        # Coletar informações da sessão/cliente
        client_info = get_client_info()
        
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
        
        # Capturar parâmetro de diretório (opcional)
        folder_param = request.form.get('folder') or request.args.get('folder')
        target_folder = validate_and_sanitize_folder(folder_param)
        
        # Gerar nome único para o arquivo
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Calcular hash do arquivo antes do upload
        file_hash = calculate_hash(file)
        
        # Formatação de tamanho
        size_info = format_size_human(size)
        
        # Categorização do arquivo
        file_category = get_file_category(file.content_type or '', file_extension)
        
        print(f"📏 Tamanho do arquivo: {size} bytes ({size_info['formatted']})")
        print(f"📁 Diretório destino: {target_folder}")
        logger.info(f"Tamanho do arquivo: {size} bytes, Diretório: {target_folder}")
        
        # Salvar arquivo temporariamente para extração de metadados
        temp_file_path = None
        media_metadata = None
        
        try:
            # Criar arquivo temporário
            temp_fd, temp_file_path = tempfile.mkstemp(suffix=f".{file_extension}")
            file.stream.seek(0)
            
            with os.fdopen(temp_fd, 'wb') as temp_file:
                file.stream.seek(0)
                temp_file.write(file.stream.read())
            
            # Extrair metadados de mídia
            print("🔍 Extraindo metadados de mídia...")
            media_metadata = extract_media_metadata(temp_file_path, file.content_type or '')
            
            if media_metadata:
                print(f"✅ Metadados extraídos: {media_metadata.get('descricao_humana', 'N/A')}")
            else:
                print("ℹ️ Metadados não disponíveis para este tipo de arquivo")
            
            # Resetar stream do arquivo para upload
            file.stream.seek(0)
            
        except Exception as e:
            logger.warning(f"Erro ao processar arquivo temporário ou extrair metadados: {e}")
            # Continuar mesmo se falhar a extração de metadados
        
        print(f"🔄 Iniciando upload: {target_folder}/{unique_filename}")
        logger.info(f"Iniciando upload: {target_folder}/{unique_filename}")
        
        # Timestamp de início do upload
        timestamp_upload_inicio = time.time()
        
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
        
        # Montar caminho completo com diretório
        s3_key = f"{target_folder}/{unique_filename}" if target_folder else unique_filename
        
        # Upload para o Spaces
        try:
            s3_client.upload_fileobj(
                Fileobj=file,
                Bucket=SPACES_BUCKET,
                Key=s3_key,
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
        
        # Timestamp de fim do upload
        timestamp_upload_fim = time.time()
        timestamp_fim = datetime.now()
        timestamp_fim_iso = timestamp_fim.isoformat()
        
        # Calcular duração total e do upload
        duracao_total_segundos = timestamp_upload_fim - timestamp_inicio_unix
        duracao_upload_segundos = timestamp_upload_fim - timestamp_upload_inicio
        
        # Calcular velocidade de upload (bytes por segundo e Mbps)
        velocidade_bytes_por_segundo = size / duracao_upload_segundos if duracao_upload_segundos > 0 else 0
        velocidade_mbps = (velocidade_bytes_por_segundo * 8) / (1024 * 1024)  # Converter para Mbps
        
        # Formatação de durações
        duracao_total_info = format_duration_human(duracao_total_segundos)
        duracao_upload_info = format_duration_human(duracao_upload_segundos)
        
        # Limpar arquivo temporário se existir
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
        
        # URL pública do arquivo
        file_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{s3_key}"
        
        print(f"✅ Upload concluído: {file_url}")
        logger.info(f"Upload concluído: {file_url}")
        
        # Montar resposta enriquecida
        arquivo_data = {
            "id": unique_filename,
            "nome_original": original_filename,
            "nome_armazenado": unique_filename,
            "hash_md5": file_hash,
            "tamanho": size_info,
            "tipo_mime": file.content_type or 'application/octet-stream',
            "extensao": file_extension,
            "categoria": file_category,
            "diretorio": target_folder,
            "caminho_completo": s3_key,
            "url_publica": file_url,
            "url_cdn": file_url,
            "descricao_humana": f"Arquivo {file_category['categoria_descricao'].lower()} '{original_filename}' ({size_info['descricao_humana']})"
        }
        
        # Adicionar metadados de mídia se disponíveis
        if media_metadata:
            arquivo_data["midia"] = media_metadata
        
        response_data = {
            "success": True,
            "arquivo": arquivo_data,
            "sessao": {
                "id_sessao": str(uuid.uuid4()),
                "ip_cliente": client_info["ip"],
                "ip_original": client_info["ip_original"],
                "user_agent": client_info["user_agent"],
                "referer": client_info["referer"],
                "idioma_preferido": client_info["accept_language"],
                "headers": client_info["headers"],
                "descricao_humana": f"Requisição de {client_info['ip']} via {client_info['user_agent'][:50]}..."
            },
            "upload": {
                "timestamp_inicio": timestamp_inicio_iso,
                "timestamp_inicio_unix": timestamp_inicio_unix,
                "timestamp_fim": timestamp_fim_iso,
                "timestamp_fim_unix": timestamp_upload_fim,
                "duracao_total": duracao_total_info,
                "duracao_upload": duracao_upload_info,
                "velocidade_bytes_por_segundo": round(velocidade_bytes_por_segundo, 2),
                "velocidade_mbps": round(velocidade_mbps, 2),
                "velocidade_formatted": f"{round(velocidade_mbps, 2)} Mbps",
                "status": "concluido",
                "bucket": SPACES_BUCKET,
                "regiao": SPACES_REGION,
                "endpoint": SPACES_ENDPOINT,
                "descricao_humana": f"Upload concluído em {duracao_upload_info['descricao_humana']} com velocidade média de {round(velocidade_mbps, 2)} Mbps"
            },
            "analytics": {
                "id_transacao": str(uuid.uuid4()),
                "timestamp_processamento": datetime.now().isoformat(),
                "tamanho_bytes": size,
                "tamanho_mb": round(size_info["megabytes"], 4),
                "duracao_segundos": round(duracao_total_segundos, 3),
                "velocidade_mbps": round(velocidade_mbps, 4),
                "categoria_arquivo": file_category["categoria"],
                "tipo_midia": file_category["tipo_midia"],
                "hash_arquivo": file_hash,
                "ip_cliente": client_info["ip"],
                "diretorio": target_folder,
                "metrica_performance": {
                    "tempo_processamento_ms": round(duracao_total_segundos * 1000, 2),
                    "tempo_upload_ms": round(duracao_upload_segundos * 1000, 2),
                    "throughput_bytes_per_sec": round(velocidade_bytes_por_segundo, 2),
                    "throughput_mbps": round(velocidade_mbps, 4)
                }
            },
            # Campos legados para compatibilidade
            "url": file_url,
            "filename": unique_filename,
            "original_filename": original_filename,
            "size": size,
            "content_type": file.content_type
        }
        
        return jsonify(response_data)
        
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
