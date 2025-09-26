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
MAX_RETRIES = 6
RETRY_INTERVAL = 5

def add_portfolio(client):

    model_data_dir = os.environ.get("OASIS_MODEL_DATA_DIR", "./OasisPiWind/")
    logger.info(f"Found model data dir: {model_data_dir}")

    piwind_portfolio_input = {
    "portfolio_name": "piwind-small",
    "location_fp": f"{model_data_dir}/tests/inputs/SourceLocOEDPiWind10.csv",
    "accounts_fp": f"{model_data_dir}/tests/inputs/SourceAccOEDPiWind.csv",
    "ri_info_fp": f"{model_data_dir}/tests/inputs/SourceReinsInfoOEDPiWind.csv",
    "ri_scope_fp": f"{model_data_dir}/tests/inputs/SourceReinsScopeOEDPiWind.csv"
    }
    existing_names = [r['name'] for r in client.portfolios.get().json()]
    logger.info('Adding portfolios...')

    if piwind_portfolio_input.get('portfolio_name') in existing_names:
        logger.info(f'Skipping {piwind_portfolio_input["portfolio_name"]}')
    else:
        logger.info(f'Adding {piwind_portfolio_input["portfolio_name"]}')
        client.upload_inputs(**piwind_portfolio_input)

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


def run_and_cancel_analysis(client, version="v1", cancel_ig=True):
    # get portfolio and model id
    portfolio_id = client.portfolios.search({"name": "piwind-small"}).json()[0]["id"]
    model_id = client.models.search({"version_id__contains": version}).json()[0]["id"]

    # create analysis
    name = f"analysis-{datetime.now().strftime('%d%m%y_%H%M%S')}"
    resp = client.analyses.create(name, portfolio_id, model_id).json()

    logger.info(f"Created analysis: {resp['id']}")

    # upload anlaysis settings
    with open(SETTINGS_PATH, "r") as f:
        analysis_settings = json.load(f)

    analysis_id = resp["id"]

    client.upload_settings(analysis_id, analysis_settings)

    logger.info("Applied analysis settings")

    logger.info("Running `analyses.generate`")

    retry_command(client.analyses.generate, {"ID": analysis_id})

    logger.info("Running `analyses.run`")
    resp = retry_command(client.analyses.generate, {"ID": analysis_id})

    logger.info("Started analysis")

    if cancel_ig:
        resp = client.analyses.cancel(analysis_id).json()
        logger.info("Cancelled during input generation")
        print(resp)
        return


if __name__=="__main__":

    parser = argparse.ArgumentParser(description="Testing zombie celery processes")
    parser.add_argument("-v", "--version", default="v1", help="Version id for model")
    parser.add_argument("--cancel_ig", action="store_true", help="Cancel run during input generation.")


    kwargs = vars(parser.parse_args())

    client = APIClient(username="admin", password="password")

    run_and_cancel_analysis(client, **kwargs)
