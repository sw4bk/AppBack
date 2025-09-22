"""
Comando para inicializar datos de prueba del sistema.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from dashboard.models import PlatformSpec
from dashboard.constants import PLATFORM_SPECS, Platform

User = get_user_model()

class Command(BaseCommand):
    help = 'Inicializa datos de prueba del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Crear superusuario de prueba',
        )
        parser.add_argument(
            '--create-platform-specs',
            action='store_true',
            help='Crear especificaciones de plataforma',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando inicialización de datos...'))
        
        if options['create_superuser']:
            self.create_superuser()
        
        if options['create_platform_specs']:
            self.create_platform_specs()
        
        self.stdout.write(self.style.SUCCESS('Inicialización completada!'))

    def create_superuser(self):
        """Crear superusuario de prueba."""
        self.stdout.write('Creando superusuario...')
        
        if User.objects.filter(username='admin').exists():
            self.stdout.write(self.style.WARNING('Superusuario ya existe'))
            return
        
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Administrador',
            last_name='Sistema',
            role='admin',
            company='Material Management'
        )
        
        self.stdout.write(self.style.SUCCESS('Superusuario creado: admin/admin123'))

    def create_platform_specs(self):
        """Crear especificaciones de plataforma en la base de datos."""
        self.stdout.write('Creando especificaciones de plataforma...')
        
        created_count = 0
        
        with transaction.atomic():
            for platform_key, platform_specs in PLATFORM_SPECS.items():
                for asset_key, specs in platform_specs.items():
                    # Verificar si ya existe
                    if PlatformSpec.objects.filter(
                        platform=platform_key, 
                        asset_key=asset_key
                    ).exists():
                        continue
                    
                    # Crear especificación
                    PlatformSpec.objects.create(
                        platform=platform_key,
                        asset_key=asset_key,
                        specifications=specs,
                        is_active=True
                    )
                    created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Creadas {created_count} especificaciones de plataforma')
        )
