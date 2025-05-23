# Generated by Django 3.2.25 on 2024-12-09 16:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_models', '0009_alter_analysismodel_run_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysismodel',
            name='ver_ods',
            field=models.CharField(default=None, help_text='The worker ods-tools version.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='analysismodel',
            name='ver_oed',
            field=models.CharField(default=None, help_text='The worker oed-schema version.', max_length=255, null=True),
        ),
    ]
