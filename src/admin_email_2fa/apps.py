from django.apps import AppConfig


class AdminEmail2FAConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_email_2fa"

    def ready(self):
        from .settings import NAMESPACE, reload_api_settings  # noqa: F401

        reload_api_settings(setting=NAMESPACE)

        super().ready()
