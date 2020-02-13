
class StorageManager(object):
    """ Instantiate a storage connector based on workers config
    """
    def __init__(self, storage_conf):
        self.storage_conf = read_conf(storage_conf)

        if storage_type == '<S3 enum>':
            return AwsObjectStore( ... )
        #elif storage_type == '<azure enum>':
        #    return AzureObjectStore( ... )
        else:
            return FileSystemShare( ... )


class StorageConnector(object)
    """ Base interface class to implement a storage service
    """
    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def _extract(self):
        pass

    def _compress(self):
        pass

    def connect(self, *args, **kwargs):
        raise NotImplementedError

    def fetch(self, reference, dest=None):
        raise NotImplementedError

    def store_dir(self, dir_reference):
        raise NotImplementedError

    def store_file(self, file_reference):
        raise NotImplementedError


class FileSystemShare(StorageConnector):
    def __init__(self, fileshare_dir):
        pass

class AwsObjectStore(BaseConnector):
    def __init__(self, conf_location):
        pass


