<img src="https://oasislmf.org/packages/oasis_theme_package/themes/oasis_theme/assets/src/oasis-lmf-colour.png" alt="Oasis LMF logo" width="250"/>

[![ktools version](https://img.shields.io/github/tag/Oasislmf/ktools?label=ktools)](https://github.com/OasisLMF/ktools/releases)
[![PyPI version](https://badge.fury.io/py/oasislmf.svg)](https://badge.fury.io/py/oasislmf)

[![Platform Image tests](https://github.com/OasisLMF/OasisPlatform/actions/workflows/test-images.yml/badge.svg?branch=master)](https://github.com/OasisLMF/OasisPlatform/actions/workflows/test-images.yml)
[![Platform Python tests](https://github.com/OasisLMF/OasisPlatform/actions/workflows/test-python.yml/badge.svg?branch=master)](https://github.com/OasisLMF/OasisPlatform/actions/workflows/test-python.yml)
[![Platform Vulnerability Scanning](https://github.com/OasisLMF/OasisPlatform/actions/workflows/scan.yml/badge.svg?branch=master)](https://github.com/OasisLMF/OasisPlatform/actions/workflows/scan.yml)

# Oasis Platform
Provides core components of the Oasis platform, specifically:
* DJango application that provides the Oasis REST API
* Celery worker for running a model

## First Steps

### Simple environment

A simple environment for the testing the API and worker can be created using Docker compose.

<img src="https://github.com/OasisLMF/OasisPlatform/blob/master/Oasis%20Simple%20Runner.png" alt="Simple Oasis platform test environment"/>

First make sure that you have Docker running. Then build the images for the API server and model execution worker:

    docker build -f Dockerfile.oasis_api_server.base  -t coreoasis/oasis_api_base .
    docker build -f Dockerfile.oasis_api_server.mysql -t coreoasis/oasis_api_server .
    docker build -f Dockerfile.model_execution_worker -t coreoasis/model_execution_worker .

The docker images for the server are structured to all inherit from `oasis_api_server:base`.
Then each child image will be setup for a specific database backend (for example 
`oasis_api_server:mysql` uses mysql as the database backend). 

Start the docker network:

    docker-compose up -d

Check that the server is running:

    curl localhost:8000/healthcheck

(For the Rabbit management application browse to http://localhost:15672, for Flower, the Celery management application, browse to http://localhost:5555.)

To run a test analysis using the worker image and example model data, run the following command:
    
    docker exec oasisplatform_runner_1 sh run_api_test_analysis.sh

### Calling the Server

The API server provides a REST interface which is described on the home page of the api server at 
<a href="http://localhost:8000/" target="_blank">http://localhost:8000/</a>. This documentation
also provides an interactable interface to the api or you can use any command line client such as 
curl. 

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
    
The demo project also needs the PiWind model. This is available [here](https://github.com/OasisLMF/OasisPiWind).
You should also set `OASIS_MODEL_DATA_DIR` to the root directory of the pi wind repo.

### Setup

Once the dependencies have been installed you will need to create the database. For development we use mysql for 
simplicity. To create the database run: 
    
    python manage.py migrate
    
This should also be ran whenever there are new database changes. If you change the database fields you
will need to generate new migrations by running:

    python manage.py makemigrations
    
And adding all generated files to git.

Once the database has been migrated the pi wind model needs to be added to the database, either in the 
admin interface or the api setting:
 
    {
        supplier_id: "OasisIM",
        model_id: "PiWind",
        version_id: "1",
    }

### Running outside of a container 

The server can be run directly in python by `./manage.py runserver`, note that if the server has `debug=false` set (the default value)
then the command `./manage.py collectstatic` must be executed first


### Testing

To test the code style run::

    flake8

To test against all supported python versions run::

    tox

To test against your currently installed version of python run::

    py.test

To run the full test suite run::

    ./runtests.sh

### OIDC and Keycloak

Due to different settings required to enable keycloak they need to be executed with a different django configuration:

    OASIS_API_AUTH_TYPE=keycloak pytest src/server/oasisapi/auth/tests/test_oidc.py

### Deploying

The Oasis CI system builds and deploys the following Docker images to DockerHub:

* <a href="https://hub.docker.com/r/coreoasis/oasis_api_server">coreoasis/oasis_api_server</a>
* <a href="https://hub.docker.com/r/coreoasis/model_execution_worker">coreoasis/model_execution_worker</a>

Note that the Dockerfiles cannot be used directly as there are version stubs that get substitued at build time by the CI system.

## Authentication

By default the server uses the standard model backend, this started users with username and password in
the database. This can be configured by setting `OASIS_API_SERVER_AUTH_BACKEND` to a comma separated 
list of python paths. Information about django authentication backends can be found [here](https://docs.djangoproject.com/en/2.0/topics/auth/customizing/#writing-an-authentication-backend)

To create an admin user call `python manage.py createsuperuser` and follow the prompts, this user
can be used as a normal user on in the api but it also gains access to the admin interface at
http://localhost:8000/admin/. From here you can edit entries and create new users.

For authenticating with the api the `HTTP-AUTHORIZATION` header needs to be set. The token to use can
be obtained by posting your username and password to `/refresh_token/`. This gives you both a refresh
token and access token. The access token should be used for most requests however this will expire after
a while. When it expires a new key can be retrieved by posting to `/access_token/` using the refresh
token in the authorization header. 

The authorization header takes the following form `Bearer <token>`.

## Workflow

The general workflow is as follows

1. Create a portfolio (post to `/portfolios/`).
2. Add a locations file to the portfolio (post to `/portfolios/<id>/locations_file/`)
3. Create the model object for your model (post to `/models/`).
4. Create an analysis (post to `/portfolios/<id>/create_analysis`). This will generate the input files
    for the analysis.
5. Add analysis settings file to the analysis (post to `/analyses/<pk>/analysis_settings/`).
6. Run the analysis (post to `/analyses/<pk>/run/`)
7. Get the outputs (get `/analuses/<pk>/output_file/`) 

## Documentation
* <a href="https://github.com/OasisLMF/OasisApi/issues">Issues</a>
* <a href="https://github.com/OasisLMF/OasisApi/releases">Releases</a>
* <a href="https://oasislmf.github.io">General Oasis documentation</a>
* <a href="https://oasislmf.github.io/docs/oasis_rest_api.html">Oasis API documentation</a>
* <a href="https://oasislmf.github.io/OasisPlatform/modules.html">Oasis Platform module documentation</a>

## License
The code in this project is licensed under BSD 3-clause license.
