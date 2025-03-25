from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2
from django.contrib.auth import get_user_model
from ...files.models import RelatedFile


@celery_app_v2.task()
def record_output(result, portfolio_pk, user_pk):
    from ..models import Portfolio
    file, success = result
    portfolio = Portfolio.objects.get(id=portfolio_pk)
    initiator = get_user_model().objects.get(pk=user_pk)

    portfolio.exposure_run_file = RelatedFile.objects.create(
        file=file, content_type='text/csv', creator=initiator,
        filename=f'portfolio_{portfolio_pk}_exposure_run.csv', store_as_filename=True
    )
    if success:
        portfolio.exposure_status = portfolio.exposure_status_choices.RUN_COMPLETED
    else:
        portfolio.exposure_status = portfolio.exposure_status_choices.ERROR
    portfolio.save()
