import uuid
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('files', '0014_merge_0006_relatedfile_groups_0013_mappingfile_groups'),
        ('portfolios', '0010_portfolio_currency_conversion_json_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalProviderSettings',
            fields=[
                ('provider', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('base_url', models.URLField()),
                ('client_id', models.CharField(blank=True, max_length=255)),
                ('client_secret', models.CharField(blank=True, max_length=255)),
                ('default_as_of', models.DateTimeField(blank=True, null=True)),
                ('entitlements_cache', models.JSONField(default=dict)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'external provider settings',
            },
        ),
        migrations.CreateModel(
            name='ExternalJob',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('provider', models.CharField(db_index=True, max_length=64)),
                ('job_type', models.CharField(
                    choices=[('location_file', 'Location file retrieval'), ('enrich', 'Attribute enrichment')],
                    max_length=32,
                )),
                ('status', models.CharField(
                    choices=[
                        ('PENDING', 'Pending'), ('RUNNING', 'Running'), ('COMPLETED', 'Completed'),
                        ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled'),
                    ],
                    db_index=True,
                    default='PENDING',
                    max_length=16,
                )),
                ('task_id', models.CharField(blank=True, max_length=255)),
                ('request_data', models.JSONField(default=dict)),
                ('error_message', models.TextField(blank=True)),
                ('started', models.DateTimeField(blank=True, null=True)),
                ('finished', models.DateTimeField(blank=True, null=True)),
                ('audit_file', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='external_job_audits',
                    to='files.relatedfile',
                )),
                ('initiator', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='external_jobs',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('portfolio', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='external_jobs',
                    to='portfolios.portfolio',
                )),
                ('result_file', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='external_job_results',
                    to='files.relatedfile',
                )),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
    ]
