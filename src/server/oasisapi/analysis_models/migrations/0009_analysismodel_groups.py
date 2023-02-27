# Generated by Django 3.2.8 on 2021-10-28 07:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('analysis_models', '0008_alter_modelscalingoptions_scaling_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysismodel',
            name='groups',
            field=models.ManyToManyField(blank=True, default=None, help_text='Groups allowed to access this object', to='auth.Group'),
        ),
    ]