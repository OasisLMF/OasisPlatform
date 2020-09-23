import boto3
import io
import logging
import os
import shutil
import tarfile
import tempfile
import uuid

from urllib.parse import urlparse, urlsplit, parse_qsl
from urllib.request import urlopen

from oasislmf.utils.exceptions import OasisException

from botocore.exceptions import ClientError as S3_ClientError

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'


def StorageSelector(settings_conf):
    """ Returns a `StorageConnector` class based on conf.ini

    Call this method from model_execution_worker.task

    :param settings_conf: Settings object for worker
    :type settings_conf: src.conf.iniconf.Settings

    :return: Storeage connector class
    :rtype BaseStorageConnector
    """
    selected_storage = settings_conf.get('worker', 'STORAGE_TYPE', fallback="").lower()

    if selected_storage in ['local-fs', 'shared-fs']:
        return BaseStorageConnector(settings_conf)
    elif selected_storage in ['aws-s3', 'aws', 's3']:
        return AwsObjectStore(settings_conf)
    else:
        raise OasisException('Invalid value for STORAGE_TYPE: {}'.format(selected_storage))


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
        return shutil.copy(file_path, stored_fp)

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


    def create_traceback(self, subprocess_run, output_dir=""):
        traceback_file = self._get_unique_filename(LOG_FILE_SUFFIX)
        fpath = os.path.join(output_dir, traceback_file)
        with open(fpath, 'w') as f:
            if subprocess_run.stdout:
                f.write(subprocess_run.stdout.decode())
            if subprocess_run.stderr:
                f.write(subprocess_run.stderr.decode())
        return os.path.abspath(fpath)


class AwsObjectStore(BaseStorageConnector):
    def __init__(self, settings):
        """ Storage Connector for Amazon S3

        Store objects in a bucket common to a single worker pool. Returns a pre-signed URL
        as a response to the server which is downloaded and stored by Django-storage module

        Documentation
        -------------
        https://github.com/jschneier/django-storages/blob/master/storages/backends/s3boto3.py
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#id244

        TODO
        ----

        * Add optional local caching
        * option to set object expiry policy on bucket

            def _get_bucket_policy(self):
                pass
            def _set_lifecycle(self, ):
                pass
                https://stackoverflow.com/questions/14969273/s3-object-expiration-using-boto
                https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-bucket-policies.html

        Parameters
        ----------
        :param settings_conf: Settings object for worker
        :type settings_conf: src.conf.iniconf.Settings
        """
        # Required
        self.storage_connector = 'AWS-S3'
        self._bucket = None
        self._connection = None
        self.access_key = settings.get('worker', 'AWS_ACCESS_KEY_ID', fallback=None)
        self.secret_key = settings.get('worker', 'AWS_SECRET_ACCESS_KEY', fallback=None)

        # Optional
        self.endpoint_url = settings.get('worker', 'AWS_S3_ENDPOINT_URL', fallback=None)
        self.file_overwrite = settings.getboolean('worker', 'AWS_S3_FILE_OVERWRITE', fallback=True)
        self.object_parameters = settings.get('worker', 'AWS_S3_OBJECT_PARAMETERS', fallback={})
        self.bucket_name = settings.get('worker', 'AWS_BUCKET_NAME')
        self.auto_create_bucket = settings.getboolean('worker', 'AWS_AUTO_CREATE_BUCKET', fallback=False)
        self.default_acl = settings.get('worker', 'AWS_DEFAULT_ACL', fallback=None)
        self.bucket_acl = settings.get('worker', 'AWS_BUCKET_ACL', fallback=self.default_acl)
        self.querystring_auth = settings.getboolean('worker', 'AWS_QUERYSTRING_AUTH', fallback=False)
        self.querystring_expire = settings.get('worker', 'AWS_QUERYSTRING_EXPIRE', fallback=604800)
        self.reduced_redundancy = settings.getboolean('worker', 'AWS_REDUCED_REDUNDANCY', fallback=False)
        self.location = settings.get('worker', 'AWS_LOCATION', fallback='')
        self.encryption = settings.getboolean('worker', 'AWS_S3_ENCRYPTION', fallback=False)
        self.security_token = settings.get('worker', 'AWS_SECURITY_TOKEN', fallback=None)
        self.secure_urls = settings.getboolean('worker', 'AWS_S3_SECURE_URLS', fallback=True)
        self.file_name_charset = settings.get('worker', 'AWS_S3_FILE_NAME_CHARSET', fallback='utf-8')
        self.gzip = settings.getboolean('worker', 'AWS_IS_GZIPPED', fallback=False)
        self.preload_metadata = settings.getboolean('worker', 'AWS_PRELOAD_METADATA', fallback=False)
        self.url_protocol = settings.get('worker', 'AWS_S3_URL_PROTOCOL', fallback='http:')
        self.region_name = settings.get('worker', 'AWS_S3_REGION_NAME', fallback=None)
        self.use_ssl = settings.getboolean('worker', 'AWS_S3_USE_SSL', fallback=True)
        self.verify = settings.get('worker', 'AWS_S3_VERIFY', fallback=None)
        self.max_memory_size = settings.get('worker', 'AWS_S3_MAX_MEMORY_SIZE', fallback=0)
        self.shared_bucket = settings.getboolean('worker', 'AWS_SHARED_BUCKET', fallback=False)
        self.gzip_content_types = settings.get('worker', 'GZIP_CONTENT_TYPES', fallback=(
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/x-javascript',
            'image/svg+xml',
        ))
        super(AwsObjectStore, self).__init__(settings)


    @property
    def connection(self):
        """ Creates an S3 boto3 session

        based on conf.ini or environment variables based on
        a subset of variables used in Django-Storage AWS S3
        """
        if self._connection is None:
            session = boto3.session.Session()
            self._connection = session.resource(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                aws_session_token=self.security_token,
                region_name=self.region_name,
                use_ssl=self.use_ssl,
                verify=self.verify,
                endpoint_url=self.endpoint_url,
            )
        return self._connection

    @property
    def bucket(self):
        """ Get the current bucket.

        If there is no current bucket object
        create it.
        """
        if self._bucket is None:
            self._bucket = self.connection.Bucket(self.bucket_name)
        return self._bucket

    def _is_stored(self, object_key):
        if not isinstance(object_key, str):
            return False
        try:
            self.bucket.Object(object_key).load()
            return True
        except S3_ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else:
                # Not a 404 re-raise the execption
                logging.info(e.response)
                raise e

    def _fetch_file(self, reference, output_dir=""):
        """
        Download an S3 object to a file

        Parameters
        ----------
        :param file_path: Path to a file object for upload
        :type  file_path: str

        """
        fpath = os.path.join(
            output_dir,
            os.path.basename(reference)
        )
        self.bucket.download_file(reference, fpath)
        logging.info('Get S3: {}'.format(reference))
        return os.path.abspath(fpath)

    def _store_file(self, file_path, suffix=None):
        """ Overloaded function for AWS file storage

        Uploads the Object pointed to by `file_path`
        with a unique filename

        Parameters
        ----------
        :param file_path: Path to a file object for upload
        :type file_path: str

        :param suffix: Set the filename extension
        :type suffix: str

        :return: Download URL for uploaded object
                 Expires after (n) seconds set by
                 `AWS_QUERYSTRING_EXPIRE`
        :rtype str
        """
        ext = file_path.split('.')[-1] if not suffix else suffix
        object_name = self._get_unique_filename(ext)

        self.upload(object_name, file_path)
        self.logger.info('Stored S3: {} -> {}'.format(file_path, object_name))

        if self.shared_bucket:
            # Return Object Key
            return os.path.join(self.location, object_name)
        else:
            # Return URL
            return self.url(object_name)

    def _store_dir(self, directory_path, suffix=None, arcname=None):
        """ Overloaded function for AWS Directory storage

        Creates a compressed .tar.gz of all files under `directory_path`
        Then uploads the tar to S3 with a unique filename

        Parameters
        ----------
        :param directory_path: Path to a directory for upload
        :type directory_path: str

        :param suffix: Set the filename extension
                       defaults to `tar.gz`
        :type suffix: str

        :param arcname: If given, `arcname' set an alternative
                        name for the file in the archive.
        :type arcname: str


        :return: Download URL for uploaded object
                 Expires after (n) seconds set by
                 `AWS_QUERYSTRING_EXPIRE`
        """
        ext = 'tar.gz' if not suffix else suffix
        object_name = self._get_unique_filename(ext)
        object_args = {
            'ContentType': 'application/x-gzip', 
            'ContentEncoding': 'gzip'
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = os.path.join(tmpdir, object_name)
            self.compress(archive_path, directory_path, arcname)
            self.upload(object_name, archive_path, ExtraArgs=object_args)
            #self.upload(object_name, archive_path)

        self.logger.info('Stored S3: {} -> {}'.format(directory_path, object_name))
        if self.shared_bucket:
            # Return Object Key
            return os.path.join(self.location, object_name)
        else:
            # Return URL
            return self.url(object_name)

    def _strip_signing_parameters(self, url):
        """ Duplicated Unsiged URLs from Django-Stroage

        Method from: https://github.com/jschneier/django-storages/blob/master/storages/backends/s3boto3.py

        Boto3 does not currently support generating URLs that are unsigned. Instead we
        take the signed URLs and strip any querystring params related to signing and expiration.
        Note that this may end up with URLs that are still invalid, especially if params are
        passed in that only work with signed URLs, e.g. response header params.
        The code attempts to strip all query parameters that match names of known parameters
        from v2 and v4 signatures, regardless of the actual signature version used.
        """
        split_url = urlsplit(url)
        qs = parse_qsl(split_url.query, keep_blank_values=True)
        blacklist = {
            'x-amz-algorithm', 'x-amz-credential', 'x-amz-date',
            'x-amz-expires', 'x-amz-signedheaders', 'x-amz-signature',
            'x-amz-security-token', 'awsaccesskeyid', 'expires', 'signature',
        }
        filtered_qs = ((key, val) for key, val in qs if key.lower() not in blacklist)
        # Note: Parameters that did not have a value in the original query string will have
        # an '=' sign appended to it, e.g ?foo&bar becomes ?foo=&bar=
        joined_qs = ('='.join(keyval) for keyval in filtered_qs)
        split_url = split_url._replace(query="&".join(joined_qs))
        return split_url.geturl()


    def url(self, object_name, parameters=None, expire=None):
        """ Return Pre-signed URL

        Download URL to `object_name` in the connected bucket with a
        fixed expire time

        Documentation
        -------------
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html


        Parameters
        ----------
        :param object_name: 'key' or name of object in bucket
        :type  object_name: str

        :param parameters: Dictionary of parameters to send to the method (BOTO3)
        :type  parameters: dict

        :param expire: Time in seconds for the presigned URL to remain valid
        :type  expire: int

        :return: Presigned URL as string. If error, returns None.
        :rtype str
        """
        params = parameters.copy() if parameters else {}
        params['Bucket'] = self.bucket.name
        if self.location:
            params['Key'] = os.path.join(self.location, object_name)
        else:
            params['Key'] = object_name

        if expire is None:
            expire = self.querystring_expire

        url = self.bucket.meta.client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=expire)

        if self.querystring_auth:
            return url
        else:
            return self._strip_signing_parameters(url)

    def upload(self, object_name, filepath, ExtraArgs=None):
        """ Wrapper for BOTO3 bucket upload

        Documentation
        -------------
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_file


        Parameters
        ----------
        :param object_name: 'key' or object name to upload as
        :type  object_name: str

        :param filepath: The path to the file to upload.
        :type  filepath: str

        :param ExtraArgs: Extra arguments that may be passed to the client operation.
        :type  ExtraArgs: dict

        :return: None
        """
        object_key = os.path.join(self.location, object_name)
        params = ExtraArgs.copy() if ExtraArgs else {}
        if self.encryption:
            params['ServerSideEncryption'] = 'AES256'
        if self.reduced_redundancy:
            params['StorageClass'] = 'REDUCED_REDUNDANCY'
        if self.default_acl:
            params['ACL'] = self.default_acl

        self.bucket.upload_file(filepath, object_key, ExtraArgs=params)
