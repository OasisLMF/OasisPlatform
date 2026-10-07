import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0014_merge_0006_relatedfile_groups_0013_mappingfile_groups'),
        ('portfolios', '0010_portfolio_currency_conversion_json_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolio',
            name='location_file_source',
            field=models.CharField(
                choices=[
                    ('user_upload', 'User upload'),
                    ('external', 'External provider'),
                    ('merged', 'Merged (user + external)'),
                ],
                default='user_upload',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='portfolio',
            name='location_file_external_provider',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='portfolio',
            name='location_file_audit',
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='audit_portfolios',
                to='files.relatedfile',
            ),
        ),
    ]
