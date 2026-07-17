import io
import pytest
from django.contrib.auth import get_user_model
from django.core.files import File

from src.server.oasisapi.external_providers.models import ExternalJob, ExternalProviderSettings
from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.portfolios.models import Portfolio

User = get_user_model()

SAMPLE_CSV = b'PortNumber,AccNumber,LocNumber,CountryCode,Latitude,Longitude,OccupancyCode\n1,ACC1,LOC1,GH,5.6,0.2,\n1,ACC1,LOC2,GH,5.7,0.3,\n'
SAMPLE_ENRICHED_CSV = b'PortNumber,AccNumber,LocNumber,CountryCode,Latitude,Longitude,OccupancyCode\n1,ACC1,LOC1,GH,5.6,0.2,1100\n1,ACC1,LOC2,GH,5.7,0.3,1100\n'


@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='testpass')


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username='admin', password='adminpass', email='admin@example.com')


@pytest.fixture
def portfolio(db, user):
    return Portfolio.objects.create(name='Test Portfolio', creator=user)


@pytest.fixture
def location_file(db, user):
    return RelatedFile.objects.create(
        file=File(io.BytesIO(SAMPLE_CSV), name='locations.csv'),
        filename='locations.csv',
        content_type='text/csv',
        creator=user,
    )


@pytest.fixture
def portfolio_with_file(portfolio, location_file):
    portfolio.location_file = location_file
    portfolio.save()
    return portfolio


@pytest.fixture
def provider_settings(db):
    return ExternalProviderSettings.objects.create(
        provider='gxm',
        base_url='http://localhost:18000',
        client_id='test-client',
        client_secret='test-secret',
    )


@pytest.fixture
def pending_location_job(db, portfolio, user, provider_settings):
    return ExternalJob.objects.create(
        provider='gxm',
        job_type=ExternalJob.JobType.LOCATION_FILE,
        portfolio=portfolio,
        initiator=user,
        request_data={'country_code': 'GH', 'format': 'csv'},
    )


@pytest.fixture
def pending_enrich_job(db, portfolio_with_file, user, provider_settings):
    return ExternalJob.objects.create(
        provider='gxm',
        job_type=ExternalJob.JobType.ENRICH,
        portfolio=portfolio_with_file,
        initiator=user,
        request_data={'fields': ['OccupancyCode'], 'format': 'csv', 'overwrite': False},
    )
