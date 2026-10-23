import json

from django.test import TestCase
from django_webtest import WebTestMixin
from django.urls import reverse

from src.server.oasisapi.analyses.v2_api.tests.fakes import fake_analysis


class AnalysisStatusViewTestCase(WebTestMixin, TestCase):
    def test_events_total_is_provided___num_events_total_is_set(self):
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': analysis.pk, 'events_total': 42}),
            content_type='application/json',
        )

        self.assertEqual(204, response.status_code)
        analysis.refresh_from_db()
        self.assertEqual(42, analysis.num_events_total)
        self.assertEqual(0, analysis.num_events_complete)

    def test_events_complete_is_provided___num_events_complete_is_incremented(self):
        analysis = fake_analysis(num_events_complete=5)

        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': analysis.pk, 'events_complete': 3}),
            content_type='application/json',
        )

        self.assertEqual(204, response.status_code)
        analysis.refresh_from_db()
        self.assertEqual(8, analysis.num_events_complete)

    def test_events_complete_is_provided_twice___num_events_complete_accumulates(self):
        analysis = fake_analysis(num_events_complete=0)

        for _ in range(2):
            self.app.post(
                reverse('analysis-status'),
                params=json.dumps({'analysis_pk': analysis.pk, 'events_complete': 4}),
                content_type='application/json',
            )

        analysis.refresh_from_db()
        self.assertEqual(8, analysis.num_events_complete)

    def test_gul_ready_is_provided_twice___num_gul_ready_accumulates(self):
        analysis = fake_analysis()

        for _ in range(2):
            self.app.post(
                reverse('analysis-status'),
                params=json.dumps({'analysis_pk': analysis.pk, 'gul_ready': 1}),
                content_type='application/json',
            )

        analysis.refresh_from_db()
        self.assertEqual(2, analysis.num_gul_ready)

    def test_outputs_total_is_provided___num_outputs_total_is_set(self):
        analysis = fake_analysis(num_outputs_total=10, num_outputs_complete=4)

        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': analysis.pk, 'outputs_total': 51}),
            content_type='application/json',
        )

        self.assertEqual(204, response.status_code)
        analysis.refresh_from_db()
        self.assertEqual(51, analysis.num_outputs_total)
        self.assertEqual(4, analysis.num_outputs_complete)

    def test_outputs_complete_is_provided_twice___num_outputs_complete_accumulates(self):
        analysis = fake_analysis(num_outputs_complete=3)

        for _ in range(2):
            self.app.post(
                reverse('analysis-status'),
                params=json.dumps({'analysis_pk': analysis.pk, 'outputs_complete': 1}),
                content_type='application/json',
            )

        analysis.refresh_from_db()
        self.assertEqual(5, analysis.num_outputs_complete)

    def test_unknown_key_is_provided___it_is_ignored(self):
        analysis = fake_analysis(num_events_complete=2)

        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': analysis.pk, 'events_complete': 1, 'outputs_done': 1}),
            content_type='application/json',
        )

        self.assertEqual(204, response.status_code)
        analysis.refresh_from_db()
        self.assertEqual(3, analysis.num_events_complete)

    def test_outputs_complete_is_negative___response_is_400(self):
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': analysis.pk, 'outputs_complete': -1}),
            content_type='application/json',
            expect_errors=True,
        )

        self.assertEqual(400, response.status_code)

    def test_neither_events_total_nor_events_complete_are_provided___no_fields_are_updated(self):
        analysis = fake_analysis(num_events_total=10, num_events_complete=5)

        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': analysis.pk}),
            content_type='application/json',
        )

        self.assertEqual(204, response.status_code)
        analysis.refresh_from_db()
        self.assertEqual(10, analysis.num_events_total)
        self.assertEqual(5, analysis.num_events_complete)

    def test_analysis_pk_is_missing___response_is_400(self):
        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'events_total': 1}),
            content_type='application/json',
            expect_errors=True,
        )

        self.assertEqual(400, response.status_code)

    def test_analysis_pk_does_not_exist___response_is_204(self):
        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': 999999999, 'events_total': 1}),
            content_type='application/json',
        )

        self.assertEqual(204, response.status_code)

    def test_user_is_not_authenticated___response_is_still_ok(self):
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-status'),
            params=json.dumps({'analysis_pk': analysis.pk, 'events_total': 1}),
            content_type='application/json',
        )

        self.assertEqual(204, response.status_code)
