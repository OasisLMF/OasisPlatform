# Generated by Django 3.2.9 on 2021-11-22 13:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analyses', '0013_analysis_sub_task_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='analysis',
            name='sub_task_count',
        ),
    ]
