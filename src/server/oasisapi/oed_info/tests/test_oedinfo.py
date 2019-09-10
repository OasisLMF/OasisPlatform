from django_webtest import WebTest
from rest_framework.reverse import reverse

from ...auth.tests.fakes import fake_user


class Perilcodes(WebTest):
    def test_user_is_not_authenticated___response_is_ok(self):
        response = self.app.get(reverse('perilcodes'))
        oed_codes_json = response.json

        self.assertEqual(200, response.status_code)
        self.assertTrue('peril_codes' in oed_codes_json)
        self.assertTrue('peril_groups' in oed_codes_json)
        self.assertTrue('oasislmf_version' in oed_codes_json)
        self.assertTrue('oasislmf_version' in oed_codes_json)
        self.assertTrue(isinstance(oed_codes_json['oasislmf_version'], str))
        self.assertFalse(oed_codes_json['peril_codes'] is {})
        self.assertFalse(oed_codes_json['peril_groups'] is {})

    def test_user_is_authenticated___response_is_ok(self):
        response = self.app.get(reverse('perilcodes'), user=fake_user())
        oed_codes_json = response.json

        self.assertEqual(200, response.status_code)
        self.assertTrue('peril_codes' in oed_codes_json)
        self.assertTrue('peril_groups' in oed_codes_json)
        self.assertTrue('oasislmf_version' in oed_codes_json)
        self.assertTrue('oasislmf_version' in oed_codes_json)
        self.assertTrue(isinstance(oed_codes_json['oasislmf_version'], str))
        self.assertFalse(oed_codes_json['peril_codes'] is {})
        self.assertFalse(oed_codes_json['peril_groups'] is {})
