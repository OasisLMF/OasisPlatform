import boto3
import logging
import os
import tempfile
import shutil

from urllib.parse import urlsplit, parse_qsl
from botocore.exceptions import ClientError as S3_ClientError

from ...common.shared import set_aws_log_level
from ..storage_manager import BaseStorageConnector


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
        self.aws_log_level = settings.get('worker', 'AWS_LOG_LEVEL', fallback='')
        self.gzip_content_types = settings.get('worker', 'GZIP_CONTENT_TYPES', fallback=(
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/x-javascript',
            'image/svg+xml',
        ))
        set_aws_log_level(self.aws_log_level)
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

    def _fetch_file(self, reference, output_path=""):
        """
        Download an S3 object to a file

        Parameters
        ----------
        :param file_path: Path to a file object for upload
        :type  file_path: str

        """
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fpath = output_path
        else:
            fpath = os.path.basename(reference)

        self.bucket.download_file(reference, fpath)
        logging.info('Get S3: {}'.format(reference))
        return os.path.abspath(fpath)

    def _store_file(self, file_path, storage_fname=None, storage_subdir='', suffix=None, **kwargs):
        """ Overloaded function for AWS file storage

        Uploads the Object pointed to by `file_path`
        with a unique filename

        Parameters
        ----------
        :param file_path: Path to a file object for upload
        :type file_path: str

        :param storage_fname: Set the name of stored file, instead of uuid
        :type  storage_fname: str

        :param suffix: Set the filename extension
        :type suffix: str

        :return: Download URL for uploaded object
                 Expires after (n) seconds set by
                 `AWS_QUERYSTRING_EXPIRE`
        :rtype str
        """
        ext = file_path.split('.')[-1] if not suffix else suffix
        filename = storage_fname if storage_fname else self._get_unique_filename(ext)
        object_name = os.path.join(storage_subdir, filename)

        if self.cache_root:
            os.makedirs(self.cache_root, exist_ok=True)
            cached_fp = os.path.join(self.cache_root, filename)
            shutil.copy(file_path, cached_fp)

        self.upload(object_name, file_path)
        self.logger.info('Stored S3: {} -> {}'.format(file_path, object_name))

        if self.shared_bucket:
            # Return Object Key
            return os.path.join(self.location, object_name)
        else:
            # Return URL
            return self.url(object_name)

    # def _store_dir(self, directory_path, suffix=None, arcname=None):
    def _store_dir(self, directory_path, storage_fname=None, storage_subdir='', suffix=None, arcname=None):
        """ Overloaded function for AWS Directory storage

        Creates a compressed .tar.gz of all files under `directory_path`
        Then uploads the tar to S3 with a unique filename

        Parameters
        ----------
        :param directory_path: Path to a directory for upload
        :type directory_path: str

        :param storage_fname: Set the name of stored file, instead of uuid
        :type  storage_fname: str

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
        filename = storage_fname if storage_fname else self._get_unique_filename(ext)
        object_name = os.path.join(storage_subdir, filename)
        object_args = {
            'ContentType': 'application/x-gzip',
            'ContentEncoding': 'gzip'
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = os.path.join(tmpdir, filename)
            self.compress(archive_path, directory_path, arcname)
            self.upload(object_name, archive_path, ExtraArgs=object_args)

            if self.cache_root:
                os.makedirs(self.cache_root, exist_ok=True)
                cached_fp = os.path.join(self.cache_root, filename)
                shutil.copy(archive_path, cached_fp)

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

    def delete_file(self, reference):
        """ Delete single Onject from S3 where
            reference = object key
        """

        del_request = {
            'Objects': [{'Key': os.path.join(self.location, reference)}],
            'Quiet': False
        }
        rsp = self.bucket.delete_objects(Delete=del_request)
        errors = rsp.get('Errors')
        deleted = rsp.get('Delete')

        if errors:
            self.logger.info(errors)
        if deleted and not errors:
            self.logger.info('Delete S3: {}'.format([obj['Key'] for obj in deleted]))

    def delete_dir(self, reference):
        """ Delete multiple Objects from S3 where
            'reference' is used to match keys of multiple stored Objects
        """

        key_prefix = os.path.join(self.location, reference)
        matching_obj = [{'Key': o.key} for o in self.bucket.objects.filter(Prefix=key_prefix)]
        del_request = {
            'Objects': matching_obj,
            'Quiet': False
        }
        rsp = self.bucket.delete_objects(Delete=del_request)
        self.logger.info(rsp)
        errors = rsp.get('Errors')
        deleted = rsp.get('Delete')

        if errors:
            self.logger.info(errors)
        if deleted and not errors:
            self.logger.info('Delete S3: {}'.format([obj['Key'] for obj in deleted]))

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
