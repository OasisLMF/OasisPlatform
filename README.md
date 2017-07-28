# Oasis API

## Cloning the repository

You can clone this repository using HTTPS or SSH, but it is recommended that that you use SSH: first ensure that you have generated an SSH key pair on your local machine and add the public key of that pair to your GitHub account (use the GitHub guide at https://help.github.com/articles/connecting-to-github-with-ssh/). Then run

    git clone --recursive git+ssh://git@github.com/OasisLMF/OasisApi

To clone over HTTPS use

    git clone --recursive https://github.com/OasisLMF/OasisApi.git

You may receive a password prompt - to bypass the password prompt use

    git clone --recursive https://<GitHub user name:GitHub password>@github.com/OasisLMF/OasisApi.git

## Running with Docker

Create images: 
~~~
docker build -t my_server -f Dockerfile.server .
docker build -t my_worker -f Dockerfile.worker .
~~~
Run docker compose:
~~~
  docker-compose up -d
~~~
Check that the server is running:
~~~
  curl localhost:8001/healthcheck
~~~

For the Rabbit management application browse to http://locathost:15672

For Flower, the celery management application, browse to http://locathost:5555

Note that ktools must be installed and the ktools docker image available. To create the ktools docker image, run the following command in the ktools base directory:
~~~
  sudo docker build -t ktools -f Dockerfile.ktools .
~~~

To run the API client tester, run the following commands.
~~~
pip install -r src/client/requirements.py
python tests/ApiTester.py --url http://127.0.0.1:8001
~~~
