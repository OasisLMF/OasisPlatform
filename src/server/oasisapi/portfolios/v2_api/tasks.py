from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2
from django.contrib.auth import get_user_model
from ...files.models import RelatedFile
from rest_framework.exceptions import ValidationError
from ods_tools.oed import OdsException
from ...files.v2_api.views import _delete_related_file


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
    portfolio = Portfolio.objects.get(pk=portfolio_pk)
    if not validation_errors:
        portfolio.set_portfolio_valid()
    elif isinstance(validation_errors, str):
        portfolio.validation_status = portfolio.validation_status_choices.ERROR
        portfolio.save()
        # remove when Issue (https://github.com/OasisLMF/ODS_Tools/issues/174) fixed
        oed_class_of_businesses__workaround(OdsException(validation_errors))
        raise ValidationError({
            'error': 'Failed to validate portfolio',
            'detail': str(validation_errors),
            'exception': type(validation_errors).__name__
        })
    else:
        validation_errors = [ValidationError(msg) for msg in validation_errors]
        portfolio.validation_status = portfolio.validation_status_choices.ERROR
        portfolio.save()
        raise ValidationError(detail=[(error['name'], error['msg']) for error in validation_errors])


@celery_app_v2.task()
def record_transform_output(file, portfolio_pk, user_pk, file_type):
    from ..models import Portfolio
    portfolio = Portfolio.objects.get(pk=portfolio_pk)
    initiator = get_user_model().objects.get(pk=user_pk)
    selection = {
        'location': 'location_file',
        'accounts': 'accounts_file',
        'ri_info': 'reinsurance_info_file',
        'ri_scope': 'reinsurance_scope_file'
    }

    relatedfile = RelatedFile.objects.create(
        file=file, content_type='text/csv', creator=initiator,
        filename=f'portfolio_{portfolio_pk}_{selection[file_type]}.csv', store_as_filename=True
    )
    setattr(portfolio, selection[file_type], relatedfile)
    portfolio.exposure_transform_status = portfolio.exposure_transform_status_choices.RUN_COMPLETED

    _delete_related_file(portfolio, 'transform_file', initiator)
    _delete_related_file(portfolio, 'mapping_file', initiator)
    portfolio.save()
