from django.apps import AppConfig


class DishesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dishes'

    def ready(self):
        """Import signals when the app is ready"""
        import dishes.signal  # Import the signals module
