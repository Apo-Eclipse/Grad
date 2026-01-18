from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'features.notifications'

    def ready(self):
        import features.notifications.signals
