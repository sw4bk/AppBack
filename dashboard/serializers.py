"""
Serializers para la API REST del sistema de gestión de materiales.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import (
    User, Project, Material, MaterialVersion, Approval, 
    PlatformSpec, DriveLink, AuditLog
)
from .constants import UserRole, MaterialType, MaterialStatus, Platform, ProjectStatus
from .services import ImageValidator, MaterialService

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuarios."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'role', 'phone', 'company', 'password', 'password_confirm'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'password_confirm': {'write_only': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    """Serializer para usuarios."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'phone', 'company', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProjectSerializer(serializers.ModelSerializer):
    """Serializer para proyectos."""
    created_by = UserSerializer(read_only=True)
    assigned_reviewers = UserSerializer(many=True, read_only=True)
    reviewer_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    completion_percentage = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'company', 'app_name', 'description', 'status',
            'status_display', 'deadline', 'created_by', 'assigned_reviewers',
            'reviewer_ids', 'completion_percentage', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        reviewer_ids = validated_data.pop('reviewer_ids', [])
        project = Project.objects.create(**validated_data)
        
        if reviewer_ids:
            reviewers = User.objects.filter(id__in=reviewer_ids, role=UserRole.REVIEWER)
            project.assigned_reviewers.set(reviewers)
        
        return project
    
    def update(self, instance, validated_data):
        reviewer_ids = validated_data.pop('reviewer_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if reviewer_ids is not None:
            reviewers = User.objects.filter(id__in=reviewer_ids, role=UserRole.REVIEWER)
            instance.assigned_reviewers.set(reviewers)
        
        return instance

class PlatformSpecSerializer(serializers.ModelSerializer):
    """Serializer para especificaciones de plataforma."""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    
    class Meta:
        model = PlatformSpec
        fields = [
            'id', 'platform', 'platform_display', 'asset_key', 
            'specifications', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class MaterialVersionSerializer(serializers.ModelSerializer):
    """Serializer para versiones de materiales."""
    created_by = UserSerializer(read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    
    class Meta:
        model = MaterialVersion
        fields = [
            'id', 'version_number', 'file_name', 'file_size', 'file_size_mb',
            'file_hash', 'mime_type', 'width', 'height', 'has_transparency',
            'storage_url', 'change_description', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class MaterialSerializer(serializers.ModelSerializer):
    """Serializer para materiales."""
    project = ProjectSerializer(read_only=True)
    project_id = serializers.IntegerField(write_only=True)
    uploaded_by = UserSerializer(read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    versions = MaterialVersionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Material
        fields = [
            'id', 'project', 'project_id', 'material_type', 'material_type_display',
            'platform', 'platform_display', 'asset_key', 'file_name', 'file_size',
            'file_size_mb', 'file_hash', 'mime_type', 'width', 'height',
            'has_transparency', 'status', 'status_display', 'storage_url',
            'comments', 'uploaded_by', 'versions', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_hash', 'uploaded_by', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        project_id = validated_data.pop('project_id')
        project = Project.objects.get(id=project_id)
        validated_data['project'] = project
        return Material.objects.create(**validated_data)

class MaterialUploadSerializer(serializers.Serializer):
    """Serializer para subida de archivos de materiales."""
    project_id = serializers.IntegerField()
    platform = serializers.ChoiceField(choices=Platform.CHOICES)
    asset_key = serializers.CharField(max_length=50)
    file = serializers.FileField()
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate_file(self, value):
        """Valida el archivo subido."""
        if value.size > 10 * 1024 * 1024:  # 10MB
            raise serializers.ValidationError("El archivo es demasiado grande. Máximo 10MB.")
        
        # Validar tipo MIME
        allowed_types = ['image/png', 'image/jpeg', 'image/svg+xml']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Tipo de archivo no permitido. Tipos permitidos: {', '.join(allowed_types)}"
            )
        
        return value
    
    def validate(self, attrs):
        """Validación cruzada de datos."""
        project_id = attrs.get('project_id')
        platform = attrs.get('platform')
        asset_key = attrs.get('asset_key')
        
        # Verificar que el proyecto existe
        try:
            project = Project.objects.get(id=project_id)
            attrs['project'] = project
        except Project.DoesNotExist:
            raise serializers.ValidationError("Proyecto no encontrado.")
        
        # Verificar que la combinación platform/asset_key es válida
        from .constants import PLATFORM_SPECS
        if platform not in PLATFORM_SPECS:
            raise serializers.ValidationError(f"Plataforma {platform} no soportada.")
        
        if asset_key not in PLATFORM_SPECS[platform]:
            raise serializers.ValidationError(
                f"Asset key {asset_key} no válido para plataforma {platform}."
            )
        
        return attrs

class ApprovalSerializer(serializers.ModelSerializer):
    """Serializer para aprobaciones."""
    material = MaterialSerializer(read_only=True)
    reviewer = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Approval
        fields = [
            'id', 'material', 'reviewer', 'status', 'status_display',
            'comments', 'approved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'approved_at', 'created_at', 'updated_at']

class DriveLinkSerializer(serializers.ModelSerializer):
    """Serializer para enlaces de Drive."""
    project = ProjectSerializer(read_only=True)
    material = MaterialSerializer(read_only=True)
    
    class Meta:
        model = DriveLink
        fields = [
            'id', 'project', 'material', 'folder_path', 'folder_id',
            'folder_url', 'file_id', 'file_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de auditoría."""
    actor = UserSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'action', 'action_display', 'actor', 'entity_type',
            'entity_id', 'payload', 'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class MaterialStatusUpdateSerializer(serializers.Serializer):
    """Serializer para actualización de estado de materiales."""
    status = serializers.ChoiceField(choices=MaterialStatus.CHOICES)
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate_status(self, value):
        """Valida transiciones de estado."""
        # TODO: Implementar lógica de transiciones válidas
        return value

class MaterialRollbackSerializer(serializers.Serializer):
    """Serializer para rollback de materiales."""
    version_id = serializers.IntegerField()
    
    def validate_version_id(self, value):
        """Valida que la versión existe y pertenece al material."""
        material_id = self.context.get('material_id')
        if not material_id:
            raise serializers.ValidationError("Material ID requerido en contexto.")
        
        try:
            version = MaterialVersion.objects.get(
                id=value, 
                material_id=material_id
            )
            return value
        except MaterialVersion.DoesNotExist:
            raise serializers.ValidationError("Versión no encontrada.")

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas del dashboard."""
    total_projects = serializers.IntegerField()
    total_materials = serializers.IntegerField()
    pending_materials = serializers.IntegerField()
    approved_materials = serializers.IntegerField()
    overdue_projects = serializers.IntegerField()
    avg_approval_time_hours = serializers.FloatField()
    materials_by_status = serializers.DictField()
    materials_by_platform = serializers.DictField()
    recent_activities = serializers.ListField()

class PlatformSpecsListSerializer(serializers.Serializer):
    """Serializer para listado de especificaciones de plataforma."""
    platform = serializers.CharField()
    platform_display = serializers.CharField()
    assets = serializers.DictField()

class LoginSerializer(serializers.Serializer):
    """Serializer para login de usuarios."""
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("Credenciales inválidas.")
            if not user.is_active:
                raise serializers.ValidationError("Usuario inactivo.")
            attrs['user'] = user
        else:
            raise serializers.ValidationError("Username y password requeridos.")
        
        return attrs
