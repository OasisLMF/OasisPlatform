# The idea here is to provide a configurable
# storage backend, currently only LocalStorage
# is implemented but this could be replaced with
# s3 etc

from .local_storage import LocalStorage


def get_storage_backend(root):
    return LocalStorage(root)
