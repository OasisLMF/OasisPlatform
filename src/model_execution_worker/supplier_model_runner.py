import multiprocessing

import subprocess

from oasislmf.model_execution.bash import genbash
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log


@oasis_log()
def run(analysis_settings, number_of_processes=-1):
    if number_of_processes == -1:
        number_of_processes = multiprocessing.cpu_count()

    genbash(number_of_processes, analysis_settings, 'run_ktools.sh')
    try:
        subprocess.check_call(['bash', 'run_ktools.sh'])
    except subprocess.CalledProcessError as e:
        raise OasisException('Error running ktools: {}'.format(e.stderr))
