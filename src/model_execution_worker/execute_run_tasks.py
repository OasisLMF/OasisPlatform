from celery import signature, Celery
from django.core.files.base import File
import os
import subprocess
from ..server.oasisapi.portfolios.models import Portfolio, RelatedFile


app = Celery()


@app.task(name='run_exposure_task')
def run_exposure_task(pk, file_path, params):
    try:
        instance = Portfolio.objects.get(id=pk)
        os.chdir(file_path)
        command = ['oasislmf', 'exposure', 'run']

        for k, v in params.items():
            command.append(k)
            command.append(v)

        with open('outfile.csv', 'w') as outfile:
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            outfile.write(process.stdout)

        with open('outfile.csv', 'rb') as file:
            instance.exposure_run_file = RelatedFile.objects.create(
                file=File(file, name='outfile.csv'),
                filename='outfile.csv',
                content_type='text/csv'
            )

        instance.save()
        return {"message": "success", "file_url": instance.exposure_run_file.file.url}

    except Exception as ex:
        traceback_info = str(ex)
        signature(
            'on_error',
            args=(traceback_info, 'run_exposure_task', pk),
            queue='celery'
        ).delay()
        raise
