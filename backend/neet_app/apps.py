from django.apps import AppConfig


class NeetAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'neet_app'

    def ready(self):
        """Import signals when the app is ready"""
        import neet_app.signals