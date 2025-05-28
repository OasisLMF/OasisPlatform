from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2
from django.contrib.auth import get_user_model
from ...files.models import RelatedFile
from rest_framework.exceptions import ValidationError


@celery_app_v2.task()
def record_exposure_output(result, portfolio_pk, user_pk):
    from ..models import Portfolio  # Circular otherwise
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
        instance.set_portolio_valid()
    elif isinstance(validation_errors, Exception):
        oed_class_of_businesses__workaround(validation_errors)  # remove when Issue (https://github.com/OasisLMF/ODS_Tools/issues/174) fixed
        raise ValidationError({
            'error': validation_errors[0],
            'detail': validation_errors[1],
            'exception': validation_errors[2]
        })
    else:
        raise ValidationError(detail=[(error['name'], error['msg']) for error in validation_errors])


@celery_app_v2.task()
def record_exposure_transformation(result, portfolio_pk, user_pk):
    from ..models import Portfolio
    portfolio = Portfolio.objects.get(pk=portfolio_pk)
    initiator = get_user_model().objects.get(pk=user_pk)
    files = ['location', 'account', 'ri_info', 'ri_scope']
    for i, file_name in enumerate(files):
        if result[i] is not None:
            related_file = RelatedFile.objects.create(
                file=result[i],
                content_type='text/csv',
                creator=initiator,
                filename=f"{file_name}.csv",
                store_as_filename=True
            )
            setattr(portfolio, f"{file_name}_file", related_file)
    portfolio.save()
