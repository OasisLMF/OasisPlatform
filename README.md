<img src="https://oasislmf.org/packages/oasis_theme_package/themes/oasis_theme/assets/src/oasis-lmf-colour.png" alt="Oasis LMF logo" width="250"/>

[![Build](http://ci.oasislmfdev.org/buildStatus/icon?job=pipeline_stable/oasis_platform)](http://ci.oasislmfdev.org/blue/organizations/jenkins/pipeline_stable%2Foasis_platform/activity)

# Oasis Platform
Provides core components of the Oasis platform, specifically:
* Flask application that provides the Oasis REST API
* Celery worker for running a model

## First Steps

### Simple environment

A simple environment for the testing the API and worker can be created using Docker compose.

<img src="https://github.com/OasisLMF/OasisPlatform/blob/master/Oasis%20Simple%20Runner.png" alt="Simple Oasis platform test environment"/>

First make sure that you have Docker running. Then build the images for the API server, model execution worker and API runner:

    docker build -f Dockerfile.oasis_api_server -t oasis_api_server .
    docker build -f Dockerfile.model_execution_worker -t model_execution_worker .
    docker build -f Dockerfile.api_runner -t api_runner .

Start the docker network:

    docker-compose up -d

Check that the server is running:

    curl localhost:8001/healthcheck

(For the Rabbit management application browse to http://localhost:15672, for Flower, the Celery management application, browse to http://localhost:5555.)

To run a test analysis using the worker image and example model data, run the following command:
    
    docker exec oasisapi_runner_1 sh run_api_test_analysis.sh

### Calling the Server

The API server provides a REST interface which is described <a href="https://oasislmf.github.io/docs/oasis_rest_api.html" target="_blank">here</a>. You can use any suitable command line client such as `curl` or <a href="www.httpie.org" target="_blank">`httpie`</a> to make individual API calls, but a custom Python client may be a better option - for this you can use the <a href="https://giub.com/OasisLMF/OasisAPIClient" target="_blank">`OasisAPIClient` repository</a>.

Oasis provides a built-in client `model_api_tester.py` (located in `src/oasisapi_client`) which is an executable multi-threaded script that can generate model analyses given the locations of the model inputs and analysis settings JSON file (see the <a href="https://github.com/OasisLMF/OasisAPIClient" target="_blank">`OasisAPIClient` repository</a> or <a href="https://oasislmf.github.io/OasisAPIClient/" target="_blank">`OasisAPIClient` documentation site</a> for more information). First install the Oasis API client requirements

    pip install -r src/oasisapi_client/requirements.py

As an example, you can run analyses for a generic Oasis model provided in this repository (model data and analysis settings JSON file are located in the `tests/data` subfolder) using

    python ./src/oasisapi_client/model_api_tester.py -s <API server URL:port> -a tests/data/analysis_settings.json -i tests/data/input -o tests/data/output -n 1 -v

## Development

### GitFlow

We use the GitFlow model described <A href="http://nvie.com/posts/a-successful-git-branching-model"> here </A>.

The main idea is that the central repo holds two main branches with an infinite lifetime:

* master: main branch where the source code of HEAD always reflects a production-ready state
* develop: main branch where the source code of HEAD always reflects a state with the latest delivered development changes for the next release. This is where our automatic builds are built from.

When the source code in the develop branch reaches a stable point and is ready to be released, all of the changes should be merged back into master. 
Feature branchs should be used for new features and fixes, then a Pull Request isues to merge into develop.

### Dependencies

Dependencies are controlled by ``pip-tools``. To install the development dependencies, first install ``pip-tools`` using:

    pip install pip-tools

and run:

    pip-sync

To add new dependencies to the development requirements add the package name to ``requirements.in`` or to add a new dependency to the installed package add the package name to ``requirements-package.in``.
Version specifiers can be supplied to the packages but these should be kept as loose as possible so that all packages can be easily updated and there will be fewer conflict when installing.
After adding packages to either ``*.in`` file, the following command should be ran ensuring the development dependencies are kept up to date:

    pip-compile && pip-sync

### Testing

To test the code style run::

    flake8

To test against all supported python versions run::

    tox

To test against your currently installed version of python run::

    py.test

To run the full test suite run::

    ./runtests.sh

### Deploying

The Oasis CI system builds and deploys the following Docker images to DockerHub:

* <a href="https://hub.docker.com/r/coreoasis/oasis_api_server">coreoasis/oasis_api_server</a>
* <a href="https://hub.docker.com/r/coreoasis/model_execution_worker">coreoasis/model_execution_worker</a>

Note that the Dockerfiles cannot be used directly as there are version stubs that get substitued at build time by the CI system.

## Documentation
* <a href="https://github.com/OasisLMF/OasisApi/issues">Issues</a>
* <a href="https://github.com/OasisLMF/OasisApi/releases">Releases</a>
* <a href="https://oasislmf.github.io">General Oasis documentation</a>
* <a href="https://oasislmf.github.io/docs/oasis_rest_api.html">Oasis API documentation</a>
* <a href="https://oasislmf.github.io/OasisPlatform/modules.html">Oasis Platform module documentation</a>

## License
The code in this project is licensed under BSD 3-clause license.
