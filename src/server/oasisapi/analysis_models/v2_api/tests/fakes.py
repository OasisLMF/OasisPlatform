from model_mommy import mommy

from ..models import AnalysisModel


def fake_analysis_model(**kwargs):
    return mommy.make(AnalysisModel, **kwargs)
