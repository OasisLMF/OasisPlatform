from django_webtest import WebTest
from rest_framework.reverse import reverse
from rest_framework_simplejwt.tokens import AccessToken

from ...auth.tests.fakes import fake_user


class Perilcodes(WebTest):
    def test_user_is_not_authenticated___response_is_ok(self):
        response = self.app.get(reverse('perilcodes'))
        oed_codes_json = response.json

        self.assertEqual(200, response.status_code)
        self.assertTrue('peril_codes' in oed_codes_json)
        self.assertTrue('peril_groups' in oed_codes_json)
        self.assertFalse(oed_codes_json['peril_codes'] is {})
        self.assertFalse(oed_codes_json['peril_groups'] is {})

    def test_user_is_authenticated___response_is_ok(self):
        response = self.app.get(reverse('perilcodes'), user=fake_user())
        oed_codes_json = response.json

        self.assertEqual(200, response.status_code)
        self.assertTrue('peril_codes' in oed_codes_json)
        self.assertTrue('peril_groups' in oed_codes_json)
        self.assertFalse(oed_codes_json['peril_codes'] is {})
        self.assertFalse(oed_codes_json['peril_groups'] is {})


class ServerInfo(WebTest):
    def test_user_is_not_authenticated___response_is_Forbidden(self):
        response = self.app.get(
            reverse('serverinfo'),
            expect_errors=True,
        )
        server_info_json = response.json
        self.assertEqual(403, response.status_code)

    def test_user_is_authenticated___response_is_ok(self):
        user = fake_user()
        response = self.app.get(
            reverse('serverinfo'), 
            user=user,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )
        server_info_json = response.json

        self.assertEqual(200, response.status_code)
        self.assertTrue('version' in server_info_json)
        self.assertTrue('config' in server_info_json)
        self.assertFalse(server_info_json['version'] is str)
        self.assertFalse(server_info_json['config'] is {})
