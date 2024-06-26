# Generated by Django 3.2.19 on 2023-07-31 09:39

from django.db import migrations, models
import django.db.models.deletion
import src.server.oasisapi.files.models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0005_relatedfile_oed_validated'),
    ]

    operations = [
        migrations.CreateModel(
            name='MappingFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=src.server.oasisapi.files.models.random_file_name)),
            ],
        ),
        migrations.AddField(
            model_name='relatedfile',
            name='conversion_state',
            field=models.CharField(choices=[('NONE', 'None'), ('PENDING', 'Pending'), ('IN_PROGRESS', 'In Progress'), ('DONE', 'Done'), ('ERROR', 'Error')], default='NONE', max_length=11),
        ),
        migrations.AddField(
            model_name='relatedfile',
            name='converted_file',
            field=models.FileField(blank=True, default=None, help_text='The file to store after conversion', null=True, upload_to=src.server.oasisapi.files.models.random_file_name),
        ),
        migrations.AddField(
            model_name='relatedfile',
            name='mapping_file',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='files.mappingfile'),
        ),
    ]
