from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2
from django.contrib.auth import get_user_model
from ...files.models import RelatedFile
from rest_framework.exceptions import ValidationError


@celery_app_v2.task()
def record_exposure_output(result, portfolio_pk, user_pk):
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


@celery_app_v2.task()
def record_validation_output(validation_errors, portfolio_pk):
    from ..models import oed_class_of_businesses__workaround, Portfolio
    if not validation_errors:
        instance = Portfolio.objects.get(pk=portfolio_pk)
        instance.set_port_valid()
    elif isinstance(validation_errors, Exception):
        oed_class_of_businesses__workaround(validation_errors)  # remove when Issue (https://github.com/OasisLMF/ODS_Tools/issues/174) fixed
        raise ValidationError({
            'error': 'Failed to validate portfolio',
            'detail': str(validation_errors),
            'exception': type(validation_errors).__name__
        })
    else:
        raise ValidationError(detail=[(error['name'], error['msg']) for error in validation_errors])
