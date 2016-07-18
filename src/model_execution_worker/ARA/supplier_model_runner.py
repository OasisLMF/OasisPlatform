import logging
import multiprocessing
from model_execution import model_runner_ara

def run(analysis_settings, number_of_processes=-1):

    if number_of_processes == -1:
        number_of_processes = multiprocessing.cpu_count()

    model_runner_ara.run_analysis(analysis_settings, number_of_processes)
