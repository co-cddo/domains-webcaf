from django.apps import AppConfig


class WebcafConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webcaf.webcaf"
    label = "webcaf"

    def ready(self) -> None:
        from django.conf import settings

        from .caf32_router import CAF32Router

        framework_path = getattr(settings, "FRAMEWORK_PATH")
        self.framework_router = CAF32Router(framework_path)
        self.framework_router.execute()
