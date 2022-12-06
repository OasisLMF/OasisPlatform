import os
from uuid import uuid4


def random_file_name(instance, filename):
    # Work around: S3 objects pushed as '<hash>.gz' should be '<hash>.tar.gz'
    if filename.endswith('.tar.gz'):
        ext = '.tar.gz'
    else:
        ext = os.path.splitext(filename)[-1]
    return '{}{}'.format(uuid4().hex, ext)


def wait_for_blob_copy(blob):
    # https://github.com/Azure/azure-sdk-for-python/issues/7043
    # Missing Async wait method for blob copy, added func here
    count = 0
    props = blob.get_blob_properties()
    while props.copy.status == 'pending':
        count = count + 1
        if count > 15:
            raise TimeoutError('Timed out waiting for async copy to complete.')
        time.sleep(5)
        props = blob.get_blob_properties()
    return props
