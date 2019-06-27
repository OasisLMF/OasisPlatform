from model_mommy import mommy

from ..models import ComplexModelDataFile


def fake_complex_model_file(**kwargs):
    """Create a fake ComplexModelDataFile for test purposes.

    Args:
        **kwargs: Keyword Arguments passed to ComplexModelDataFile

    Returns:
        ComplexModelDataFile: A faked ComplexModelDataFile

    """
    return mommy.make(ComplexModelDataFile, **kwargs)
