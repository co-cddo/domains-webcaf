from django.apps import AppConfig


class WebcafConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webcaf.webcaf"
    label = "webcaf"

    def ready(self) -> None:
        from django.conf import settings

        from .caf32_router import FrameworkRouter

        framework_path = getattr(settings, "FRAMEWORK_PATH")
        self.framework_router = FrameworkRouter(framework_path)
        self.framework_router.all_route()
