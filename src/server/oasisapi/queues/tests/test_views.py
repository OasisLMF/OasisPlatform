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
