import os
import io
import tarfile
import tempfile
import uuid
import shutil
import boto3

from urllib.parse import urlparse
from urllib.request import urlopen

from os import path
from oasislmf.utils.exceptions import OasisException

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'


def StorageSelector(settings_conf):
    """ Instantiate a storage connector based on workers config
    """
    selected_storage = settings_conf.get('worker', 'STORAGE_TYPE', fallback="")

    if selected_storage.lower() in ['aws-s3', 'aws', 's3']:
        return AwsObjectStore(settings_conf)
    #elif storage_type == '<azure enum>':
    #    return AzureObjectStore( ... )

    else:
        return BaseStorageConnector(settings_conf)

class MissingInputsException(OasisException):
    def __init__(self, input_filepath):
        super(MissingInputsException, self).__init__('Input file not found: {}'.format(input_filepath))

class BaseStorageConnector(object):
    """ Base class to implement a storage service

    """
    def __init__(self, setting):
        self.media_root = setting.get('worker', 'MEDIA_ROOT')
        self.storage_connector = 'FS-SHARE'
        self.settings = setting

    def _get_unique_filename(self, suffix=""):
       return "{}.{}".format(uuid.uuid4().hex, suffix)

    def _is_valid_url(self, url):
        if url:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        else:
            return False

    def _store_file(self, file_path, suffix=None):
        ext = file_path.split('.')[-1] if not suffix else suffix
        stored_fp = os.path.join(
            self.media_root,
            self._get_unique_filename(ext))
        return shutil.copy(file_path, stored_fp)

    def _store_dir(self, directory_path, suffix=None, arcname=None):
            ext = 'tar.gz' if not suffix else suffix
            stored_fp = os.path.join(
                self.media_root,
                self._get_unique_filename(ext))
            self.compress(stored_fp, directory_path, arcname)
            return stored_fp

    def extract(self, archive_fp, directory):
        with tarfile.open(archive_fp) as f:
            f.extractall(directory)

    def compress(self, archive_fp, directory, arcname=None):
        arcname = arcname if arcname else '/'
        with tarfile.open(archive_fp, 'w:gz') as tar:
            tar.add(directory, arcname=arcname)

    def get(self, reference, output_dir=""):
        """
            Top level 'get from storage' function

            Case m: 'reference' is a URL to a remote file, download
                    to `dest` location if set or CWD if None

            Case n: 'reference' is a valid path to a shared volumne file
                    copy to 'dest' if set to a valid filepath

                    return sf-share + filename
        """
        if self._is_valid_url(reference):
            response = urlopen(reference)
            fdata = response.read()

            header_fname = response.headers.get('Content-Disposition', '').split('filename=')[-1]
            fname = header_fname if header_fname else os.path.basename(urlparse(reference).path)
            fpath = os.path.join(output_dir, fname)

            with io.open(fpath, 'w+b') as f:
                f.write(fdata)
            return os.path.abspath(fpath)

        elif isinstance(reference, str):
            fpath = os.path.join(
                self.media_root,
                os.path.basename(reference)
            )
            if os.path.isfile(fpath):
                #logging.info('Fetch FILE: {}'.format(reference))
                return os.path.abspath(fpath)
            else:
                raise MissingInputsException(fpath)

        else:
            return None

    def put(self, reference, suffix=None, arcname=None):
        """ Top level send to storage function
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
        # https://github.com/jschneier/django-storages/blob/master/storages/backends/s3boto3.py
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#id244

        self.storage_connector = 'AWS-S3'
        self._bucket = None
        self._connection = None
        self.access_key = settings.get('worker', 'AWS_ACCESS_KEY_ID')
        self.secret_key = settings.get('worker', 'AWS_SECRET_ACCESS_KEY')

        self.file_overwrite = settings.get('worker', 'AWS_S3_FILE_OVERWRITE', fallback=True)
        self.object_parameters = settings.get('worker', 'AWS_S3_OBJECT_PARAMETERS', fallback={})
        self.bucket_name = settings.get('worker', 'AWS_BUCKET_NAME')
        self.auto_create_bucket = settings.get('worker', 'AWS_AUTO_CREATE_BUCKET', fallback=False)
        self.default_acl = settings.get('worker', 'AWS_DEFAULT_ACL', fallback=None)
        self.bucket_acl = settings.get('worker', 'AWS_BUCKET_ACL', fallback=self.default_acl)
        self.querystring_auth = settings.get('worker', 'AWS_QUERYSTRING_AUTH', fallback=True)
        self.querystring_expire = settings.get('worker', 'AWS_QUERYSTRING_EXPIRE', fallback=3600)
        #self.signature_version = settings.get('worker', 'AWS_S3_SIGNATURE_VERSION')
        self.reduced_redundancy = settings.get('worker', 'AWS_REDUCED_REDUNDANCY', fallback=False)
        self.location = settings.get('worker', 'AWS_LOCATION', fallback='')
        self.encryption = settings.get('worker', 'AWS_S3_ENCRYPTION', fallback=False)
        self.security_token = settings.get('worker', 'AWS_SECURITY_TOKEN', fallback=None)
        #self.custom_domain = settings.get('worker', 'AWS_S3_CUSTOM_DOMAIN')
        #self.addressing_style = settings.get('worker', 'AWS_S3_ADDRESSING_STYLE')
        self.secure_urls = settings.get('worker', 'AWS_S3_SECURE_URLS', fallback=True)
        self.file_name_charset = settings.get('worker', 'AWS_S3_FILE_NAME_CHARSET', fallback='utf-8')
        self.gzip = settings.get('worker', 'AWS_IS_GZIPPED', fallback=False)
        self.preload_metadata = settings.get('worker', 'AWS_PRELOAD_METADATA', fallback=False)
        self.gzip_content_types = settings.get('worker', 'GZIP_CONTENT_TYPES', fallback=(
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/x-javascript',
            'image/svg+xml',
        ))
        self.url_protocol = settings.get('worker', 'AWS_S3_URL_PROTOCOL', fallback='http:')
        #self.endpoint_url = settings.get('worker', 'AWS_S3_ENDPOINT_URL')
        #self.proxies = settings.get('worker', 'AWS_S3_PROXIES')
        self.region_name = settings.get('worker', 'AWS_S3_REGION_NAME', fallback=None)
        self.use_ssl = settings.get('worker', 'AWS_S3_USE_SSL', fallback=True)
        self.verify = settings.get('worker', 'AWS_S3_VERIFY', fallback=None)
        self.max_memory_size = settings.get('worker', 'AWS_S3_MAX_MEMORY_SIZE', fallback=0)

        super(AwsObjectStore, self).__init__(settings)

    @property
    def connection(self):
        """
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
                #endpoint_url=self.endpoint_url,
                #config=self.config,
                verify=self.verify,
            )
        return self._connection

    @property
    def bucket(self):
        """
        Get the current bucket. If there is no current bucket object
        create it.
        """
        if self._bucket is None:
            self._bucket = self.connection.Bucket(self.bucket_name)
        return self._bucket


    """ TODO - Might be too dangrous to set policy based on conf file
    def _get_bucket_policy(self):
        pass
    def _set_lifecycle(self, ):
        pass
        # https://stackoverflow.com/questions/14969273/s3-object-expiration-using-boto
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-bucket-policies.html
    """

    def _store_file(self, file_path, suffix=None):
        """ Overloaded function for AWS filestorage
        """
        ext = file_path.split('.')[-1] if not suffix else suffix
        object_name = self._get_unique_filename(ext)

        self.upload(object_name, file_path)
        return self.url(object_name)

    def _store_dir(self, directory_path, suffix=None, arcname=None):
        """ Overloaded function for AWS filestorage
        """
        ext = 'tar.gz' if not suffix else suffix
        object_name = self._get_unique_filename(ext)
        with tempfile.TemporaryDirectory() as tmpdir: 
            archive_path = os.path.join(tmpdir, object_name)
            self.compress(archive_path, directory_path, arcname)
            self.upload(object_name, archive_path)

        return self.url(object_name)

    def url(self, object_name, parameters=None, expire=None):
        """
        """
        params = parameters.copy() if parameters else {}
        params['Bucket'] = self.bucket.name
        if self.location:
            params['Key'] = os.path.join(self.location, object_name)
        else:
            params['Key'] = object_name

        if expire is None:
            expire = self.querystring_expire

        return self.bucket.meta.client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=expire)

    def upload(self, object_name, filepath, ExtraArgs=None):
        """
        """
        object_key = os.path.join(self.location, object_name)
        params = ExtraArgs.copy() if ExtraArgs else {}
        if self.encryption:
            params['ServerSideEncryption'] = 'AES256'
        if self.reduced_redundancy:
            params['StorageClass'] = 'REDUCED_REDUNDANCY'
        if self.default_acl:
            params['ACL'] = self.default_acl

        #logging.info('Store S3: {} -> {}'.format(filepath, object_key))
        self.bucket.upload_file(filepath, object_key, ExtraArgs=params)
