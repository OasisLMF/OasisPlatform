from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
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

    if success:
        portfolio.exposure_status = portfolio.exposure_status_choices.RUN_COMPLETED
        portfolio.exposure_run_file = RelatedFile.objects.create(
            file=file, content_type='text/csv', creator=initiator,
            filename=f'portfolio_{portfolio_pk}_exposure_run.csv', store_as_filename=True
        )
    else:
        portfolio.exposure_status = portfolio.exposure_status_choices.ERROR
        portfolio.run_errors_file = RelatedFile.objects.create(
            file=file, content_type='text/csv', creator=initiator,
            filename=f'portfolio_{portfolio_pk}_errors.txt', store_as_filename=True
        )

    portfolio.save()


@celery_app_v2.task()
def record_validation_output(validation_errors, portfolio_pk, user_pk):
    from ..models import oed_class_of_businesses__workaround, Portfolio
    portfolio = Portfolio.objects.get(pk=portfolio_pk)
    initiator = get_user_model().objects.get(pk=user_pk)
    if not validation_errors:
        portfolio.set_portfolio_valid()
        return

    file = ContentFile(content=str(validation_errors), name=f'portfolio_{portfolio_pk}_errors.txt')
    portfolio.validation_status = portfolio.validation_status_choices.ERROR
    portfolio.run_errors_file = RelatedFile.objects.create(
        file=file, content_type='text/csv', creator=initiator,
        filename=file.name, store_as_filename=True
    )
    portfolio.save()
    oed_class_of_businesses__workaround(OdsException(str(validation_errors)))
    raise ValidationError()


@celery_app_v2.task()
def record_transform_output(result, portfolio_pk, user_pk, file_type):
    from ..models import Portfolio
    file, success = result
    portfolio = Portfolio.objects.get(pk=portfolio_pk)
    initiator = get_user_model().objects.get(pk=user_pk)
    selection = {
        'location': 'location_file',
        'accounts': 'accounts_file',
        'ri_info': 'reinsurance_info_file',
        'ri_scope': 'reinsurance_scope_file'
    }
    _delete_related_file(portfolio, 'transform_file', initiator)
    _delete_related_file(portfolio, 'mapping_file', initiator)

    if success:
        relatedfile = RelatedFile.objects.create(
            file=file, content_type='text/csv', creator=initiator,
            filename=f'portfolio_{portfolio_pk}_{selection[file_type]}.csv', store_as_filename=True
        )
        setattr(portfolio, selection[file_type], relatedfile)
        portfolio.exposure_transform_status = portfolio.exposure_transform_status_choices.RUN_COMPLETED
        portfolio.save()
    else:
        file = ContentFile(content=str(file), name=f'portfolio_{portfolio_pk}_errors.txt')
        portfolio.run_errors_file = RelatedFile.objects.create(
            file=file, content_type='text/csv', creator=initiator,
            filename=file.name, store_as_filename=True
        )
        portfolio.exposure_transform_status = portfolio.exposure_transform_status_choices.ERROR
        portfolio.validation_status = portfolio.validation_status_choices.ERROR
        portfolio.save()
        raise Exception("Transformation failed!")
