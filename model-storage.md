The model storage is configured in the same way as the existing worker storage but exists
in a separate section of the config file (namely worker.model_storage).

For example to specify loading model data from an S3 bucket add the following to your
conf.ini file::

    [worker.model_storage]
    STORAGE_TYPE=S3
    AWS_BUCKET_NAME=example-bucket
    AWS_ACCESS_KEY_ID=<worker-key-id>
    AWS_SECRET_ACCESS_KEY=<worker-access-key>
    AWS_QUERYSTRING_EXPIRE=180
    AWS_QUERYSTRING_AUTH=True

Similarly, these values can be overridden by setting environment variables using the prefix
`OASIS_WORKER_MODEL_STORAGE_`.

If model storage is setup, it is assumed that the model data will be stored in a subdirectory
specific to that model. This directory takes the following pattern `/<supplier_id>/<model_id>/<version>`. 
For the OasisLMF PiWind v3 model for example, the path will be `/OasisLMF/PiWind/3`.
