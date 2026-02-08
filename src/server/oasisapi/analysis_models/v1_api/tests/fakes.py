from model_bakery import baker

from ...models import AnalysisModel


def fake_analysis_model(**kwargs):
    return baker.make(AnalysisModel, **kwargs)
