from __future__ import absolute_import

from celery import Celery
import subprocess
from ..conf import celeryconf_v2 as celery_conf
from ..conf.iniconf import settings
import shutil
from ..common.filestore.filestore import get_filestore

app = Celery()
app.config_from_object(celery_conf)

@app.task(name='run_exposure_task')
def run_exposure_task(loc_filepath, acc_filepath, params):
    print('Task received')
    command = ['oasislmf', 'exposure', 'run', '-f', 'outfile.csv']

    shutil.copy2(loc_filepath, "location.csv")
    shutil.copy2(acc_filepath, "account.csv")

    for k, v in params.items():
        command.append(k)
        command.append(v)
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        filestore = get_filestore(settings)
        return filestore.put("outfile.csv")
    except Exception as e:
        print(e)
        print(e.stderr)
        print(e.stdout)
        raise
