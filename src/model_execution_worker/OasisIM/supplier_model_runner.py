import multiprocessing
from oasis_utils import oasis_log_utils
from model_execution import model_runner

@oasis_log_utils.oasis_log()
def run(analysis_settings, number_of_processes=-1):

    if number_of_processes == -1:
        number_of_processes = multiprocessing.cpu_count()

    model_runner.run_analysis(analysis_settings, number_of_processes)
