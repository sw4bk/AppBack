"""
Servicios del sistema de gestión de materiales.
"""

import hashlib
import mimetypes
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image
from PIL.ExifTags import TAGS
import io
import logging
from django.core.exceptions import ValidationError
from django.conf import settings
from .constants import PLATFORM_SPECS, Platform
from .models import Material, PlatformSpec

logger = logging.getLogger(__name__)

class ImageValidationError(ValidationError):
    """Excepción específica para errores de validación de imágenes."""
    pass

class ImageValidator:
    """
    Servicio para validación de imágenes según especificaciones de plataforma.
    """
    
    def __init__(self):
        self.supported_formats = ['PNG', 'JPG', 'JPEG', 'SVG']
        self.max_file_size = 10 * 1024 * 1024  # 10MB por defecto
    
    def validate_image(self, file_content: bytes, platform: str, asset_key: str) -> Dict[str, Any]:
        """
        Valida una imagen según las especificaciones de la plataforma.
        RECHAZA AUTOMÁTICAMENTE archivos que no cumplan con las especificaciones.
        
        Args:
            file_content: Contenido del archivo en bytes
            platform: Plataforma de destino
            asset_key: Clave del asset (ej: logo, splash, background)
            
        Returns:
            Dict con información de validación y metadatos
            
        Raises:
            ImageValidationError: Si la validación falla (RECHAZO AUTOMÁTICO)
        """
        try:
            # Obtener especificaciones de la plataforma
            specs = self._get_platform_specs(platform, asset_key)
            if not specs:
                raise ImageValidationError(f"No se encontraron especificaciones para {platform}/{asset_key}")
            
            # Validar formato de archivo
            mime_type = self._get_mime_type(file_content)
            file_format = self._extract_format_from_mime(mime_type)
            
            if file_format not in specs.get('formats', []):
                raise ImageValidationError(
                    f"❌ RECHAZADO: Formato {file_format} no permitido. "
                    f"Formatos permitidos: {', '.join(specs['formats'])}"
                )
            
            # Validar tamaño de archivo
            file_size = len(file_content)
            max_size_bytes = specs.get('max_size_mb', 10) * 1024 * 1024
            
            if file_size > max_size_bytes:
                raise ImageValidationError(
                    f"❌ RECHAZADO: Archivo demasiado grande: {file_size / (1024*1024):.2f}MB. "
                    f"Tamaño máximo permitido: {specs['max_size_mb']}MB"
                )
            
            # Para SVG, validaciones básicas
            if file_format == 'SVG':
                return self._validate_svg(file_content, specs, mime_type, file_size)
            
            # Para imágenes raster (PNG, JPG), validaciones completas
            return self._validate_raster_image(file_content, specs, mime_type, file_size)
            
        except Exception as e:
            logger.error(f"Error validando imagen: {str(e)}")
            if isinstance(e, ImageValidationError):
                raise
            raise ImageValidationError(f"❌ RECHAZADO: Error interno validando imagen: {str(e)}")
    
    def _get_platform_specs(self, platform: str, asset_key: str) -> Optional[Dict]:
        """Obtiene las especificaciones de la plataforma desde la base de datos o constantes."""
        try:
            # Intentar obtener desde la base de datos primero
            platform_spec = PlatformSpec.objects.get(
                platform=platform, 
                asset_key=asset_key, 
                is_active=True
            )
            return platform_spec.specifications
        except PlatformSpec.DoesNotExist:
            # Fallback a constantes
            return PLATFORM_SPECS.get(platform, {}).get(asset_key)
    
    def _get_mime_type(self, file_content: bytes) -> str:
        """Detecta el tipo MIME del archivo."""
        # Detectar por magic bytes
        if file_content.startswith(b'\x89PNG'):
            return 'image/png'
        elif file_content.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif file_content.startswith(b'<svg') or file_content.startswith(b'<?xml'):
            return 'image/svg+xml'
        else:
            # Fallback a detección por extensión (menos confiable)
            return 'application/octet-stream'
    
    def _extract_format_from_mime(self, mime_type: str) -> str:
        """Extrae el formato de archivo del MIME type."""
        mime_to_format = {
            'image/png': 'PNG',
            'image/jpeg': 'JPG',
            'image/jpg': 'JPG',
            'image/svg+xml': 'SVG',
        }
        return mime_to_format.get(mime_type, 'UNKNOWN')
    
    def _validate_svg(self, file_content: bytes, specs: Dict, mime_type: str, file_size: int) -> Dict:
        """Valida archivos SVG con validaciones estrictas."""
        try:
            # Para SVG, validaciones básicas de contenido
            svg_content = file_content.decode('utf-8', errors='ignore')
            
            # Verificar que es un SVG válido
            if not ('<svg' in svg_content.lower() and '</svg>' in svg_content.lower()):
                raise ImageValidationError("❌ RECHAZADO: Archivo SVG inválido o corrupto")
            
            # Verificar que tenga atributos de viewBox o dimensiones
            if 'viewbox' not in svg_content.lower() and 'width' not in svg_content.lower():
                raise ImageValidationError(
                    "❌ RECHAZADO: SVG debe tener viewBox o dimensiones definidas"
                )
            
            # Verificar transparencia si es requerida
            has_transparency = (
                'transparent' in svg_content.lower() or 
                'rgba' in svg_content.lower() or
                'fill="none"' in svg_content.lower() or
                'fill:none' in svg_content.lower()
            )
            
            if specs.get('transparent_bg', False) and not has_transparency:
                raise ImageValidationError(
                    "❌ RECHAZADO: Se requiere transparencia para este asset SVG. "
                    "Use fill='none' o colores RGBA con transparencia."
                )
            
            # Verificar que no tenga transparencia si no se requiere
            if not specs.get('transparent_bg', False) and has_transparency:
                raise ImageValidationError(
                    "❌ RECHAZADO: Este asset SVG no debe tener transparencia. "
                    "Use un fondo sólido en lugar de transparencia."
                )
            
            # Verificar que no tenga elementos problemáticos
            problematic_elements = ['<script', '<iframe', '<object', '<embed']
            for element in problematic_elements:
                if element in svg_content.lower():
                    raise ImageValidationError(
                        f"❌ RECHAZADO: SVG contiene elemento no permitido: {element}"
                    )
            
            return {
                'valid': True,
                'format': 'SVG',
                'mime_type': mime_type,
                'file_size': file_size,
                'width': None,  # SVG no tiene dimensiones fijas
                'height': None,
                'has_transparency': has_transparency,
                'warnings': []
            }
            
        except UnicodeDecodeError:
            raise ImageValidationError("❌ RECHAZADO: Archivo SVG no es texto válido UTF-8")
        except Exception as e:
            if isinstance(e, ImageValidationError):
                raise
            raise ImageValidationError(f"❌ RECHAZADO: Error validando SVG: {str(e)}")
    
    def _validate_raster_image(self, file_content: bytes, specs: Dict, mime_type: str, file_size: int) -> Dict:
        """Valida imágenes raster (PNG, JPG) con validaciones estrictas."""
        try:
            # Abrir imagen con Pillow
            image = Image.open(io.BytesIO(file_content))
            
            # Obtener dimensiones
            width, height = image.size
            
            # Validar dimensiones exactas (RECHAZO AUTOMÁTICO si no coinciden)
            expected_width = specs.get('width')
            expected_height = specs.get('height')
            
            if expected_width and width != expected_width:
                raise ImageValidationError(
                    f"❌ RECHAZADO: Ancho incorrecto: {width}px. Se requiere exactamente: {expected_width}px"
                )
            
            if expected_height and height != expected_height:
                raise ImageValidationError(
                    f"❌ RECHAZADO: Alto incorrecto: {height}px. Se requiere exactamente: {expected_height}px"
                )
            
            # Validar transparencia (RECHAZO AUTOMÁTICO si no cumple)
            has_transparency = self._check_transparency(image)
            if specs.get('transparent_bg', False) and not has_transparency:
                raise ImageValidationError(
                    "❌ RECHAZADO: Se requiere transparencia para este asset. "
                    "El archivo debe tener canal alfa (RGBA o LA)."
                )
            
            # Validar que no tenga transparencia si no se requiere
            if not specs.get('transparent_bg', False) and has_transparency:
                raise ImageValidationError(
                    "❌ RECHAZADO: Este asset no debe tener transparencia. "
                    "Use un fondo sólido en lugar de canal alfa."
                )
            
            # Validar integridad del archivo
            try:
                # Intentar procesar la imagen para verificar que no esté corrupta
                image.verify()
            except Exception:
                raise ImageValidationError("❌ RECHAZADO: Archivo de imagen corrupto o inválido")
            
            # Generar warnings para margin_recommended_px (solo informativos)
            warnings = []
            margin_px = specs.get('margin_recommended_px')
            if margin_px:
                effective_width = width - (margin_px * 2)
                effective_height = height - (margin_px * 2)
                warnings.append(
                    f"ℹ️ Recomendado: margen de {margin_px}px. "
                    f"Área efectiva: {effective_width}x{effective_height}px"
                )
            
            return {
                'valid': True,
                'format': self._extract_format_from_mime(mime_type),
                'mime_type': mime_type,
                'file_size': file_size,
                'width': width,
                'height': height,
                'has_transparency': has_transparency,
                'warnings': warnings
            }
            
        except Exception as e:
            if isinstance(e, ImageValidationError):
                raise
            raise ImageValidationError(f"❌ RECHAZADO: Error procesando imagen: {str(e)}")
    
    def _check_transparency(self, image: Image.Image) -> bool:
        """Verifica si la imagen tiene transparencia."""
        if image.mode in ('RGBA', 'LA'):
            # Verificar si hay píxeles transparentes
            if image.mode == 'RGBA':
                alpha = image.split()[-1]
                return alpha.getextrema()[0] < 255
            elif image.mode == 'LA':
                alpha = image.split()[-1]
                return alpha.getextrema()[0] < 255
        return False
    
    def resize_image(self, file_content: bytes, target_width: int, target_height: int, 
                    maintain_aspect: bool = False) -> bytes:
        """
        Redimensiona una imagen manteniendo formato y transparencia.
        
        Args:
            file_content: Contenido original de la imagen
            target_width: Ancho objetivo
            target_height: Alto objetivo
            maintain_aspect: Si mantener proporción (crop si es necesario)
            
        Returns:
            Contenido de la imagen redimensionada en bytes
        """
        try:
            image = Image.open(io.BytesIO(file_content))
            original_format = image.format
            
            if maintain_aspect:
                # Mantener proporción, crop si es necesario
                image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                
                # Crear nueva imagen con el tamaño exacto
                new_image = Image.new(image.mode, (target_width, target_height), (0, 0, 0, 0))
                
                # Centrar la imagen redimensionada
                x = (target_width - image.width) // 2
                y = (target_height - image.height) // 2
                new_image.paste(image, (x, y))
                image = new_image
            else:
                # Redimensionar exactamente
                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Guardar en bytes manteniendo formato original
            output = io.BytesIO()
            save_kwargs = {'format': original_format}
            
            if original_format == 'PNG':
                save_kwargs['optimize'] = True
            elif original_format in ('JPEG', 'JPG'):
                save_kwargs['optimize'] = True
                save_kwargs['quality'] = 95
            
            image.save(output, **save_kwargs)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error redimensionando imagen: {str(e)}")
            raise ImageValidationError(f"Error redimensionando imagen: {str(e)}")

class DriveSyncService:
    """
    Servicio para sincronización con Google Drive.
    """
    
    def __init__(self):
        self.credentials_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
        self.token_file = settings.GOOGLE_DRIVE_TOKEN_FILE
        self.base_folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    
    def create_project_structure(self, project) -> Dict[str, str]:
        """
        Crea la estructura de carpetas en Drive para un proyecto.
        
        Args:
            project: Instancia del proyecto
            
        Returns:
            Dict con IDs y URLs de las carpetas creadas
        """
        # TODO: Implementar cuando se configure Google Drive API
        logger.info(f"Creando estructura de Drive para proyecto: {project.name}")
        return {
            'project_folder_id': 'placeholder_id',
            'project_folder_url': 'https://drive.google.com/drive/folders/placeholder_id',
            'documents_folder_id': 'placeholder_docs_id',
            'images_folder_id': 'placeholder_images_id'
        }
    
    def upload_file(self, file_content: bytes, file_name: str, folder_id: str) -> Dict[str, str]:
        """
        Sube un archivo a Google Drive.
        
        Args:
            file_content: Contenido del archivo
            file_name: Nombre del archivo
            folder_id: ID de la carpeta destino
            
        Returns:
            Dict con ID y URL del archivo subido
        """
        # TODO: Implementar cuando se configure Google Drive API
        logger.info(f"Subiendo archivo {file_name} a carpeta {folder_id}")
        return {
            'file_id': 'placeholder_file_id',
            'file_url': f'https://drive.google.com/file/d/placeholder_file_id/view'
        }

class NotificationService:
    """
    Servicio para notificaciones via webhooks/websockets.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_material_status_change(self, material, old_status: str, new_status: str, user):
        """
        Envía notificación de cambio de estado de material.
        
        Args:
            material: Instancia del material
            old_status: Estado anterior
            new_status: Estado nuevo
            user: Usuario que realizó el cambio
        """
        # TODO: Implementar webhooks/websockets
        self.logger.info(
            f"Notificación: Material {material.id} cambió de {old_status} a {new_status} "
            f"por {user.username}"
        )
    
    def send_approval_request(self, material, reviewer):
        """
        Envía notificación de solicitud de aprobación.
        
        Args:
            material: Instancia del material
            reviewer: Usuario revisor
        """
        # TODO: Implementar webhooks/websockets
        self.logger.info(
            f"Notificación: Solicitud de aprobación para material {material.id} "
            f"asignado a {reviewer.username}"
        )

class AuditService:
    """
    Servicio para logging de auditoría.
    """
    
    @staticmethod
    def log_action(action: str, actor, entity_type: str, entity_id: int, 
                   payload: Dict = None, request=None):
        """
        Registra una acción en el log de auditoría.
        
        Args:
            action: Tipo de acción realizada
            actor: Usuario que realizó la acción
            entity_type: Tipo de entidad afectada
            entity_id: ID de la entidad
            payload: Datos adicionales
            request: Request HTTP (opcional)
        """
        from .models import AuditLog
        
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT')
        
        AuditLog.objects.create(
            action=action,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent
        )

class MaterialService:
    """
    Servicio principal para gestión de materiales.
    """
    
    def __init__(self):
        self.image_validator = ImageValidator()
        self.drive_sync = DriveSyncService()
        self.notifications = NotificationService()
        self.audit = AuditService()
    
    def create_material(self, project, platform: str, asset_key: str, 
                       file_content: bytes, file_name: str, uploaded_by, request=None) -> Material:
        """
        Crea un nuevo material validando el archivo.
        RECHAZA AUTOMÁTICAMENTE archivos que no cumplan con las especificaciones.
        
        Args:
            project: Proyecto al que pertenece
            platform: Plataforma de destino
            asset_key: Clave del asset
            file_content: Contenido del archivo
            file_name: Nombre del archivo
            uploaded_by: Usuario que sube el archivo
            request: Request HTTP (opcional)
            
        Returns:
            Instancia del material creado (solo si pasa validación)
            
        Raises:
            ImageValidationError: Si el archivo no cumple con las especificaciones
        """
        # Validar imagen (RECHAZO AUTOMÁTICO si no cumple)
        validation_result = self.image_validator.validate_image(file_content, platform, asset_key)
        
        # Calcular hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Determinar tipo de material
        material_type = 'image' if validation_result['format'] in ['PNG', 'JPG', 'SVG'] else 'document'
        
        # Crear material (solo si pasa todas las validaciones)
        material = Material.objects.create(
            project=project,
            material_type=material_type,
            platform=platform,
            asset_key=asset_key,
            file_name=file_name,
            file_size=len(file_content),
            file_hash=file_hash,
            mime_type=validation_result['mime_type'],
            width=validation_result.get('width'),
            height=validation_result.get('height'),
            has_transparency=validation_result.get('has_transparency', False),
            uploaded_by=uploaded_by,
            status='pending'  # Solo llega aquí si pasó todas las validaciones
        )
        
        # Log de auditoría
        self.audit.log_action(
            action='upload',
            actor=uploaded_by,
            entity_type='Material',
            entity_id=material.id,
            payload={
                'platform': platform,
                'asset_key': asset_key,
                'file_size': len(file_content),
                'validation_warnings': validation_result.get('warnings', []),
                'validation_status': 'passed'
            },
            request=request
        )
        
        return material
    
    def update_material_status(self, material, new_status: str, user, comments: str = "", request=None):
        """
        Actualiza el estado de un material.
        
        Args:
            material: Instancia del material
            new_status: Nuevo estado
            user: Usuario que realiza el cambio
            comments: Comentarios del cambio
            request: Request HTTP (opcional)
        """
        old_status = material.status
        material.status = new_status
        if comments:
            material.comments = comments
        material.save()
        
        # Log de auditoría
        self.audit.log_action(
            action='update',
            actor=user,
            entity_type='Material',
            entity_id=material.id,
            payload={
                'old_status': old_status,
                'new_status': new_status,
                'comments': comments
            },
            request=request
        )
        
        # Enviar notificación
        self.notifications.send_material_status_change(material, old_status, new_status, user)
