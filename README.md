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
  docker-compose up
~~~
Check that the server is running:
~~~
  curl localhost:8001/healthcheck
~~~

For the Rabbit management application browse to http://locathost:15672

For Flower, the celery management application, browse to http://locathost:5555
