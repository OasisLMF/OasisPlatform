import json
import string

from backports.tempfile import TemporaryDirectory
from django.contrib.auth.models import Group
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTestMixin
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, binary, sampled_from
from mock import patch
from rest_framework_simplejwt.tokens import AccessToken

from ...files.tests.fakes import fake_related_file
from ...analysis_models.tests.fakes import fake_analysis_model
from ...portfolios.tests.fakes import fake_portfolio
from ...auth.tests.fakes import fake_user, add_fake_group
from ...data_files.tests.fakes import fake_data_file
from ..models import Analysis
from .fakes import fake_analysis

# Override default deadline for all tests to 8s
settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")


class AnalysisApi(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            reverse('analysis-detail', kwargs={'version': 'v1', 'pk': analysis.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_name_is_not_provided___response_is_400(self):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params={},
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)

    @given(name=text(alphabet=' \t\n\r', max_size=10))
    def test_cleaned_name_is_empty___response_is_400(self, name):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name}),
            content_type='application/json'
        )

        self.assertEqual(400, response.status_code)

    @given(name=text(alphabet=string.ascii_letters, max_size=10, min_size=1))
    def test_cleaned_name_portfolio_and_model_are_present___object_is_created(self, name):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                self.maxDiff = None
                user = fake_user()
                model = fake_analysis_model()
                portfolio = fake_portfolio(location_file=fake_related_file())

                response = self.app.post(
                    reverse('analysis-list', kwargs={'version': 'v1'}),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': model.pk}),
                    content_type='application/json'
                )
                self.assertEqual(201, response.status_code)

                analysis = Analysis.objects.get(pk=response.json['id'])
                analysis.settings_file = fake_related_file()
                analysis.input_file = fake_related_file()
                analysis.lookup_errors_file = fake_related_file()
                analysis.lookup_success_file = fake_related_file()
                analysis.lookup_validation_file = fake_related_file()
                analysis.summary_levels_file = fake_related_file()
                analysis.input_generation_traceback_file = fake_related_file()
                analysis.output_file = fake_related_file()
                analysis.run_traceback_file = fake_related_file()
                analysis.run_log_file = fake_related_file()
                analysis.save()

                response = self.app.get(
                    analysis.get_absolute_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(200, response.status_code)
                self.assertEqual({
                    'complex_model_data_files': [],
                    'created': analysis.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'modified': analysis.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'id': analysis.pk,
                    'name': name,
                    'portfolio': portfolio.pk,
                    'model': model.pk,
                    'settings_file': response.request.application_url + analysis.get_absolute_settings_file_url(),
                    'settings': response.request.application_url + analysis.get_absolute_settings_url(),
                    'input_file': response.request.application_url + analysis.get_absolute_input_file_url(),
                    'lookup_errors_file': response.request.application_url + analysis.get_absolute_lookup_errors_file_url(),
                    'lookup_success_file': response.request.application_url + analysis.get_absolute_lookup_success_file_url(),
                    'lookup_validation_file': response.request.application_url + analysis.get_absolute_lookup_validation_file_url(),
                    'input_generation_traceback_file': response.request.application_url + analysis.get_absolute_input_generation_traceback_file_url(),
                    'output_file': response.request.application_url + analysis.get_absolute_output_file_url(),
                    'run_log_file': response.request.application_url + analysis.get_absolute_run_log_file_url(),
                    'run_traceback_file': response.request.application_url + analysis.get_absolute_run_traceback_file_url(),
                    'status': Analysis.status_choices.NEW,
                    'status_count': {'CANCELLED': 0,
                                     'COMPLETED': 0,
                                     'ERROR': 0,
                                     'PENDING': 0,
                                     'QUEUED': 0,
                                     'STARTED': 0,
                                     'TOTAL': 0,
                                     'TOTAL_IN_QUEUE': 0},
                    'storage_links': 'http://testserver/v1/analyses/1/storage_links/',
                    'sub_task_count': 0,
                    'sub_task_error_ids': [],
                    'sub_task_list': 'http://testserver/v1/analyses/1/sub_task_list/',
                    'summary_levels_file': response.request.application_url + analysis.get_absolute_summary_levels_file_url(),
                    'task_started': None,
                    'task_finished': None,
                    'groups': [],
                    'analysis_chunks': None,
                    'lookup_chunks': None,
                    'priority': 4,
                }, response.json)

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_complex_model_file_present___object_is_created(self, name):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                self.maxDiff = None
                user = fake_user()
                model = fake_analysis_model()
                portfolio = fake_portfolio(location_file=fake_related_file())

                response = self.app.post(
                    reverse('analysis-list', kwargs={'version': 'v1'}),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': model.pk}),
                    content_type='application/json'
                )
                self.assertEqual(201, response.status_code)

                analysis = Analysis.objects.get(pk=response.json['id'])
                cmf_1 = fake_data_file()
                cmf_2 = fake_data_file()
                analysis.complex_model_data_files.set([cmf_1, cmf_2])
                analysis.save()

                response = self.app.get(
                    analysis.get_absolute_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(200, response.status_code)
                self.assertEqual({
                    'complex_model_data_files': [cmf_1.pk, cmf_2.pk],
                    'created': analysis.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'modified': analysis.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'id': analysis.pk,
                    'name': name,
                    'portfolio': portfolio.pk,
                    'model': model.pk,
                    'settings_file': None,
                    'settings': None,
                    'input_file': None,
                    'lookup_errors_file': None,
                    'lookup_success_file': None,
                    'lookup_validation_file': None,
                    'input_generation_traceback_file': None,
                    'output_file': None,
                    'run_log_file': None,
                    'run_traceback_file': None,
                    'status': 'NEW',
                    'status_count': {'CANCELLED': 0,
                                     'COMPLETED': 0,
                                     'ERROR': 0,
                                     'PENDING': 0,
                                     'QUEUED': 0,
                                     'STARTED': 0,
                                     'TOTAL': 0,
                                     'TOTAL_IN_QUEUE': 0},
                    'storage_links': 'http://testserver/v1/analyses/1/storage_links/',
                    'sub_task_count': 0,
                    'sub_task_error_ids': [],
                    'sub_task_list': 'http://testserver/v1/analyses/1/sub_task_list/',
                    'storage_links': response.request.application_url + analysis.get_absolute_storage_url(),
                    'summary_levels_file': None,
                    'groups': [],
                    'task_started': None,
                    'task_finished': None,
                    'analysis_chunks': None,
                    'lookup_chunks': None,
                    'priority': 4,
                }, response.json)

    def test_model_does_not_exist___response_is_400(self):
        user = fake_user()
        analysis = fake_analysis()
        model = fake_analysis_model()

        response = self.app.patch(
            analysis.get_absolute_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'model': model.pk + 1}),
            content_type='application/json',
            expect_errors=True,
        )

        self.assertEqual(400, response.status_code)

    def test_model_does_exist___response_is_200(self):
        user = fake_user()
        analysis = fake_analysis()
        model = fake_analysis_model()

        response = self.app.patch(
            analysis.get_absolute_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'model': model.pk}),
            content_type='application/json',
            expect_errors=True,
        )

        analysis.refresh_from_db()

        self.assertEqual(200, response.status_code)
        self.assertEqual(analysis.model, model)

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
        group_name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_portfolio_group_inheritance___same_groups_as_portfolio(self, name, group_name):

        user = fake_user()
        group = add_fake_group(user, group_name)
        model = fake_analysis_model()
        portfolio = fake_portfolio(location_file=fake_related_file())

        # Deny due to not in the same group as model
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': model.pk}),
            content_type='application/json',
            expect_errors=True,
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual('You are not allowed to use this model', json.loads(response.body).get('model')[0])

        model.groups.add(group)
        model.save()

        # Deny due to not in the same group as portfolio
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': model.pk}),
            content_type='application/json',
            expect_errors=True,
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual('You are not allowed to use this portfolio', json.loads(response.body).get('portfolio')[0])

        portfolio.groups.add(group)
        portfolio.save()

        # Successfully create
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': model.pk}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)

        analysis = Analysis.objects.get(pk=response.json['id'])

        response = self.app.get(
            analysis.get_absolute_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual([group_name], json.loads(response.body).get('groups'))

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
        group_name1=text(alphabet=string.ascii_letters, max_size=2, min_size=1),
        group_name2=text(alphabet=string.ascii_letters, max_size=4, min_size=3),
        group_name3=text(alphabet=string.ascii_letters, max_size=6, min_size=5),
    )
    def test_multiple_analyses_with_different_groups___user_should_not_see_each_others(self, name, group_name1, group_name2, group_name3):

        group1, _ = Group.objects.get_or_create(name=group_name1)
        group2, _ = Group.objects.get_or_create(name=group_name2)
        group3, _ = Group.objects.get_or_create(name=group_name3)

        user1 = fake_user()
        user2 = fake_user()

        group1.user_set.add(user1)
        group1.user_set.add(user2)
        group1.save()

        group2.user_set.add(user1)
        group2.save()

        group3.user_set.add(user2)
        group3.save()

        model = fake_analysis_model()
        model.groups.add(group1)
        model.groups.add(group2)
        model.groups.add(group3)
        model.save()

        portfolio1 = fake_portfolio(location_file=fake_related_file())
        portfolio1.groups.add(group2)
        portfolio1.save()

        portfolio2 = fake_portfolio(location_file=fake_related_file())
        portfolio2.groups.add(group3)
        portfolio2.save()

        # Create an analysis with portfolio1 - group2
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user1))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio1.pk, 'model': model.pk}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)
        analysis1_id = response.json['id']

        # Create an analysis with portfolio2 - group3
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user2))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio2.pk, 'model': model.pk}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)
        analysis2_id = response.json['id']

        # User1 should only se analysis 1 with groups2
        response = self.app.get(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user1))
            },
        )
        self.assertEqual(200, response.status_code)
        analysis = json.loads(response.body)[0]
        self.assertEqual(analysis1_id, analysis.get('id'))
        self.assertEqual([group_name2], analysis.get('groups'))

        # User2 should only se analysis2 with groups3
        response = self.app.get(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user2))
            },
        )
        self.assertEqual(200, response.status_code)
        analyses = json.loads(response.body)
        self.assertEqual(1, len(analyses))
        analysis = analyses[0]
        self.assertEqual(analysis2_id, analysis.get('id'))
        self.assertEqual([group_name3], analysis.get('groups'))

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
        group_name1=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_multiple_analyses_with_different_groups___user_without_group_should_not_see_them(self, name, group_name1):

        group1, _ = Group.objects.get_or_create(name=group_name1)

        user1 = fake_user()
        group1.user_set.add(user1)
        group1.save()

        user2 = fake_user()

        model = fake_analysis_model()
        model.groups.add(group1)
        model.save()

        portfolio1 = fake_portfolio(location_file=fake_related_file())
        portfolio1.groups.add(group1)
        portfolio1.save()

        # Create an analysis
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user1))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio1.pk, 'model': model.pk}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)

        # User2 should not see any analysis
        response = self.app.get(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user2))
            },
        )
        self.assertEqual(200, response.status_code)
        analyses = json.loads(response.body)
        self.assertEqual(0, len(analyses))

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
        group_name1=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_user_with_and_without_group_can_access_portfolio_without_group(self, name, group_name1):

        group1, _ = Group.objects.get_or_create(name=group_name1)

        user_with_group1 = fake_user()
        group1.user_set.add(user_with_group1)
        group1.save()

        user_without_group = fake_user()

        model = fake_analysis_model()
        model.save()

        portfolio1 = fake_portfolio(location_file=fake_related_file())
        portfolio1.save()

        # Create an analysis
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_without_group))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio1.pk, 'model': model.pk}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)

        # user_with_group1 should see the analysis
        response = self.app.get(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_with_group1))
            },
        )
        self.assertEqual(200, response.status_code)
        analyses = json.loads(response.body)
        self.assertEqual(1, len(analyses))

        # user_without_group should see the analysis
        response = self.app.get(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_without_group))
            },
        )
        self.assertEqual(200, response.status_code)
        analyses = json.loads(response.body)
        self.assertEqual(1, len(analyses))

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
        group_name1=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_modify_analysis_without_group___successfully(self, name, group_name1):

        group1, _ = Group.objects.get_or_create(name=group_name1)

        user_with_group1 = fake_user()
        group1.user_set.add(user_with_group1)
        group1.save()

        user_without_group = fake_user()

        model = fake_analysis_model()
        model.save()

        portfolio1 = fake_portfolio(location_file=fake_related_file())
        portfolio1.save()

        # Create an analysis
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_without_group))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio1.pk, 'model': model.pk}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)

        # user_with_group1 should see the analysis
        response = self.app.get(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_with_group1))
            },
        )
        self.assertEqual(200, response.status_code)
        analyses = json.loads(response.body)
        self.assertEqual(1, len(analyses))
        analysis_id = analyses[0].get('id')

        # user_with_group1 should be allowed to write
        response = self.app.post(
            reverse('analysis-settings', kwargs={'version': 'v1', 'pk': analysis_id}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_with_group1))
            },
            params={},
            expect_errors=True,
        )
        self.assertEqual(400, response.status_code)

        # user_without_group should see the analysis
        response = self.app.get(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_without_group))
            },
        )
        self.assertEqual(200, response.status_code)
        analyses = json.loads(response.body)
        self.assertEqual(1, len(analyses))

        # user_without_group should be allowed to write
        response = self.app.post(
            reverse('analysis-settings', kwargs={'version': 'v1', 'pk': analysis_id}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_without_group))
            },
            params={},
            expect_errors=True,
        )
        self.assertEqual(400, response.status_code)

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_create_no_priority___successfully_set_default(self, name):

        portfolio = fake_portfolio(location_file=fake_related_file())

        # Create an analysis
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(fake_user()))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': fake_analysis_model().pk}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)
        analysis = json.loads(response.body)
        self.assertEqual(4, analysis.get('priority'))

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_create_as_admin_low_priority___successfully(self, name):

        user = fake_user()
        user.is_staff = True
        user.save()
        portfolio = fake_portfolio(location_file=fake_related_file())

        # Create an analysis
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': fake_analysis_model().pk, 'priority': 1}),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)

    @given(
        name=text(alphabet=string.ascii_letters, max_size=10, min_size=1),
    )
    def test_create_as_no_admin_low_priority___rejected(self, name):

        model = fake_analysis_model()
        portfolio = fake_portfolio(location_file=fake_related_file())

        # Create an analysis
        response = self.app.post(
            reverse('analysis-list', kwargs={'version': 'v1'}),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(fake_user()))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': model.pk, 'priority': 9}),
            content_type='application/json',
            expect_errors=True
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual('Levels restricted to administrators: [8, 9, 10]', json.loads(response.body).get('priority')[0])


class AnalysisRun(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_run_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-run', kwargs={'version': 'v1', 'pk': analysis.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_user_is_authenticated_object_exists___run_is_called(self):
        with patch('src.server.oasisapi.analyses.models.Analysis.run', autospec=True) as run_mock:
            user = fake_user()
            analysis = fake_analysis()

            self.app.post(
                analysis.get_absolute_run_url(),
                headers={
                    'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                }
            )

            run_mock.assert_called_once_with(analysis, user)

    def test_user_is_not_in_same_model_group___run_is_denied(self):
        user = fake_user()
        analysis = fake_analysis()
        group, _ = Group.objects.get_or_create(name='group_name')
        analysis.model.groups.add(group)
        analysis.model.save()

        response = self.app.post(
            analysis.get_absolute_run_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual('You are not allowed to run this model', response.json.get('detail'))


class AnalysisCancel(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_cancel_analysis_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-cancel', kwargs={'version': 'v1', 'pk': analysis.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_user_is_authenticated_object_exists___cancel_is_called(self):
        with patch('src.server.oasisapi.analyses.models.Analysis.cancel_analysis', autospec=True) as cancel_mock:
            user = fake_user()
            analysis = fake_analysis()

            self.app.post(
                analysis.get_absolute_cancel_analysis_url(),
                headers={
                    'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                }
            )

            cancel_mock.assert_called_once_with(analysis)

    def test_user_is_not_in_same_model_group___cancel_is_denied(self):
        user = fake_user()
        analysis = fake_analysis()
        group, _ = Group.objects.get_or_create(name='group_name')
        analysis.model.groups.add(group)
        analysis.model.save()

        response = self.app.post(
            analysis.get_absolute_cancel_analysis_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual('You are not allowed to cancel this model', response.json.get('detail'))


class AnalysisGenerateInputs(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_generate_inputs_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-generate-inputs', kwargs={'version': 'v1', 'pk': analysis.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_user_is_authenticated_object_exists___generate_inputs_is_called(self):
        with patch('src.server.oasisapi.analyses.models.Analysis.generate_inputs', autospec=True) as generate_inputs_mock:
            user = fake_user()
            analysis = fake_analysis()

            self.app.post(
                analysis.get_absolute_generate_inputs_url(),
                headers={
                    'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                }
            )

            generate_inputs_mock.assert_called_once_with(analysis, user)

    def test_user_is_not_in_same_model_group___run_is_denied(self):
        user = fake_user()
        analysis = fake_analysis()
        group, _ = Group.objects.get_or_create(name='group_name')
        analysis.model.groups.add(group)
        analysis.model.save()

        response = self.app.post(
            analysis.get_absolute_generate_inputs_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual('You are not allowed to run this model', response.json.get('detail'))


class AnalysisCancelInputsGeneration(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_cancel_inputs_generation_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-cancel-generate-inputs', kwargs={'version': 'v1', 'pk': analysis.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_user_is_authenticated_object_exists___generate_inputs_generation_is_called(self):
        with patch('src.server.oasisapi.analyses.models.Analysis.cancel_generate_inputs', autospec=True) as cancel_generate_inputs:
            user = fake_user()
            analysis = fake_analysis()

            self.app.post(
                analysis.get_absolute_cancel_inputs_generation_url(),
                headers={
                    'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                }
            )

            cancel_generate_inputs.assert_called_once_with(analysis)

    def test_user_is_not_in_same_model_group___cancel_is_denied(self):
        user = fake_user()
        analysis = fake_analysis()
        group, _ = Group.objects.get_or_create(name='group_name')
        analysis.model.groups.add(group)
        analysis.model.save()

        response = self.app.post(
            analysis.get_absolute_cancel_inputs_generation_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual('You are not allowed to cancel this model', response.json.get('detail'))


class AnalysisCopy(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_copy_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-copy', kwargs={'version': 'v1', 'pk': analysis.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_new_object_is_created(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertNotEqual(analysis.pk, response.json['id'])

    @given(name=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_no_new_name_is_provided___copy_is_appended_to_name(self, name):
        user = fake_user()
        analysis = fake_analysis(name=name)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).name, '{} - Copy'.format(name))

    @given(orig_name=text(min_size=1, max_size=10, alphabet=string.ascii_letters), new_name=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_new_name_is_provided___new_name_is_set_on_new_object(self, orig_name, new_name):
        user = fake_user()
        analysis = fake_analysis(name=orig_name)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': new_name}),
            content_type='application/json'
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).name, new_name)

    @given(status=sampled_from(list(Analysis.status_choices._db_values)))
    def test_state_is_reset(self, status):
        user = fake_user()
        analysis = fake_analysis(status=status)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).status, Analysis.status_choices.NEW)

    def test_creator_is_set_to_caller(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).creator, user)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_run_task_id_is_reset(self, task_id):
        user = fake_user()
        analysis = fake_analysis(run_task_id=task_id)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).run_task_id, '')

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_generate_inputs_task_id_is_reset(self, task_id):
        user = fake_user()
        analysis = fake_analysis(generate_inputs_task_id=task_id)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).generate_inputs_task_id, '')

    def test_portfolio_is_not_supplied___portfolio_is_copied(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).portfolio, analysis.portfolio)

    def test_portfolio_is_supplied___portfolio_is_replaced(self):
        user = fake_user()
        analysis = fake_analysis()
        new_portfolio = fake_portfolio(location_file=fake_related_file())

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'portfolio': new_portfolio.pk}),
            content_type='application/json',
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).portfolio, new_portfolio)

    def test_model_is_not_supplied___model_is_copied(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).model, analysis.model)

    def test_model_is_supplied___model_is_replaced(self):
        user = fake_user()
        analysis = fake_analysis()
        new_model = fake_analysis_model()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'model': new_model.pk}),
            content_type='application/json',
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).model, new_model)

    def test_complex_model_file_is_not_supplied___model_is_copied(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        actual_cmf_pks = [obj.pk for obj in Analysis.objects.get(pk=response.json['id']).complex_model_data_files.all()]
        expected_cmf_pks = [obj.pk for obj in analysis.complex_model_data_files.all()]

        self.assertEqual(expected_cmf_pks, actual_cmf_pks)

    def test_complex_model_file_is_supplied___model_is_replaced(self):
        user = fake_user()
        analysis = fake_analysis()
        new_cmf_1 = fake_data_file()
        new_cmf_2 = fake_data_file()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'complex_model_data_files': [new_cmf_1.pk, new_cmf_2.pk]}),
            content_type='application/json',
        )

        actual_cmf_pks = [obj.pk for obj in Analysis.objects.get(pk=response.json['id']).complex_model_data_files.all()]
        expected_cmf_pks = [new_cmf_1.pk, new_cmf_2.pk]

        self.assertEqual(expected_cmf_pks, actual_cmf_pks)

    def test_settings_file_is_not_supplied___settings_file_is_copied(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(settings_file=fake_related_file(file='{}'))

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    }
                )

                self.assertEqual(Analysis.objects.get(pk=response.json['id']).settings_file.pk, Analysis.objects.get(pk=response.json['id']).pk)

    def test_input_file_is_not_supplied___input_file_is_not_copied(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(input_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    }
                )

                self.assertEqual(Analysis.objects.get(pk=response.json['id']).input_file, None)

    def test_lookup_errors_file_is_cleared(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(lookup_errors_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertIsNone(Analysis.objects.get(pk=response.json['id']).lookup_errors_file)

    def test_lookup_success_file_is_cleared(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(lookup_success_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertIsNone(Analysis.objects.get(pk=response.json['id']).lookup_success_file)

    def test_lookup_validation_file_is_cleared(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(lookup_validation_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertIsNone(Analysis.objects.get(pk=response.json['id']).lookup_validation_file)

    def test_output_file_is_cleared(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(output_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertIsNone(Analysis.objects.get(pk=response.json['id']).output_file)


class AnalysisSettingsJson(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_settings_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_settings_json_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_settings_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_json_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_settings_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_json_is_not_valid___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()
                json_data = {
                    "analysis_settings": {
                        "analysis_tag": "test_analysis",
                        "model_supplier_id": "OasisLMF",
                        "model_version_id": "1",
                        "model_name_id": "PiWind",
                        "number_of_samples": -1,
                        "gul_threshold": 0,
                        "model_settings": {
                            "use_random_number_file": True,
                            "event_occurrence_file_id": "1"
                        },
                        "gul_output": True,
                        "gul_summaries": [
                            {
                                "id": 1,
                                "summarycalc": True,
                                "eltcalc": True,
                                "aalcalc": "Not-A-Boolean",
                                "pltcalc": True,
                                "lec_output": False
                            }
                        ],
                        "il_output": False
                    }
                }

                response = self.app.post(
                    analysis.get_absolute_settings_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    params=json.dumps(json_data),
                    content_type='application/json',
                    expect_errors=True,
                )

                validation_error = {
                    'number_of_samples': ['-1 is less than the minimum of 0'],
                    'gul_summaries-0-aalcalc': ["'Not-A-Boolean' is not of type 'boolean'"]
                }
                self.assertEqual(400, response.status_code)
                self.assertEqual(json.loads(response.body), validation_error)

    def test_settings_json_is_uploaded___can_be_retrieved(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()
                json_data = {
                    "analysis_settings": {
                        "source_tag": "test_source",
                        "analysis_tag": "test_analysis",
                        "model_supplier_id": "OasisLMF",
                        "model_version_id": "1",
                        "model_name_id": "PiWind",
                        "number_of_samples": 10,
                        "gul_threshold": 0,
                        "model_settings": {
                            "use_random_number_file": True,
                            "event_occurrence_file_id": "1"
                        },
                        "gul_output": True,
                        "gul_summaries": [
                            {
                                "id": 1,
                                "summarycalc": True,
                                "eltcalc": True,
                                "aalcalc": True,
                                "pltcalc": True,
                                "lec_output": False
                            }
                        ],
                        "il_output": False
                    }
                }

                self.app.post(
                    analysis.get_absolute_settings_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    params=json.dumps(json_data),
                    content_type='application/json'
                )

                response = self.app.get(
                    analysis.get_absolute_settings_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )
                self.assertEqual(json.loads(response.body), json_data['analysis_settings'])
                self.assertEqual(response.content_type, 'application/json')


class AnalysisSettingsFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_settings_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_settings_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_settings_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_settings_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.post(
                    analysis.get_absolute_settings_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.tar', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1))
    def test_settings_file_is_uploaded___file_can_be_retrieved(self, file_content):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                self.app.post(
                    analysis.get_absolute_settings_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.json', file_content),
                    ),
                )

                response = self.app.get(
                    analysis.get_absolute_settings_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, 'application/json')


class AnalysisInputFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_input_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_input_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_input_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar']))
    def test_input_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(input_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_input_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class AnalysisLookupErrorsFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_lookup_errors_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_lookup_errors_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_lookup_errors_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    '''
    def test_lookup_errors_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_lookup_errors_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)
    '''

    @given(file_content=binary(min_size=1), content_type=sampled_from(['text/csv']))
    def test_lookup_errors_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(lookup_errors_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_lookup_errors_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class AnalysisLookupSuccessFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_lookup_success_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_lookup_success_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_lookup_success_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    '''
    def test_lookup_success_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_lookup_success_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)
    '''

    @given(file_content=binary(min_size=1), content_type=sampled_from(['text/csv']))
    def test_lookup_success_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(lookup_success_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_lookup_success_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class AnalysisLookupValidationFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_lookup_validation_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_lookup_validation_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_lookup_validation_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    '''
    def test_lookup_validation_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_lookup_validation_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)
    '''

    @given(file_content=binary(min_size=1), content_type=sampled_from(['application/json']))
    def test_lookup_validation_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(lookup_validation_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_lookup_validation_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class AnalysisInputGenerationTracebackFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_input_generation_traceback_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_input_generation_traceback_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_input_generation_traceback_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_input_generation_traceback_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_input_generation_traceback_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    @given(file_content=binary(min_size=1))
    def test_input_generation_traceback_file_is_present___file_can_be_retrieved(self, file_content):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(input_generation_traceback_file=fake_related_file(file=file_content, content_type='text/plain'))

                response = self.app.get(
                    analysis.get_absolute_input_generation_traceback_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, 'text/plain')


class AnalysisOutputFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_output_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_output_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_output_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_output_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_output_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_output_file_is_not_valid_format___post_response_is_405(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.post(
                    analysis.get_absolute_output_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.csv', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(405, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar']))
    def test_output_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(output_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_output_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class AnalysisRunTracebackFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_run_traceback_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_run_traceback_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_run_traceback_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_run_traceback_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_run_traceback_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_run_traceback_file_is_not_valid_format___post_response_is_405(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.post(
                    analysis.get_absolute_run_traceback_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.csv', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(405, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar']))
    def test_run_traceback_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(run_traceback_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_run_traceback_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)
