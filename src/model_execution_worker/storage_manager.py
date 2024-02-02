import io
import logging
import os
import shutil
import tarfile
import uuid

from urllib.parse import urlparse
from urllib.request import urlopen

from oasislmf.utils.exceptions import OasisException

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'

#from .backends.aws_storage import AwsObjectStore
#from .backends.azure_storage import AzureObjectStore
#
#
#
#
#def StorageSelector(settings_conf):
#    """ Returns a `StorageConnector` class based on conf.ini
#
#    Call this method from model_execution_worker.task
#
#    :param settings_conf: Settings object for worker
#    :type settings_conf: src.conf.iniconf.Settings
#
#    :return: Storeage connector class
#    :rtype BaseStorageConnector
#    """
#    selected_storage = settings_conf.get('worker', 'STORAGE_TYPE', fallback="").lower()
#
#    if selected_storage in ['local-fs', 'shared-fs']:
#        return BaseStorageConnector(settings_conf)
#    elif selected_storage in ['aws-s3', 'aws', 's3']:
#        return AwsObjectStore(settings_conf)
#    elif selected_storage in ['azure']:
#        return AzureStore(settings_conf)
#    else:
#        raise OasisException('Invalid value for STORAGE_TYPE: {}'.format(selected_storage))


class MissingInputsException(OasisException):
    def __init__(self, input_filepath):
        super(MissingInputsException, self).__init__('Input file not found: {}'.format(input_filepath))


class BaseStorageConnector(object):
    """ Base storage class

    Implements storage for a local fileshare between
    `server` and `worker` containers
    """
    def __init__(self, setting, logger=None):
        self.media_root = setting.get('worker', 'MEDIA_ROOT')
        self.storage_connector = 'FS-SHARE'
        self.settings = setting
        self.logger = logger or logging.getLogger()

    def _get_unique_filename(self, suffix=""):
        """ Returns a unique name

        Parameters
        ----------
        :param suffix: Set the filename extension
        :type suffix: str

        :return: filename string
        :rtype str
        """
        return "{}.{}".format(uuid.uuid4().hex, suffix)

    def _is_stored(self, fname):
        """ Check if file is stored in media root
        Parameters

        Override this method depending on storage type
        ----------
        :param fname: filename to check
        :type fname: str

        :return: `True` if URL otherwise `False`
        :rtype boolean
        """
        if not isinstance(fname, str):
            return False
        return os.path.isfile(os.path.join(
            self.media_root,
            os.path.basename(fname)
        ))

    def _is_valid_url(self, url):
        """ Check if a String is a valid url

        Parameters
        ----------
        :param url: String to check
        :type url: str

        :return: `True` if URL otherwise `False`
        :rtype boolean
        """
        if url:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        else:
            return False

    def _store_file(self, file_path, suffix=None):
        """ Copy a file to `media_root`

        Places the file in `self.media_root` which is the shared storage location

        Parameters
        ----------
        :param file_path: The path to the file to store.
        :type  file_path: str

        :param suffix: Set the filename extension
        :type  suffix: str

        :return: The absolute stored file path
        :rtype str
        """
        ext = file_path.split('.')[-1] if not suffix else suffix
        stored_fp = os.path.join(
            self.media_root,
            self._get_unique_filename(ext))
        self.logger.info('Store file: {} -> {}'.format(file_path, stored_fp))
        return shutil.copyfile(file_path, stored_fp)

    def _store_dir(self, directory_path, suffix=None, arcname=None):
        """ Compress and store a directory

        Creates a compressed .tar.gz of all files under `directory_path`
        Then copies it to `self.media_root`

        Parameters
        ----------
        :param directory_path: Path to a directory for upload
        :type  directory_path: str

        :param suffix: Set the filename extension
                       defaults to `tar.gz`
        :type suffix: str

        :param arcname: If given, `arcname' set an alternative
                        name for the file in the archive.
        :type arcname: str

        :return: The absolute stored file path
        :rtype str
        """
        ext = 'tar.gz' if not suffix else suffix
        stored_fp = os.path.join(
            self.media_root,
            self._get_unique_filename(ext))
        self.compress(stored_fp, directory_path, arcname)
        self.logger.info('Store dir: {} -> {}'.format(directory_path, stored_fp))
        return stored_fp

    def _fetch_file(self, reference, output_dir):
        fpath = os.path.join(
            self.media_root,
            os.path.basename(reference)
        )
        logging.info('Get shared file: {}'.format(reference))
        return os.path.abspath(fpath)

    def extract(self, archive_fp, directory):
        """ Extract tar file

        Parameters
        ----------
        :param archive_fp: Path to archive file
        :type  archive_fp: str

        :param directory: Path to extract contents to.
        :type  directory: str
        """
        with tarfile.open(archive_fp) as f:
            f.extractall(directory)

    def compress(self, archive_fp, directory, arcname=None):
        """ Compress a directory

        Parameters
        ----------
        :param archive_fp: Path to archive file
        :type  archive_fp: str

        :param directory: Path to extract contents to.
        :type  directory: str

        :param arcname: If given, `arcname' set an alternative
                        name for the file in the archive.
        :type arcname: str
        """
        arcname = arcname if arcname else '/'
        with tarfile.open(archive_fp, 'w:gz') as tar:
            tar.add(directory, arcname=arcname)

    def get(self, reference, output_dir="", required=False):
        """ Retrieve stored object

        Top level 'get from storage' function
        Check if `reference` is either download `URL` or filename

        If URL: download the object and place in `output_dir`
        If Filename: return stored file path of the shared object

        Parameters
        ----------
        :param reference: Filename or download URL
        :type  reference: str

        :param output_dir: If given, download to that directory.
        :type  output_dir: str


        :return: Absolute filepath to stored Object
        :rtype str
        """
        if self._is_valid_url(reference):
            response = urlopen(reference)
            fdata = response.read()

            header_fname = response.headers.get('Content-Disposition', '').split('filename=')[-1]
            fname = header_fname if header_fname else os.path.basename(urlparse(reference).path)
            fpath = os.path.join(output_dir, fname)

            with io.open(fpath, 'w+b') as f:
                f.write(fdata)
                logging.info('Get from URL: {}'.format(fname))
            return os.path.abspath(fpath)

        elif self._is_stored(reference):
            return self._fetch_file(reference, output_dir)
        else:
            # Replace this with exeception?
            if required:
                raise MissingInputsException(reference)
            else:
                return None

    def put(self, reference, suffix=None, arcname=None):
        """ Place object in storage

        Top level send to storage function,
        Create new connector classes by Overriding
        `self._store_file( .. )` and `self._store_dir( .. )`

        Parameters
        ----------
        :param reference: Path to either a `File` or `Directory`
        :type  reference: str

        :param arcname: If given, `arcname' set an alternative
                        name for the file in the archive.
        :type arcname: str

        :param suffix: Set the filename extension defaults to `tar.gz`
        :type suffix: str

        :return: access storage reference returned from self._store_file, self._store_dir
                 This will either be a pre-signed URL or absolute filepath
        :rtype str
        """
        if not reference:
            return None
        if os.path.isfile(reference):
            return self._store_file(reference, suffix=suffix)
        elif os.path.isdir(reference):
            return self._store_dir(reference, suffix=suffix, arcname=arcname)
        else:
            return None

    def create_traceback(self, stdout, stderr, output_dir=""):
        traceback_file = self._get_unique_filename(LOG_FILE_SUFFIX)
        fpath = os.path.join(output_dir, traceback_file)
        with open(fpath, 'w') as f:
            if stdout:
                f.write(stdout)
            if stderr:
                f.write(stderr)
        return os.path.abspath(fpath)
