import os
from uuid import uuid4


def random_file_name(instance, filename):
    # Work around: S3 objects pushed as '<hash>.gz' should be '<hash>.tar.gz'
    if filename.endswith('.tar.gz'):
        ext = '.tar.gz'
    else:
        ext = os.path.splitext(filename)[-1]
    return '{}{}'.format(uuid4().hex, ext)
