# Generated by Django 3.2.13 on 2022-06-21 08:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_models', '0010_auto_20220620_1426'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='analysismodel',
            options={'ordering': ['id']},
        ),
    ]