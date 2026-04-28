import uuid

from django.conf import settings
from django.db import models
from django.db.models import TextChoices
from model_utils.models import TimeStampedModel


class ExternalProviderSettings(models.Model):
    provider = models.CharField(max_length=64, primary_key=True)
    base_url = models.URLField()
    client_id = models.CharField(max_length=255, blank=True)
    # stored in DB; in production use env vars (OASIS_GXM_CLIENT_SECRET) via conf.ini override
    client_secret = models.CharField(max_length=255, blank=True)
    default_as_of = models.DateTimeField(null=True, blank=True)
    entitlements_cache = models.JSONField(default=dict)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'external provider settings'

    def __str__(self):
        return self.provider


class ExternalJob(TimeStampedModel):
    class Status(TextChoices):
        PENDING = 'PENDING', 'Pending'
        RUNNING = 'RUNNING', 'Running'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class JobType(TextChoices):
        LOCATION_FILE = 'location_file', 'Location file retrieval'
        ENRICH = 'enrich', 'Attribute enrichment'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=64, db_index=True)
    job_type = models.CharField(max_length=32, choices=JobType.choices)
    portfolio = models.ForeignKey(
        'portfolios.Portfolio',
        on_delete=models.CASCADE,
        related_name='external_jobs',
    )
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='external_jobs',
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    task_id = models.CharField(max_length=255, blank=True)
    request_data = models.JSONField(default=dict)
    result_file = models.ForeignKey(
        'files.RelatedFile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='external_job_results',
    )
    audit_file = models.ForeignKey(
        'files.RelatedFile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='external_job_audits',
    )
    error_message = models.TextField(blank=True)
    started = models.DateTimeField(null=True, blank=True)
    finished = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.provider}/{self.job_type}/{self.id}'
