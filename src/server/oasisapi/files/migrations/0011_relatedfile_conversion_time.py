# Generated by Django 3.2.19 on 2023-08-02 10:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0010_auto_20230802_0929'),
    ]

    operations = [
        migrations.AddField(
            model_name='relatedfile',
            name='conversion_time',
            field=models.DateTimeField(blank=True, default=None, editable=False, help_text='The time the last conversion was started', null=True),
        ),
    ]
