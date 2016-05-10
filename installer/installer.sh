echo installer starting ... > InstallerLogger

apt-get -y -qq update

for i in dos2unix apache2 libapache2-mod-wsgi python-pip git rabbitmq-server python-flask
do
  package=$i
  apt-get -y -qq install $i     
  dpkg-query -W -f='${Package}: ${Status} - ${Version}\n' $i >> InstallerLogger
done

for i in celery flask-swagger # Flask django django-adminfiles djangorestframework
do
  pip install -U $i
  echo $i >> InstallerLogger
done

echo installer completed ... >> InstallerLogger
