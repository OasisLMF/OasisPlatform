# Generated by Django 3.2.20 on 2024-01-22 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_models', '0008_analysismodel_run_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysismodel',
            name='run_mode',
            field=models.CharField(choices=[('V1', 'Available for Single-Instance Execution'), ('V2', 'Available for Distributed Execution')], default=None, help_text='Execution modes Available, v1 = Single-Instance, v2 = Distributed Execution', max_length=2, null=True),
        ),
    ]
