from model_bakery import baker

from src.server.oasisapi.portfolios.models import Portfolio


def fake_portfolio(**kwargs):
    return baker.make(Portfolio, **kwargs)
