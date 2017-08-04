============
Introduction
============

First steps
-----------

First make sure that the ktools binaries are installed (see the `ktools <https://github.com/OasisLMF/ktools>`_
GitHub repository for instructions) and the ktools docker image is
available (from ``coreoasis/ktools`` on Docker Hub, or build locally
from the ktools repository). Also ensure that API runner image has been
built (from ``Dockerfile.api_runner``).

Then, build the images for the API server and model execution worker:

::

    docker build -f Dockerfile.oasis_api_server -t oasis_api_server .
    docker build -f Dockerfile.model_execution_worker -t model_execution_worker .

Run docker compose:

::

    docker-compose up -d

Check that the server is running:

::

    curl localhost:8001/healthcheck

For the Rabbit management application browse to http://localhost:15672.

For Flower, the celery management application, browse to
http://locathost:5555.

To run the API client tester, run the following commands:

::

    pip install -r src/client/requirements.py
    python ./src/utils/api_tester.py -i localhost:8001 -a tests/data/analysis_settings.json -d tests/data/input -o tests/data/output -n 1 -v