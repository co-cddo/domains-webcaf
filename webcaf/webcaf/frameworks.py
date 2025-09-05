from webcaf.webcaf.abcs import FrameworkRouter
from webcaf.webcaf.caf.routers import CAF32Router, CAF40Router

routers_mapping = {"caf32": CAF32Router, "caf40": CAF40Router}

routers: dict[str, FrameworkRouter] = {}


def execute_routers() -> None:
    for key, router_class in routers_mapping.items():
        routers[key] = router_class()
        routers[key].execute()
