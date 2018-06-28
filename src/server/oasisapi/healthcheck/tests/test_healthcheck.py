from django_webtest import WebTest
from rest_framework.reverse import reverse

from ...auth.tests.fakes import fake_user


class Healthcheck(WebTest):
    def test_user_is_not_authenticated___response_is_ok(self):
        response = self.app.get(reverse('healthcheck'))

        self.assertEqual(200, response.status_code)

    def test_user_is_authenticated___response_is_ok(self):
        response = self.app.get(reverse('healthcheck'), user=fake_user())

        self.assertEqual(200, response.status_code)
