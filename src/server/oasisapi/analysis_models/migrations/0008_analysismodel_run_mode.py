# Generated by Django 3.2.20 on 2023-12-06 15:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_models', '0007_modelscalingoptions_worker_count_min'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysismodel',
            name='run_mode',
            field=models.CharField(choices=[('BOTH', 'Works on both Execution modes'), ('V1', 'Available for Single-Instance Execution'), ('V2', 'Available for Distributed Execution')], default='BOTH', help_text='Execution modes Available, v1 = Single-Instance, v2 = Distributed Execution', max_length=4, null=True),
        ),
    ]
