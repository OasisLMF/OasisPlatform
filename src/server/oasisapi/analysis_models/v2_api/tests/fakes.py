from model_bakery import baker

from src.server.oasisapi.analysis_models.models import AnalysisModel


def fake_analysis_model(**kwargs):
    return baker.make(AnalysisModel, **kwargs)
