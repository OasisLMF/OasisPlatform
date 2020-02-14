import re
import os
import wget
import tarfile
import uuid
import shutil

from os import path
from oasislmf.utils.exceptions import OasisException

LOG_FILE_SUFFIX = '.txt'
ARCHIVE_FILE_SUFFIX = '.tar'


#class StorageManager(object):
#    """ Instantiate a storage connector based on workers config
#    """
#    def __init__(self, settings_conf):
#        self.storage_conf = read_conf(storage_conf)
#
#        if storage_type == '<S3 enum>':
#            return AwsObjectStore( ... )
#        #elif storage_type == '<azure enum>':
#        #    return AzureObjectStore( ... )
#        else:
#            return BaseStorageConnector( ... )

class MissingInputsException(OasisException):
    def __init__(self, input_filepath):
        super(MissingInputsException, self).__init__('Input file not found: {}'.format(input_filepath))

class BaseStorageConnector(object):
    """ Base class to implement a storage service

    """
    def __init__(self, worker_conf):
        self.settings = worker_conf
        self.media_root = self.settings.get('worker', 'MEDIA_ROOT')

    def _get_unique_filename(self, suffix=""):
       return "{}.{}".format(uuid.uuid4().hex, suffix)

    def _is_valid_url(self, url):
       # Replace this later?
        regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(regex, url) is not None

    def extract(self, archive_fp, directory):
        with tarfile.open(archive_fp) as f:
            f.extractall(directory)

    def compress(self, archive_fp, directory, arcname='/'):
        with tarfile.open(archive_fp, 'w:gz') as tar:
            tar.add(directory, arcname=arcname)

    def get(self, reference, download_dir=None):
        """
            Top level 'get from storage' function

            Case m: 'reference' is a URL to a remote file, download
                    to `dest` location if set or CWD if None

            Case n: 'reference' is a valid path to a shared volumne file
                    copy to 'dest' if set to a valid filepath

                    return sf-share + filename
        """
        if self._is_valid_url(reference):
            return wget.download(
                url=reference, 
                out=os.path.abspath(download_dir)
        elif isinstance(reference, str):
            filepath = os.path.join(
                self.media_root,
                os.path.basename(reference)
            )
            if os.path.isfile(filepath):
                return filepath
            else:
                raise MissingInputsException(filepath)

        else:
            return None

    def put(self, reference, suffix="", arcname=None):
        """ Top level send to storage function
        """
        ext = os.path.splitext(reference)[-1] if not suffix else suffix
        stored_fp = os.path.join(
            self.media_root,
            self._get_unique_filename(ext)
        )

        if os.path.isfile(reference):
            stored_fp = os.path.join(
                self.media_root,
                self._get_unique_filename(ext)
            )
            return shutil.copy(reference, stored_fp)

        elif os.path.isdir(reference):
            stored_fp = os.path.join(
                self.media_root,
                self._get_unique_filename('tar.gz')
            )
            self.compress(stored_fp, reference, arcname)
            return stored_fp

        else:
            return None

    def create_traceback(self, subprocess_run):
        traceback_location = self._get_unique_filename(LOG_FILE_SUFFIX)
        with open(traceback_location, 'w') as f:
            if subprocess_run.stdout:
                f.write(subprocess_run.stdout.decode())
            if subprocess_run.stderr:
                f.write(subprocess_run.stderr.decode())
        return os.path.abspath(traceback_location)

class AwsObjectStore(BaseStorageConnector):
    def __init__(self, conf_location):
        pass

    def connect(self, *args, **kwargs):
        raise NotImplementedError
