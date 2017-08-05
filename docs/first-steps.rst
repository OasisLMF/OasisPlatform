First Steps
===========

Docker and ktools
-----------------

First make sure that you have Docker running. Then make sure that the
ktools binaries are installed (see `ktools <https://github.com/OasisLMF/ktools>`_ GitHub repository for
instructions) and the ktools docker image is available (pull from
`Docker Hub <https://hub.docker.com/r/coreoasis/ktools/>`_, or build locally from the ktools
repository, and name it as ``ktools`` to match the reference in the
``docker-compose.yml``).

Then build the images for the API server, model execution worker and API
runner:

::

    docker build -f Dockerfile.oasis_api_server -t oasis_api_server .
    docker build -f Dockerfile.model_execution_worker -t model_execution_worker .
    docker build -f Dockerfile.api_runner -t api_runner .

Start the docker network:

::

    docker-compose up -d

Check that the server is running:

::

    curl localhost:8001/healthcheck

(For the Rabbit management application browse to http://localhost:15672,
for Flower, the celery management application, browse to
http://localhost:5555.)

Calling the server
------------------

The API server provides a REST interface which is described here. You
can use any suitable command line client such as ``curl`` or
`httpie <www.httpie.org>`_  to make individual API calls, but a custom Python client
may be a better option - for this you can use the `OasisAPIClient <https://github.com/OasisLMF/OasisAPIClient>`_
repository.

To run the example API client tester (located in ``src/utils``; for a
generic Oasis model) first install the Oasis API client requirements

::

    pip install -r src/oasisapi_client/requirements.py

and then call the tester using

::

    python ./src/utils/api_tester.py -i localhost:8001 -a tests/data/analysis_settings.json -d tests/data/input -o tests/data/output -n 1 -v
