from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    User, Project, Material, MaterialVersion, Approval, 
    PlatformSpec, DriveLink, AuditLog
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin personalizado para usuarios."""
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'company', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'company']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información adicional', {'fields': ('role', 'phone', 'company')}),
    )

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin para proyectos."""
    list_display = ['name', 'company', 'app_name', 'status', 'created_by', 'created_at', 'is_overdue']
    list_filter = ['status', 'company', 'created_at', 'deadline']
    search_fields = ['name', 'app_name', 'company', 'description']
    readonly_fields = ['created_at', 'updated_at', 'completion_percentage']
    filter_horizontal = ['assigned_reviewers']
    
    def is_overdue(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">⚠️ Atrasado</span>')
        return format_html('<span style="color: green;">✅ En tiempo</span>')
    is_overdue.short_description = 'Estado de plazo'

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    """Admin para materiales."""
    list_display = ['file_name', 'project', 'platform', 'asset_key', 'status', 'file_size_mb', 'uploaded_by', 'created_at']
    list_filter = ['status', 'platform', 'material_type', 'has_transparency', 'created_at']
    search_fields = ['file_name', 'asset_key', 'project__name', 'project__app_name']
    readonly_fields = ['file_hash', 'created_at', 'updated_at', 'file_size_mb']
    
    def file_size_mb(self, obj):
        return f"{obj.file_size_mb} MB"
    file_size_mb.short_description = 'Tamaño'

@admin.register(MaterialVersion)
class MaterialVersionAdmin(admin.ModelAdmin):
    """Admin para versiones de materiales."""
    list_display = ['material', 'version_number', 'file_name', 'file_size_mb', 'created_by', 'created_at']
    list_filter = ['created_at', 'material__platform']
    search_fields = ['file_name', 'material__file_name', 'change_description']
    readonly_fields = ['created_at', 'file_size_mb']
    
    def file_size_mb(self, obj):
        return f"{obj.file_size_mb} MB"
    file_size_mb.short_description = 'Tamaño'

@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    """Admin para aprobaciones."""
    list_display = ['material', 'reviewer', 'status', 'approved_at', 'created_at']
    list_filter = ['status', 'created_at', 'approved_at']
    search_fields = ['material__file_name', 'reviewer__username', 'comments']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']

@admin.register(PlatformSpec)
class PlatformSpecAdmin(admin.ModelAdmin):
    """Admin para especificaciones de plataforma."""
    list_display = ['platform', 'asset_key', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['platform', 'asset_key']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(DriveLink)
class DriveLinkAdmin(admin.ModelAdmin):
    """Admin para enlaces de Drive."""
    list_display = ['project', 'folder_path', 'material', 'created_at']
    list_filter = ['created_at', 'project']
    search_fields = ['folder_path', 'project__name', 'material__file_name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin para logs de auditoría."""
    list_display = ['actor', 'action', 'entity_type', 'entity_id', 'created_at']
    list_filter = ['action', 'entity_type', 'created_at', 'actor']
    search_fields = ['actor__username', 'entity_type', 'payload']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
