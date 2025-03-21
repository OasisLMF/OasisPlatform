from __future__ import absolute_import

from celery import Celery
from ..conf import celeryconf_v2 as celery_conf
from ..conf.iniconf import settings
import shutil
from ..common.filestore.filestore import get_filestore
import os

app = Celery()
app.config_from_object(celery_conf)


@app.task(name='run_exposure_task')
def run_exposure_task(loc_filepath, acc_filepath, ri_filepath, rl_filepath, given_params):
    from oasislmf.manager import OasisManager
    from src.model_execution_worker.utils import TemporaryDir

    try:
        with TemporaryDir() as temp_dir:
            loc_temp = os.path.join(temp_dir, "location.csv")
            acc_temp = os.path.join(temp_dir, "account.csv")
            ri_temp = os.path.join(temp_dir, "ri_info.csv") if ri_filepath else None
            rl_temp = os.path.join(temp_dir, "ri_scope.csv") if rl_filepath else None
            shutil.copy2(loc_filepath, loc_temp)
            shutil.copy2(acc_filepath, acc_temp)
            if ri_filepath:
                shutil.copy2(ri_filepath, ri_temp)
            if rl_filepath:
                shutil.copy2(rl_filepath, rl_temp)
            os.chdir(temp_dir)
            print(temp_dir)
            params = OasisManager()._params_run_exposure()
            update_params(params, given_params)
            OasisManager().run_exposure(**params)
            return get_filestore(settings).put("outfile.csv")

    except Exception as e:
        with open("error.txt", "w") as error_file:
            error_file.write(e)
        return get_filestore(settings).put("error.txt")


def update_params(params, given_params):
    for k, v in given_params.items():
        if k in params:
            if " " not in v:
                params[k] = v
            else:
                raise ValueError(f"Values must be one word: {k}, {v}")
    params["output_file"] = "outfile.csv"
