import os
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Safely prints a diagnostic report of the environment-based configuration without exposing secrets."

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print non-secret values along with the status.',
        )

    def get_masked_value(self, value):
        if not value:
            return "<EMPTY>"
        
        value_str = str(value)
        if len(value_str) <= 4:
            return "****"
        return f"{value_str[:2]}****{value_str[-2:]}"

    def check_var(self, name, value, is_secret=False, verbose=False):
        if not value:
            self.stdout.write(self.style.ERROR(f"[MISSING] {name}"))
            return False
            
        if is_secret:
            display_value = self.get_masked_value(value)
        else:
            display_value = str(value) if verbose else "<SET>"
            
        if verbose or is_secret:
            self.stdout.write(self.style.SUCCESS(f"[OK]      {name} = {display_value}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"[OK]      {name}"))
            
        return True

    def handle(self, *args, **options):
        verbose = options['verbose']
        self.stdout.write(self.style.WARNING("=== Configuration Diagnostics ==="))
        self.stdout.write(f"DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE', 'Not Set')}")
        self.stdout.write(f"DEBUG: {settings.DEBUG}\n")

        self.stdout.write(self.style.WARNING("--- Database ---"))
        db = settings.DATABASES.get('default', {})
        self.check_var("POSTGRES_DB", db.get("NAME"), verbose=verbose)
        self.check_var("POSTGRES_USER", db.get("USER"), verbose=verbose)
        self.check_var("POSTGRES_PASSWORD", db.get("PASSWORD"), is_secret=True, verbose=verbose)
        self.check_var("POSTGRES_HOST", db.get("HOST"), verbose=verbose)

        self.stdout.write(self.style.WARNING("\n--- Infrastructure ---"))
        self.check_var("REDIS_URL", getattr(settings, "REDIS_URL", ""), is_secret=True, verbose=verbose)
        self.check_var("CELERY_BROKER_URL", getattr(settings, "CELERY_BROKER_URL", ""), is_secret=True, verbose=verbose)

        self.stdout.write(self.style.WARNING("\n--- Security & Network ---"))
        self.check_var("SECRET_KEY", settings.SECRET_KEY, is_secret=True, verbose=verbose)
        self.check_var("ALLOWED_HOSTS", settings.ALLOWED_HOSTS, verbose=verbose)
        self.check_var("CORS_ALLOWED_ORIGINS", getattr(settings, "CORS_ALLOWED_ORIGINS", []), verbose=verbose)
        self.check_var("CSRF_TRUSTED_ORIGINS", getattr(settings, "CSRF_TRUSTED_ORIGINS", []), verbose=verbose)
        self.check_var("FRONTEND_URL", getattr(settings, "FRONTEND_URL", ""), verbose=verbose)

        self.stdout.write(self.style.WARNING("\n--- Meta Integrations ---"))
        self.check_var("META_APP_ID", os.environ.get("META_APP_ID"), verbose=verbose)
        self.check_var("META_APP_SECRET", os.environ.get("META_APP_SECRET"), is_secret=True, verbose=verbose)
        self.check_var("META_VERIFY_TOKEN", os.environ.get("META_VERIFY_TOKEN"), is_secret=True, verbose=verbose)
        self.check_var("INSTAGRAM_ACCESS_TOKEN", os.environ.get("INSTAGRAM_ACCESS_TOKEN"), is_secret=True, verbose=verbose)
        self.check_var("WHATSAPP_PHONE_NUMBER_ID", os.environ.get("WHATSAPP_PHONE_NUMBER_ID"), verbose=verbose)
        self.check_var("WHATSAPP_ACCESS_TOKEN", os.environ.get("WHATSAPP_ACCESS_TOKEN"), is_secret=True, verbose=verbose)

        self.stdout.write(self.style.WARNING("\n=== Diagnostics Complete ==="))
