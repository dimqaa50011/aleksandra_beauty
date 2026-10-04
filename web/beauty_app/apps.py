from django.apps import AppConfig

class BeautyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'beauty_app'

    def ready(self):
        # Импортируем сигналы при запуске приложения
        import beauty_app.signals