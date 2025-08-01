import concurrent.futures

from django.db import close_old_connections

# Create a thread pool executor
ORM_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def run_async_orm(orm_func, *args, **kwargs):
    """Run ORM operations in a dedicated thread"""

    def _wrapper():
        try:
            result = orm_func(*args, **kwargs)
            return result
        finally:
            # Clean up database connections
            close_old_connections()

    return ORM_EXECUTOR.submit(_wrapper).result()


# Convenience methods
def create_model(model, **kwargs):
    return run_async_orm(model.objects.create, **kwargs)


def get_model(model, **kwargs):
    return run_async_orm(model.objects.get, **kwargs)


def exists_model(model, **kwargs):
    return run_async_orm(model.objects.filter(**kwargs).exists)


def delete_model(instance):
    return run_async_orm(instance.delete)
