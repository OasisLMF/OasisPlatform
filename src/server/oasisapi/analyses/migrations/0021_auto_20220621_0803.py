# Generated by Django 3.2.13 on 2022-06-21 08:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analyses', '0020_alter_analysis_priority'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='analysis',
            options={'ordering': ['id'], 'verbose_name_plural': 'analyses'},
        ),
        migrations.AlterModelOptions(
            name='analysistaskstatus',
            options={'ordering': ['id']},
        ),
    ]