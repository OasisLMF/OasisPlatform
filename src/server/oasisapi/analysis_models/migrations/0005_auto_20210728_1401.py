# Generated by Django 3.2.5 on 2021-07-28 14:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_models', '0004_analysismodel_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysismodel',
            name='num_analysis_chunks',
            field=models.PositiveSmallIntegerField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='analysismodel',
            name='oasislmf_config',
            field=models.TextField(default=''),
        ),
        migrations.CreateModel(
            name='QueueModelAssociation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('queue_name', models.CharField(editable=False, max_length=255)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='queue_associations', to='analysis_models.analysismodel')),
            ],
            options={
                'unique_together': {('model', 'queue_name')},
            },
        ),
    ]