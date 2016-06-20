import os
import sys
import json
import shutil
import tempfile
import logging
import subprocess
from model_execution import model_runner
from common import helpers
from billiard import Process, Queue, cpu_count

def run(analysis_settings, number_of_processes=-1):
 
    if number_of_processes == -1:
        number_of_processes = cpu_count()

    model_runner.run_analysis(analysis_settings, number_of_processes)