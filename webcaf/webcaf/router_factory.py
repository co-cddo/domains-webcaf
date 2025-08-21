import inspect


class _RouterFactory:
    def __init__(self):
        # Prevent direct instantiation from outside this module
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        if caller_module is None or caller_module.__name__ != __name__:
            raise RuntimeError("Direct instantiation not allowed. Use create_instance().")

    @staticmethod
    def get_router(version):
        from webcaf import settings

        return settings.CAF_FRAMEWORKS[version]


ROUTE_FACTORY = _RouterFactory()
