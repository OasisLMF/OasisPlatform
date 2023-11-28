from model_mommy import mommy

from ..models import DataFile


def fake_data_file(**kwargs):
    """Create a fake DataFile for test purposes.

    Args:
        **kwargs: Keyword Arguments passed to DataFile

    Returns:
        ComplexModelDataFile: A faked DataFile

    """
    return mommy.make(DataFile, **kwargs)
