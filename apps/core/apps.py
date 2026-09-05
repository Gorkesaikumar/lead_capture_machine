from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core Infrastructure"

    def ready(self):
        from corsheaders.signals import check_request_enabled
        from .public_cors import public_form_cors
        check_request_enabled.connect(public_form_cors, dispatch_uid="v4-public-form-cors")
