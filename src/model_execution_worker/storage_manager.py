import io
import logging
import os
import shutil
import tarfile
import tempfile
import uuid

from pathlib2 import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from oasislmf.utils.exceptions import OasisException

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'


class MissingInputsException(OasisException):
    def __init__(self, input_filepath):
        super(MissingInputsException, self).__init__('Input file not found: {}'.format(input_filepath))


class BaseStorageConnector(object):
    """ Base storage class

    Implements storage for a local fileshare between
    `server` and `worker` containers
    """

    def __init__(self, setting, logger=None):

        # Use for caching files across multiple runs, set value 'None' or 'False' to disable
        self.cache_root = setting.get('worker', 'CACHE_DIR', fallback='/tmp/data-cache')
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

    def _is_locally_stored(self, fname):
        """ Check if file is stored in media root
        Parameters
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
            fname
        ))

    def _is_stored(self, fname):
        return self._is_locally_stored(fname)

    def _is_valid_url(self, url):
        """ Check if a String is a valid url

        Parameters
        ----------
        :param url: String to check
        :type  url: str

        :return: `True` if URL otherwise `False`
        :rtype boolean
        """
        if url:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        else:
            return False

    def _store_file(self, file_path, storage_fname=None, storage_subdir='', suffix=None, **kwargs):
        """ Copy a file to `media_root`

        Places the file in `self.media_root` which is the shared storage location

        Parameters
        ----------
        :param file_path: The path to the file to store.
        :type  file_path: str

        :param storage_fname: Set the name of stored file, instead of uuid
        :type  storage_fname: str

        :param storage_subdir: Store object in given sub directory
        :type  storage_subdir: str

        :param suffix: Set the filename extension
        :type  suffix: str

        :return: The reference to the file in storage
        :rtype str
        """
        ext = file_path.split('.')[-1] if not suffix else suffix
        storage_dir = os.path.join(self.media_root, storage_subdir)
        store_reference = storage_fname if storage_fname else self._get_unique_filename(ext)

        os.makedirs(storage_dir, exist_ok=True)
        stored_fp = os.path.join(storage_dir, store_reference)

        self.logger.info('Store file: {} -> {}'.format(file_path, stored_fp))
        shutil.copyfile(file_path, stored_fp)
        return os.path.join(storage_subdir, store_reference)

    def _store_dir(self, directory_path, storage_fname=None, storage_subdir='', suffix=None, arcname=None, **kwargs):
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

        :param storage_fname: Set the name of stored file, instead of uuid
        :type  storage_fname: str

        :param storage_subdir: Store object in given sub directory
        :type  storage_subdir: str

        :param arcname: If given, `arcname' set an alternative
                        name for the file in the archive.
        :type arcname: str

        :return: The reference to the file in storage
        :rtype str
        """
        ext = 'tar.gz' if not suffix else suffix
        storage_dir = os.path.join(self.media_root, storage_subdir)
        store_reference = storage_fname if storage_fname else self._get_unique_filename(ext)
        os.makedirs(storage_dir, exist_ok=True)

        stored_fp = os.path.join(storage_dir, store_reference)
        self.compress(stored_fp, directory_path, arcname)
        self.logger.info('Store dir: {} -> {}'.format(directory_path, stored_fp))
        return os.path.join(storage_subdir, store_reference)

    def _fetch_file(self, reference, output_path, subdir):
        fpath = os.path.join(
            self.media_root,
            subdir,
            os.path.basename(reference)
        )
        if os.path.isfile(fpath):
            logging.info('Get shared file: {}'.format(fpath))
            if os.path.isdir(output_path):
                shutil.copyfile(
                    fpath,
                    os.path.join(output_path, os.path.basename(fpath))
                )
            else:
                shutil.copyfile(fpath, output_path)
            return os.path.abspath(fpath)

        else:
            raise MissingInputsException(fpath)

    def filepath(self, reference):
        """ return the absolute filepath 
        """
        fpath = os.path.join(
            self.media_root,
            os.path.basename(reference)
        )
        logging.info('Get shared filepath: {}'.format(reference))
        return os.path.abspath(fpath)

    def extract(self, archive_fp, directory, storage_subdir=''):
        """ Extract tar file

        Parameters
        ----------
        :param archive_fp: Path to archive file
        :type  archive_fp: str

        :param directory: Path to extract contents to.
        :type  directory: str

        :param storage_subdir: Store object in given sub directory
        :type  storage_subdir: str
        """
        temp_dir = tempfile.TemporaryDirectory()
        try:
            temp_dir_path = temp_dir.__enter__()
            local_archive_path = self.get(
                archive_fp,
                os.path.join(temp_dir_path, os.path.basename(archive_fp)),
                subdir=storage_subdir
            )
            with tarfile.open(local_archive_path) as f:
                f.extractall(directory)
        finally:
            temp_dir.cleanup()

    def compress(self, archive_fp, directory, arcname=None):
        """ Compress a directory

        Parameters
        ----------
        :param archive_fp: Path to archive file
        :type  archive_fp: str

        :param directory: Path to archive.
        :type  directory: str

        :param arcname: If given, `arcname' set an alternative
                        name for the file in the archive.
        :type arcname: str
        """
        arcname = arcname if arcname else '/'
        with tarfile.open(archive_fp, 'w:gz') as tar:
            tar.add(directory, arcname=arcname)

    def get(self, reference, output_path="", subdir='', required=False):
        """ Retrieve stored object

        Top level 'get from storage' function
        Check if `reference` is either download `URL` or filename

        If URL: download the object and place in `output_dir`
        If Filename: return stored file path of the shared object

        Parameters
        ----------
        :param reference: Filename or download URL
        :type  reference: str

        :param output_path: If given, download to that directory.
        :type  output_path: str

        :param subdir: Store a file under this sub directory path
        :type  subdir: str

        :return: Absolute filepath to stored Object
        :rtype str
        """
        # null ref given
        if not reference:
            if required:
                raise MissingInputsException(reference)
            else:
                return None

        # Download if URL ref
        if self._is_valid_url(reference):
            response = urlopen(reference)
            fdata = response.read()
            header_fname = response.headers.get('Content-Disposition', '').split('filename=')[-1]
            fname = header_fname if header_fname else os.path.basename(urlparse(reference).path)

            if os.path.isdir(output_path):
                fpath = os.path.join(output_path, fname)
            else:
                fpath = output_path

            # Check and copy file if cached
            if self.cache_root:
                cached_file = os.path.join(self.cache_root, fname)
                if os.path.isfile(cached_file):
                    logging.info('Get from Cache: {}'.format(fname))
                    shutil.copyfile(cached_file, fpath)
                    return os.path.abspath(fpath)

            # Download if not cached
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with io.open(fpath, 'w+b') as f:
                f.write(fdata)
                logging.info('Get from URL: {}'.format(fname))

            # Store in cache if enabled
            if self.cache_root:
                os.makedirs(self.cache_root, exist_ok=True)
                shutil.copyfile(fpath, cached_file)
            return os.path.abspath(fpath)

        # return local file
        if self._is_locally_stored(reference):
            return self._fetch_file(reference, output_path, subdir)

        # current
        if self._is_stored(reference):
            if os.path.isdir(output_path):
                fpath = os.path.join(output_path, os.path.basename(reference))
            else:
                fpath = output_path
            return self._fetch_file(reference, fpath)

    def put(self, reference, filename=None, subdir='', suffix=None, arcname=None):
        """ Place object in storage

        Top level send to storage function,
        Create new connector classes by Overriding
        `self._store_file( .. )` and `self._store_dir( .. )`

        Parameters
        ----------
        :param reference: Path to either a `File` or `Directory`
        :type  reference: str

        :param filename: Set the name of stored file, instead of uuid
        :type  filename: str

        :param subdir: Store a file under this sub directory path
        :type  subdir: str

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
            return self._store_file(
                reference,
                storage_fname=filename,
                storage_subdir=subdir,
                suffix=suffix,
                arcname=arcname
            )
        elif os.path.isdir(reference):
            return self._store_dir(
                reference,
                storage_fname=filename,
                storage_subdir=subdir,
                suffix=suffix,
                arcname=arcname
            )
        else:
            return None

    def delete_file(self, reference):
        """
        Delete single file from shared storage

        :param reference: Path to `File`
        :type  reference: str
        """

        ref_path = os.path.join(self.media_root, os.path.basename(reference))
        if os.path.isfile(ref_path):
            os.remove(ref_path)
            logging.info('Deleted Shared file: {}'.format(ref_path))
        else:
            logging.info('Delete Error - Unknwon reference {}'.format(reference))

    def delete_dir(self, reference):
        """
        Delete subdirectory from shared storage

        :param reference: Path to `Directory`
        :type  reference: str
        """
        ref_path = os.path.join(self.media_root, os.path.basename(reference))
        if os.path.isdir(ref_path):
            root = Path(self.media_root)
            subdir = Path(ref_path)
            if root == subdir:
                logging.info('Delete Error - prevented media root deletion')
            else:
                shutil.rmtree(ref_path, ignore_errors=True)
                logging.info('Deleted shared dir: {}'.format(ref_path))
        else:
            logging.info('Delete Error - Unknwon reference {}'.format(reference))

    def create_traceback(self, stdout, stderr, output_dir=""):
        traceback_file = self._get_unique_filename(LOG_FILE_SUFFIX)
        fpath = os.path.join(output_dir, traceback_file)
        with open(fpath, 'w') as f:
            if stdout:
                f.write(stdout)
            if stderr:
                f.write(stderr)
        return os.path.abspath(fpath)
