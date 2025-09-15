from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import hashlib
import json
from .constants import (
    UserRole, MaterialType, MaterialStatus, Platform, ProjectStatus, AuditAction
)

class User(AbstractUser):
    """
    Usuario extendido con roles específicos del sistema.
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.CHOICES,
        default=UserRole.CLIENT,
        help_text="Rol del usuario en el sistema"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Teléfono de contacto"
    )
    company = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Empresa del usuario"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    @property
    def is_reviewer(self):
        return self.role == UserRole.REVIEWER
    
    @property
    def is_client(self):
        return self.role == UserRole.CLIENT

class Project(models.Model):
    """
    Proyecto que agrupa materiales para una app específica.
    """
    name = models.CharField(
        max_length=200,
        help_text="Nombre del proyecto"
    )
    company = models.CharField(
        max_length=100,
        help_text="Empresa cliente"
    )
    app_name = models.CharField(
        max_length=100,
        help_text="Nombre de la aplicación"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción del proyecto"
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.CHOICES,
        default=ProjectStatus.DRAFT,
        help_text="Estado del proyecto"
    )
    deadline = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Fecha límite del proyecto"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_projects',
        help_text="Usuario que creó el proyecto"
    )
    assigned_reviewers = models.ManyToManyField(
        User,
        related_name='assigned_projects',
        blank=True,
        help_text="Revisores asignados al proyecto"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company} - {self.app_name}"
    
    @property
    def is_overdue(self):
        if not self.deadline:
            return False
        return timezone.now() > self.deadline
    
    @property
    def completion_percentage(self):
        """Calcula el porcentaje de completado basado en materiales aprobados."""
        total_materials = self.materials.count()
        if total_materials == 0:
            return 0
        approved_materials = self.materials.filter(status=MaterialStatus.APPROVED).count()
        return round((approved_materials / total_materials) * 100, 2)

class PlatformSpec(models.Model):
    """
    Especificaciones de plataforma - Source of Truth para validaciones.
    """
    platform = models.CharField(
        max_length=50,
        choices=Platform.CHOICES,
        help_text="Plataforma de la tienda"
    )
    asset_key = models.CharField(
        max_length=50,
        help_text="Clave del asset (ej: logo, splash, background)"
    )
    specifications = models.JSONField(
        help_text="Especificaciones técnicas del asset"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Si la especificación está activa"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Especificación de Plataforma"
        verbose_name_plural = "Especificaciones de Plataforma"
        unique_together = ['platform', 'asset_key']
        ordering = ['platform', 'asset_key']
    
    def __str__(self):
        return f"{self.get_platform_display()} - {self.asset_key}"

class Material(models.Model):
    """
    Material (documento o imagen) para publicación en tiendas.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='materials',
        help_text="Proyecto al que pertenece el material"
    )
    material_type = models.CharField(
        max_length=20,
        choices=MaterialType.CHOICES,
        help_text="Tipo de material"
    )
    platform = models.CharField(
        max_length=50,
        choices=Platform.CHOICES,
        help_text="Plataforma de destino"
    )
    asset_key = models.CharField(
        max_length=50,
        help_text="Clave del asset (ej: logo, splash, background)"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Nombre del archivo original"
    )
    file_size = models.PositiveIntegerField(
        help_text="Tamaño del archivo en bytes"
    )
    file_hash = models.CharField(
        max_length=64,
        help_text="Hash SHA-256 del archivo"
    )
    mime_type = models.CharField(
        max_length=100,
        help_text="Tipo MIME del archivo"
    )
    width = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Ancho en píxeles (para imágenes)"
    )
    height = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Alto en píxeles (para imágenes)"
    )
    has_transparency = models.BooleanField(
        default=False,
        help_text="Si el archivo tiene transparencia"
    )
    status = models.CharField(
        max_length=20,
        choices=MaterialStatus.CHOICES,
        default=MaterialStatus.PENDING,
        help_text="Estado del material"
    )
    storage_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL del archivo en Google Drive"
    )
    comments = models.TextField(
        blank=True,
        null=True,
        help_text="Comentarios sobre el material"
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_materials',
        help_text="Usuario que subió el material"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiales"
        ordering = ['-created_at']
        unique_together = ['project', 'platform', 'asset_key']
    
    def __str__(self):
        return f"{self.project.app_name} - {self.get_platform_display()} - {self.asset_key}"
    
    def calculate_file_hash(self, file_content):
        """Calcula el hash SHA-256 del contenido del archivo."""
        return hashlib.sha256(file_content).hexdigest()
    
    @property
    def file_size_mb(self):
        """Retorna el tamaño del archivo en MB."""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_image(self):
        return self.material_type == MaterialType.IMAGE
    
    @property
    def is_document(self):
        return self.material_type == MaterialType.DOCUMENT

class MaterialVersion(models.Model):
    """
    Versión de un material para control de versiones.
    """
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='versions',
        help_text="Material al que pertenece esta versión"
    )
    version_number = models.PositiveIntegerField(
        help_text="Número de versión"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Nombre del archivo de esta versión"
    )
    file_size = models.PositiveIntegerField(
        help_text="Tamaño del archivo en bytes"
    )
    file_hash = models.CharField(
        max_length=64,
        help_text="Hash SHA-256 del archivo"
    )
    mime_type = models.CharField(
        max_length=100,
        help_text="Tipo MIME del archivo"
    )
    width = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Ancho en píxeles (para imágenes)"
    )
    height = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Alto en píxeles (para imágenes)"
    )
    has_transparency = models.BooleanField(
        default=False,
        help_text="Si el archivo tiene transparencia"
    )
    storage_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL del archivo en Google Drive"
    )
    change_description = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción de los cambios en esta versión"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_versions',
        help_text="Usuario que creó esta versión"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Versión de Material"
        verbose_name_plural = "Versiones de Material"
        ordering = ['-created_at']
        unique_together = ['material', 'version_number']
    
    def __str__(self):
        return f"{self.material} - v{self.version_number}"
    
    @property
    def file_size_mb(self):
        """Retorna el tamaño del archivo en MB."""
        return round(self.file_size / (1024 * 1024), 2)

class Approval(models.Model):
    """
    Proceso de aprobación de materiales.
    """
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='approvals',
        help_text="Material a aprobar"
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='approvals',
        help_text="Revisor asignado"
    )
    status = models.CharField(
        max_length=20,
        choices=MaterialStatus.CHOICES,
        default=MaterialStatus.PENDING,
        help_text="Estado de la aprobación"
    )
    comments = models.TextField(
        blank=True,
        null=True,
        help_text="Comentarios del revisor"
    )
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Fecha de aprobación"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Aprobación"
        verbose_name_plural = "Aprobaciones"
        ordering = ['-created_at']
        unique_together = ['material', 'reviewer']
    
    def __str__(self):
        return f"{self.material} - {self.reviewer.username}"
    
    def approve(self, comments=""):
        """Aprueba el material."""
        self.status = MaterialStatus.APPROVED
        self.comments = comments
        self.approved_at = timezone.now()
        self.save()
        
        # Actualizar el estado del material
        self.material.status = MaterialStatus.APPROVED
        self.material.save()
    
    def reject(self, comments=""):
        """Rechaza el material."""
        self.status = MaterialStatus.NEEDS_CORRECTION
        self.comments = comments
        self.save()
        
        # Actualizar el estado del material
        self.material.status = MaterialStatus.NEEDS_CORRECTION
        self.material.save()

class DriveLink(models.Model):
    """
    Enlaces a archivos en Google Drive.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='drive_links',
        help_text="Proyecto al que pertenece el enlace"
    )
    folder_path = models.CharField(
        max_length=500,
        help_text="Ruta de la carpeta en Drive"
    )
    folder_id = models.CharField(
        max_length=100,
        help_text="ID de la carpeta en Drive"
    )
    folder_url = models.URLField(
        help_text="URL de la carpeta en Drive"
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='drive_links',
        blank=True,
        null=True,
        help_text="Material asociado (opcional)"
    )
    file_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID del archivo en Drive"
    )
    file_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL del archivo en Drive"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Enlace de Drive"
        verbose_name_plural = "Enlaces de Drive"
        ordering = ['-created_at']
    
    def __str__(self):
        if self.material:
            return f"{self.project} - {self.material.asset_key}"
        return f"{self.project} - {self.folder_path}"

class AuditLog(models.Model):
    """
    Log de auditoría para todas las acciones del sistema.
    """
    action = models.CharField(
        max_length=20,
        choices=AuditAction.CHOICES,
        help_text="Acción realizada"
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text="Usuario que realizó la acción"
    )
    entity_type = models.CharField(
        max_length=50,
        help_text="Tipo de entidad afectada"
    )
    entity_id = models.PositiveIntegerField(
        help_text="ID de la entidad afectada"
    )
    payload = models.JSONField(
        blank=True,
        null=True,
        help_text="Datos adicionales de la acción"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="Dirección IP del usuario"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="User Agent del navegador"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]
    
    def __str__(self):
        return f"{self.actor.username} - {self.get_action_display()} - {self.entity_type}:{self.entity_id}"
