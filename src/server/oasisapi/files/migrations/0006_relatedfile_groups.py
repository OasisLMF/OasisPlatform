# Generated by Django 3.2.20 on 2023-07-24 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('files', '0005_relatedfile_oed_validated'),
    ]

    operations = [
        migrations.AddField(
            model_name='relatedfile',
            name='groups',
            field=models.ManyToManyField(blank=True, default=None, help_text='Groups allowed to access this object', to='auth.Group'),
        ),
    ]
