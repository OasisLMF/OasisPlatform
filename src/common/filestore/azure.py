import os

from oasis_data_manager.filestore.backends.azure_abfs import AzureABFSStorage


class ContainerRootedAzureStorage(AzureABFSStorage):
    """Azure storage whose keys are relative to the container, not to AZURE_LOCATION.

    `AzureABFSStorage` uses AZURE_LOCATION as its root dir, so the keys it returns and
    accepts are relative to that location. The server works with container-relative
    blob names (`file_storage_link()` returns '<server location>/<name>' and
    `is_in_container()` checks the raw blob name), so whenever AZURE_LOCATION is set
    the worker could neither read server references nor hand back keys the server
    could find.

    This roots the store at the container and prefixes `location` in `put()`, the same
    way `AwsS3Storage` handles AWS_LOCATION.
    """

    def __init__(self, location='', **kwargs):
        super().__init__(location='', **kwargs)
        self.location = location

    def put(self, reference, filename=None, subdir='', suffix=None, arcname=None):
        subdir = os.path.join(self.location, subdir) if self.location else subdir
        return super().put(reference, filename=filename, subdir=subdir, suffix=suffix, arcname=arcname)
