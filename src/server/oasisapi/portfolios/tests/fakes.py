from model_mommy import mommy

from ..models import Portfolio


def fake_portfolio(**kwargs):
    return mommy.make(Portfolio, **kwargs)
