from model_mommy import mommy

from src.server.oasisapi.analysis_models.models import AnalysisModel


def fake_analysis_model(**kwargs):
    return mommy.make(AnalysisModel, **kwargs)
