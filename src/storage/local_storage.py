import uuid

from pathlib2 import Path


class LocalStorage(object):
    def __init__(self, root):
        self.root = root

    def get_random_filename(self):
        return uuid.uuid4().hex

    def save(self, content, filename=None, mode='wb'):
        filename = filename or self.get_random_filename()

        with open(str(Path(self.root, filename)), mode) as f:
            f.write(content)

        return filename

    def read(self, filename, mode='rb'):
        with open(str(Path(self.root, filename)), mode) as f:
            return f.read()
