from model_mommy import mommy

from src.server.oasisapi.portfolios.models import Portfolio


def fake_portfolio(**kwargs):
    return mommy.make(Portfolio, **kwargs)
