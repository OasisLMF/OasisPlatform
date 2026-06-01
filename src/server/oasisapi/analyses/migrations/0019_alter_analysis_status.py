from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analyses', '0018_alter_analysis_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysis',
            name='status',
            field=models.CharField(
                choices=[
                    ('NEW', 'New'),
                    ('INPUTS_GENERATION_ERROR', 'Inputs generation error'),
                    ('INPUTS_GENERATION_NO_KEYS', 'Inputs generation no keys'),
                    ('INPUTS_GENERATION_CANCELLED', 'Inputs generation cancelled'),
                    ('INPUTS_GENERATION_STARTED', 'Inputs generation started'),
                    ('INPUTS_GENERATION_QUEUED', 'Inputs generation added to queue'),
                    ('READY', 'Ready'),
                    ('RUN_QUEUED', 'Run added to queue'),
                    ('RUN_STARTED', 'Run started'),
                    ('RUN_COMPLETED', 'Run completed'),
                    ('RUN_CANCELLED', 'Run cancelled'),
                    ('RUN_ERROR', 'Run error'),
                ],
                db_index=True,
                default='NEW',
                editable=False,
                max_length=27,
            ),
        ),
    ]
