from django.apps import AppConfig


class AgilyConfig(AppConfig):
    name = 'agily'
    verbose_name = 'Agily'

    def ready(self):
        # Import signals to register them
        import agily.signals