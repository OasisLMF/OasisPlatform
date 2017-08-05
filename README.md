`OasisApi`
==========

# Repository Management

## Cloning the repository

You can clone this repository from <a href="https://github.com/OasisLMF/OasisApi" target="_blank">GitHub</a> using HTTPS or SSH, but it is recommended that that you use SSH: first ensure that you have generated an SSH key pair on your local machine and add the public key of that pair to your GitHub account (use the GitHub guide at https://help.github.com/articles/connecting-to-github-with-ssh/). Then run

    git clone --recursive git+ssh://git@github.com/OasisLMF/OasisApi

To clone over HTTPS use

    git clone --recursive https://github.com/OasisLMF/OasisApi

You may receive a password prompt - to bypass the password prompt use

    git clone --recursive https://<GitHub user name:GitHub password>@github.com/OasisLMF/OasisApi

The `--recursive` option ensures the cloned repository contains the necessary Oasis repositories <a href="https://github.com/OasisLMF/oasis_utils" target="_blank">`oasis_utils`</a> and <a href="https://github.com/OasisLMF/OasisAPIClient" target="_blank">`OasisAPIClient`</a> as Git submodules.

## Managing the submodules

Run the command

    git submodule

to list the submodules (latest commit IDs, paths and branches). If any are missing then you can add them using

	git submodule add <submodule GitHub repo URL> <local path/destination>

It is a quirk of Git that the first time you clone a repository with submodules they will be checked out as commits not branches, which is not what you want. You should run the command

    git submodule foreach 'git checkout master'

to ensure that the submodules are checked out on the `master` branches.

If you've already cloned the repository and wish to update the submodules (all at once) in your working directory from their GitHub repositories then run

    git submodule foreach 'git pull origin'

You can also update the submodules individually by pulling from within them.

Unless you've been given read access to this repository on GitHub (via an OasisLMF organizational team) you should not make any local changes to these submodules because you have read-only access to their GitHub repositories. So submodule changes can only propagate from GitHub to your local repository. To detect these changes you can run `git status -uno` and to commit them you can add the paths and commit them in the normal way.

# Sphinx Docs

This repository is enabled with <a href="https://pypi.python.org/pypi/Sphinx" target="_blank">Sphinx</a> documentation for the Python modules, and the documentation is published to <a href="https://oasislmf.github.io/OasisLMF/OasisApi" target="_blank">https://oasislmf.github.io/OasisApi/</a> manually using the procedure described below. (Note: GitHub pages is not enabled for this repository because it contains the private repository <a href="https://github.com/OasisLMF/oasis_utils" target="_blank">`oasis_utils`</a> as a Git submodule, which is incompatible with GitHub pages.)

## Setting up Sphinx

Firstly, to work on the Sphinx docs for this package you must have Sphinx installed on your system or in your virtual environment (`virtualenv` is recommended).

You should also clone the Oasis publication repository <a href="https://github.com/OasisLMF/OasisLMF.github.io" target="_blank">OasisLMF.github.io</a>.

## Building and publishing

The Sphinx documentation source files are reStructuredText files, and are contained in the `docs` subfolder, which also contains the Sphinx configuration file `conf.py` and the `Makefile` for the build. To do a new build make sure you are in the `docs` subfolder and run

    make html

You should see a new set of HTML files and assets in the `_build/html` subfolder (the build directory can be changed to `docs` itself in the `Makefile` but that is not recommended). The `docs` subfolder should always contain the latest copy of the built HTML and assets so first copy the files from `_build/html` to `docs` using

    cp -R _build/html/* .

Add and commit these files to the local repository, and then update the remote repository on GitHub. Then copy the same files to the Oasis API server docs static subfolder in the publication repository

    cp -R _build/html/* /path/to/your/OasisLMF.github.io/OasisApi/

Add and commit the new files in the publication repository, and then update the remote repository on GitHub - GitHub pages will automatically publish the new documents to the documentation site https://oasislmf.github.io/OasisApi/.

# First Steps

## Docker and ktools

First make sure that you have Docker running. Then make sure that the ktools binaries are installed (see <a href="https://github.com/OasisLMF/ktools" target="_blank">ktools</a> GitHub repository for instructions) and the ktools docker image is available (pull from <a href="https://hub.docker.com/r/coreoasis/ktools/" target="_blank">Docker Hub</a>, or build locally from the ktools repository, and name it as `ktools` to match the reference in the `docker-compose.yml`).

Then build the images for the API server, model execution worker and API runner: 

    docker build -f Dockerfile.oasis_api_server -t oasis_api_server .
    docker build -f Dockerfile.model_execution_worker -t model_execution_worker .
    docker build -f Dockerfile.api_runner -t api_runner .

Start the docker network:

    docker-compose up -d

Check that the server is running:

    curl localhost:8001/healthcheck

(For the Rabbit management application browse to http://localhost:15672, for Flower, the celery management application, browse to http://localhost:5555.)

## Calling the Server

The API server provides a REST interface which is described <a href="https://oasislmf.github.io/OasisApi/modules.html" target="_blank">here</a>. You can use any suitable command line client such as `curl` or <a href="www.httpie.org" target="_blank">`httpie`</a> to make individual API calls, but a custom Python client may be a better option - for this you can use the <a href="https://github.com/OasisLMF/OasisAPIClient" target="_blank">`OasisAPIClient`</a> repository.

To run the example API client tester (located in `src/utils`; for a generic Oasis model) first install the Oasis API client requirements

    pip install -r src/oasisapi_client/requirements.py

and then call the tester using

    python ./src/utils/api_tester.py -i localhost:8001 -a tests/data/analysis_settings.json -d tests/data/input -o tests/data/output -n 1 -v

