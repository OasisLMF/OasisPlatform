from oasislmf.platform_api.client import APIClient
import logging
import os
import json
from datetime import datetime
import time
import argparse

from requests.models import HTTPError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SETTINGS_PATH = os.path.join(os.environ.get("OASIS_MODEL_DATA_DIR", "./OasisPiWind/"), 'analysis_settings.json')
MAX_RETRIES = 10
RETRY_INTERVAL = 5
POLL_INTERVAL = 2

VALID_STATUSES =  [
        'NEW',
        'INPUTS_GENERATION_ERROR',
        'INPUTS_GENERATION_CANCELLED',
        'INPUTS_GENERATION_STARTED',
        'INPUTS_GENERATION_QUEUED',
        'READY',
        'RUN_QUEUED',
        'RUN_STARTED',
        'RUN_COMPLETED',
        'RUN_CANCELLED',
        'RUN_ERROR',
        ]

COMPLETED_STATUSES = [
        'INPUTS_GENERATION_ERROR',
        'INPUTS_GENERATION_CANCELLED',
        'RUN_COMPLETED',
        'RUN_CANCELLED',
        'RUN_ERROR',
                      ]

def retry_command(command, kwargs):
    retry_count = 0
    while True:
        if retry_count >  MAX_RETRIES:
            breakpoint()
            raise Exception("Failed to start analysis")

        if retry_count > 0:
            time.sleep(RETRY_INTERVAL)

        try:
            resp = command(**kwargs).json()
            break
        except HTTPError as e:
            retry_count += 1
            logger.info(f"Failed running {retry_count} times.")

    return resp


def run_and_cancel_analysis(client, worker="v1", portfolio="piwind-small", cancel_ig=True, cancel_state=None,
                            settings_path=SETTINGS_PATH):

    # get portfolio and model id
    portfolio_id = client.portfolios.search({"name": portfolio}).json()[0]["id"]
    model_id = client.models.search({"model_id__contains": worker}).json()[0]["id"]

    logger.info(f"Found portfolio ID: {portfolio_id}")
    logger.info(f"Found model ID: {model_id}")

    # create analysis
    name = f"analysis-{datetime.now().strftime('%d%m%y_%H%M%S')}"
    resp = client.analyses.create(name, portfolio_id, model_id).json()

    logger.info(f"Created analysis: {resp['id']}")

    # upload anlaysis settings
    with open(settings_path, "r") as f:
        analysis_settings = json.load(f)

    analysis_id = resp["id"]

    client.upload_settings(analysis_id, analysis_settings)

    logger.info("Applied analysis settings")

    logger.info("Running `analyses.generate`")

    retry_command(client.analyses.generate, {"ID": analysis_id})

    if cancel_ig:
        resp = client.analyses.cancel(analysis_id).json()
        logger.info("Cancelled during input generation")
        print(resp)
        return

    input("Press Enter to start running...")

    logger.info("Running `analyses.run`")
    resp = retry_command(client.analyses.run, {"ID": analysis_id})

    logger.info("Started analysis")

    if cancel_state is not None:
        assert cancel_state.upper() in VALID_STATUSES, "cancel_state needs to be a valid status"

        while True:
            time.sleep(POLL_INTERVAL)

            resp = client.analyses.get(analysis_id).json()
            logger.info(f"Current status: {resp['status']}")

            if resp['status'].upper() == cancel_state:
                break

            if resp['status'].upper() in COMPLETED_STATUSES:
                logger.info(f"Cancel state {cancel_state.upper()} not found.")
                break


if __name__=="__main__":

    parser = argparse.ArgumentParser(description="Testing zombie celery processes")
    parser.add_argument("-w", "--worker", default="v1", help="worker for model")
    parser.add_argument("--cancel_ig", action="store_true", help="Cancel run during input generation.")
    parser.add_argument("--cancel_state", default=None, type=str, help="State to look for")
    parser.add_argument("--portfolio", default="piwind-small", type=str, help="Portfolio to run against model")
    parser.add_argument("-s", "--settings_path", default=SETTINGS_PATH, type=str, help="Path to analysis settings file")


    kwargs = vars(parser.parse_args())

    client = APIClient(username="admin", password="password")

    run_and_cancel_analysis(client, **kwargs)
