from django.apps import AppConfig


class PractikumConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'practikum'
    
    def ready(self):
        """Подключаем сигналы при запуске приложения."""
        import practikum.signals

