from django_webtest import WebTest
from rest_framework.reverse import reverse
from unittest.mock import patch

from ...auth.tests.fakes import fake_user
from ..views import HealthcheckViewDeep


class Healthcheck(WebTest):

    @patch.object(HealthcheckViewDeep, 'celery_v1_is_ok', return_value=True)
    @patch.object(HealthcheckViewDeep, 'celery_v2_is_ok', return_value=True)
    def test_user_is_not_authenticated_deep___response_is_ok(self, mock_celery_v1, mock_celery_v2):
        response = self.app.get(reverse('healthcheck_deep'))
        self.assertEqual(200, response.status_code)

    @patch.object(HealthcheckViewDeep, 'celery_v1_is_ok', return_value=True)
    @patch.object(HealthcheckViewDeep, 'celery_v2_is_ok', return_value=True)
    def test_user_is_authenticated_deep___response_is_ok(self, mock_celery_v1, mock_celery_v2):
        response = self.app.get(reverse('healthcheck_deep'), user=fake_user())
        self.assertEqual(200, response.status_code)

    def test_user_is_not_authenticated_shallow___response_is_ok(self):
        response = self.app.get(reverse('healthcheck'))

        self.assertEqual(200, response.status_code)

    def test_user_is_authenticated_shallow___response_is_ok(self):
        response = self.app.get(reverse('healthcheck'), user=fake_user())

        self.assertEqual(200, response.status_code)
