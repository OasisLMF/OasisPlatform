from model_mommy import mommy

from ..models import Analysis


def fake_analysis(**kwargs):
    return mommy.make(Analysis, **kwargs)
