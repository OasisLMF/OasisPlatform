from __future__ import absolute_import

from ..conf import celeryconf_v2 as celery_conf
from ..conf.iniconf import settings
from ..common.filestore.filestore import get_filestore
from oasislmf.manager import OasisManager
from src.model_execution_worker.utils import TemporaryDir, update_params, copy_or_download, get_destination_file
import os
from celery import Celery

app = Celery()

app.config_from_object(celery_conf)


@app.task(name='run_exposure_task')
def run_exposure_task(loc_filepath, acc_filepath, ri_filepath, rl_filepath, given_params):
    with TemporaryDir() as temp_dir:
        loc_temp = get_destination_file(loc_filepath, temp_dir, "location")
        copy_or_download(loc_filepath, loc_temp)
        acc_temp = get_destination_file(acc_filepath, temp_dir, "account")
        copy_or_download(acc_filepath, acc_temp)
        if ri_filepath:
            ri_temp = get_destination_file(ri_filepath, temp_dir, "ri_loss")
            copy_or_download(ri_filepath, ri_temp)
        if rl_filepath:
            rl_temp = get_destination_file(acc_filepath, temp_dir, "ri_scope")
            copy_or_download(rl_filepath, rl_temp)

        os.chdir(temp_dir)
        try:
            params = OasisManager()._params_run_exposure()
            update_params(params, given_params)
            OasisManager().run_exposure(**params)
            return get_filestore(settings).put("outfile.csv")
        except Exception as e:
            with open("error.txt", "w") as error_file:
                error_file.write(str(e))
            return get_filestore(settings).put("error.txt")
