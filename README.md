# Material Management API

Sistema de gestión centralizada de materiales para publicación de aplicaciones en múltiples plataformas.

## 🚀 Características

- **Validación automática estricta** - Rechaza automáticamente archivos que no cumplan con las especificaciones
- **Soporte multi-plataforma** - Web Brand, Samsung Tizen, LG webOS, Android Google Play, Amazon Appstore, iOS/tvOS
- **Sistema de roles** - Administradores, Revisores y Clientes
- **Control de versiones** - Historial completo de cambios en materiales
- **Integración con Google Drive** - Almacenamiento en la nube
- **API REST completa** - Documentación automática con Swagger
- **Auditoría completa** - Log de todas las acciones del sistema
- **Dashboard con estadísticas** - Métricas en tiempo real

## 🛠️ Tecnologías

- **Backend**: Django 4.2.7 + Django REST Framework
- **Base de datos**: PostgreSQL (con fallback a SQLite)
- **Autenticación**: JWT (JSON Web Tokens)
- **Almacenamiento**: Google Drive API
- **Tareas asíncronas**: Celery + Redis
- **Documentación**: OpenAPI/Swagger
- **Validación de imágenes**: Pillow

## 📋 Requisitos

- Python 3.8+
- PostgreSQL 12+ (opcional, puede usar SQLite)
- Redis (para Celery)

## 🔧 Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd AppBack
```

2. **Crear entorno virtual**
```bash
python -m venv env
# Windows
env\Scripts\activate
# Linux/Mac
source env/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp env.example .env
# Editar .env con tus configuraciones
```

5. **Ejecutar migraciones**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Crear superusuario**
```bash
python manage.py createsuperuser
```

7. **Ejecutar servidor**
```bash
python manage.py runserver
```

## 📚 API Endpoints

### Autenticación
- `POST /api/auth/register/` - Registro de usuarios
- `POST /api/auth/login/` - Login con JWT
- `GET /api/auth/me/` - Información del usuario actual

### Proyectos
- `GET /api/projects/` - Listar proyectos
- `POST /api/projects/` - Crear proyecto
- `GET /api/projects/{id}/` - Detalle del proyecto
- `PUT /api/projects/{id}/` - Actualizar proyecto
- `DELETE /api/projects/{id}/` - Eliminar proyecto
- `GET /api/projects/{id}/materials/` - Materiales del proyecto
- `GET /api/projects/{id}/stats/` - Estadísticas del proyecto

### Materiales
- `GET /api/materials/` - Listar materiales
- `POST /api/materials/upload/` - Subir material (con validación automática)
- `GET /api/materials/{id}/` - Detalle del material
- `POST /api/materials/{id}/update_status/` - Actualizar estado
- `POST /api/materials/{id}/rollback/` - Rollback a versión anterior
- `GET /api/materials/{id}/versions/` - Versiones del material

### Aprobaciones
- `GET /api/approvals/` - Listar aprobaciones
- `POST /api/approvals/{id}/approve/` - Aprobar material
- `POST /api/approvals/{id}/reject/` - Rechazar material

### Dashboard
- `GET /api/dashboard/stats/` - Estadísticas generales
- `GET /api/platform-specs/list/` - Especificaciones de plataforma

## 🔒 Validación Automática

El sistema **rechaza automáticamente** archivos que no cumplan con las especificaciones:

### ❌ Archivos rechazados automáticamente:
- **Formato incorrecto** - Solo PNG, JPG, SVG según especificación
- **Dimensiones incorrectas** - Debe coincidir exactamente con las requeridas
- **Tamaño excesivo** - Máximo 10MB por archivo
- **Transparencia incorrecta** - Debe tener/non tener según especificación
- **Archivos corruptos** - Imágenes dañadas o inválidas
- **SVG malformados** - Sin viewBox, con elementos peligrosos

### ✅ Archivos aceptados:
- Cumplen exactamente con las especificaciones de la plataforma
- Tienen las dimensiones correctas
- Formato y transparencia según especificación
- Archivos íntegros y válidos

## 🎯 Especificaciones por Plataforma

### Web Brand
- Logo: 482x108px PNG con transparencia
- Logo Top: 400x377px PNG con transparencia
- Background: 3480x2160px PNG
- Splash: 3480x2160px PNG

### Samsung Tizen
- Launcher Icon: 400x400px PNG (margen 50px)
- Splash: 3840x2160px PNG

### LG webOS
- Icon 80: 80x80px PNG (margen 25px)
- Large Icon: 130x130px PNG
- Background: 1920x1080px PNG
- Splash: 1920x1080px PNG

### Android Google Play
- Logo Services: 430x314px PNG
- Logo VOD: 300x440px PNG
- Logo Home: 1200x472px PNG con transparencia
- Background: 1920x1080px PNG
- Background Mobile: 1080x1920px PNG
- Play Feature Graphic: 1024x500px PNG

### Amazon Appstore
- App Icon: 1280x720px PNG
- Background: 1920x1080px PNG

### iOS/tvOS App Store
- Store Logo: 1920x1080px SVG con transparencia
- Logo Top: 400x377px SVG
- Background: 3480x2160px SVG
- Background Mobile: 4688x10150px SVG

## 📊 Documentación de API

Una vez ejecutando el servidor, accede a:
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Schema JSON**: http://localhost:8000/api/schema/

## 🔧 Configuración Avanzada

### Google Drive
1. Crear proyecto en Google Cloud Console
2. Habilitar Google Drive API
3. Crear credenciales OAuth 2.0
4. Configurar variables en `.env`

### Celery (Tareas asíncronas)
```bash
# Terminal 1: Servidor Django
python manage.py runserver

# Terminal 2: Worker Celery
celery -A repositorio worker -l info

# Terminal 3: Beat (tareas programadas)
celery -A repositorio beat -l info
```

## 🚨 Importante

- **Validación estricta**: El sistema NO acepta archivos que no cumplan exactamente con las especificaciones
- **Sin revisión manual**: Los archivos se validan automáticamente al subir
- **Mensajes claros**: Los errores indican exactamente qué corregir
- **Auditoría completa**: Todas las acciones quedan registradas

## 📝 Licencia

Este proyecto es privado y confidencial.
