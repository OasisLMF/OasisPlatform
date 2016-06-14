# Oasis API

Running with Docker
-------------------

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

To run the API client tester, run the following commands. Note that Xtools must be installed.
~~~
pip install -r src/cleint/requirements.py
python tests/ApiTester.py --url http://127.0.0.1:8001
~~~
