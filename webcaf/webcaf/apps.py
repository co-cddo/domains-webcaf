from django.apps import AppConfig


class WebcafConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webcaf.webcaf"
    label = "webcaf"

    def ready(self) -> None:
        from .frameworks import execute_routers

        execute_routers()
