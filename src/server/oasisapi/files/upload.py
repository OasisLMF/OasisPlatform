import os
from uuid import uuid4


def random_file_name(instance, filename):
    ext = os.path.splitext(filename)[-1]
    return '{}{}'.format(uuid4().hex, ext)
