"""
Constantes y especificaciones de plataforma para el sistema de gestión de materiales.
"""

# Roles de usuario
class UserRole:
    ADMIN = 'admin'
    REVIEWER = 'reviewer'
    CLIENT = 'client'
    
    CHOICES = [
        (ADMIN, 'Administrador'),
        (REVIEWER, 'Revisor'),
        (CLIENT, 'Cliente'),
    ]

# Tipos de material
class MaterialType:
    DOCUMENT = 'document'
    IMAGE = 'image'
    
    CHOICES = [
        (DOCUMENT, 'Documento'),
        (IMAGE, 'Imagen'),
    ]

# Estados de material
class MaterialStatus:
    PENDING = 'pending'
    IN_REVIEW = 'in_review'
    APPROVED = 'approved'
    NEEDS_CORRECTION = 'needs_correction'
    
    CHOICES = [
        (PENDING, 'Pendiente'),
        (IN_REVIEW, 'En Revisión'),
        (APPROVED, 'Aprobado'),
        (NEEDS_CORRECTION, 'Necesita Corrección'),
    ]

# Plataformas soportadas
class Platform:
    WEB_BRAND = 'web_brand'
    SAMSUNG_TIZEN = 'samsung_tizen'
    LG_WEBOS = 'lg_webos'
    ANDROID_GOOGLE_PLAY = 'android_google_play'
    AMAZON_APPSTORE = 'amazon_appstore'
    IOS_TVOS_APP_STORE = 'ios_tvos_app_store'
    
    CHOICES = [
        (WEB_BRAND, 'Web Brand'),
        (SAMSUNG_TIZEN, 'Samsung Tizen'),
        (LG_WEBOS, 'LG webOS'),
        (ANDROID_GOOGLE_PLAY, 'Android Google Play'),
        (AMAZON_APPSTORE, 'Amazon Appstore'),
        (IOS_TVOS_APP_STORE, 'iOS/tvOS App Store'),
    ]

# Especificaciones de plataforma - Source of Truth
PLATFORM_SPECS = {
    Platform.WEB_BRAND: {
        'logo': {
            'width': 482,
            'height': 108,
            'formats': ['PNG'],
            'transparent_bg': True,
            'max_size_mb': 10,
        },
        'logo_top': {
            'width': 400,
            'height': 377,
            'formats': ['PNG'],
            'transparent_bg': True,
            'max_size_mb': 10,
        },
        'placeholder': {
            'width': 220,
            'height': 160,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'background': {
            'width': 3480,
            'height': 2160,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'splash': {
            'width': 3480,
            'height': 2160,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
    },
    Platform.SAMSUNG_TIZEN: {
        'launcher_icon': {
            'width': 400,
            'height': 400,
            'formats': ['PNG'],
            'margin_recommended_px': 50,
            'max_size_mb': 10,
        },
        'splash': {
            'width': 3840,
            'height': 2160,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
    },
    Platform.LG_WEBOS: {
        'icon_80': {
            'width': 80,
            'height': 80,
            'formats': ['PNG'],
            'margin_recommended_px': 25,
            'max_size_mb': 10,
        },
        'large_icon': {
            'width': 130,
            'height': 130,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'background': {
            'width': 1920,
            'height': 1080,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'splash': {
            'width': 1920,
            'height': 1080,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
    },
    Platform.ANDROID_GOOGLE_PLAY: {
        'default_logo_services': {
            'width': 430,
            'height': 314,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'default_logo_vod': {
            'width': 300,
            'height': 440,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'logo_home': {
            'width': 1200,
            'height': 472,
            'formats': ['PNG'],
            'transparent_bg': True,
            'max_size_mb': 10,
        },
        'logo_watermark': {
            'width': 1200,
            'height': 472,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'background': {
            'width': 1920,
            'height': 1080,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'background_mobile': {
            'width': 1080,
            'height': 1920,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'logo_splash': {
            'width': 1000,
            'height': 1000,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'radio_background': {
            'width': 1920,
            'height': 1080,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'play_feature_graphic': {
            'width': 1024,
            'height': 500,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'play_banner_tv': {
            'width': 1280,
            'height': 720,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
    },
    Platform.AMAZON_APPSTORE: {
        'app_icon': {
            'width': 1280,
            'height': 720,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
        'background': {
            'width': 1920,
            'height': 1080,
            'formats': ['PNG'],
            'max_size_mb': 10,
        },
    },
    Platform.IOS_TVOS_APP_STORE: {
        'store_logo': {
            'width': 1920,
            'height': 1080,
            'formats': ['SVG'],
            'transparent_bg': True,
            'max_size_mb': 10,
        },
        'logo_top': {
            'width': 400,
            'height': 377,
            'formats': ['SVG'],
            'max_size_mb': 10,
        },
        'background_mobile': {
            'width': 4688,
            'height': 10150,
            'formats': ['SVG'],
            'max_size_mb': 10,
        },
        'background': {
            'width': 3480,
            'height': 2160,
            'formats': ['SVG'],
            'max_size_mb': 10,
        },
    },
}

# Estados de proyecto
class ProjectStatus:
    DRAFT = 'draft'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (DRAFT, 'Borrador'),
        (IN_PROGRESS, 'En Progreso'),
        (COMPLETED, 'Completado'),
        (CANCELLED, 'Cancelado'),
    ]

# Tipos de acción en audit log
class AuditAction:
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    APPROVE = 'approve'
    REJECT = 'reject'
    UPLOAD = 'upload'
    DOWNLOAD = 'download'
    SYNC_DRIVE = 'sync_drive'
    
    CHOICES = [
        (CREATE, 'Crear'),
        (UPDATE, 'Actualizar'),
        (DELETE, 'Eliminar'),
        (APPROVE, 'Aprobar'),
        (REJECT, 'Rechazar'),
        (UPLOAD, 'Subir'),
        (DOWNLOAD, 'Descargar'),
        (SYNC_DRIVE, 'Sincronizar Drive'),
    ]
