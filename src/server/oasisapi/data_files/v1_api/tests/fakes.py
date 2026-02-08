from model_bakery import baker

from src.server.oasisapi.data_files.models import DataFile


def fake_data_file(**kwargs):
    """Create a fake DataFile for test purposes.

    Args:
        **kwargs: Keyword Arguments passed to DataFile

    Returns:
        ComplexModelDataFile: A faked DataFile

    """
    return baker.make(DataFile, **kwargs)
