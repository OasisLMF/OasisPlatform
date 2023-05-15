#pkg_list=(
#    'oasislmf==1.15.*'
#    joblib
#    oauthlib
#    parso
#    certifi
#    cryptography
#    wheel
#    ruamel.yaml
#    distlib
#    'sqlalchemy==1.*'
#    'django==3.*'
#    django-celery-results
#    'celery==5.*'
#    virtualenv
#    filelock
#    text-unidecode
#    azure-storage-blob
#    coverage
#    django-request-logging
#    drf-yasg
#    scipy
#    waitress
#    sklearn
#    psycopg2-binary
#    scikit-learn
#)


pkg_list=(
    'oasislmf==1.15.*'
    'django==3.*'
    'celery==5.*'
    certifi
    cookiecutter
    'cryptography==3.3.*'
    #'cryptography==39.*'
    future
    ipython
    py
    pygments
    pyjwt
    sqlparse
    urllib3
    waitress
)


PKG_UPDATE=''
for pk in "${pkg_list[@]}"; do
    PKG_UPDATE=$PKG_UPDATE" --upgrade-package $pk"   
done

#rm requirements-worker.txt requirements-server.txt requirements.txt
set -e
pip-compile $PKG_UPDATE requirements-worker.in
pip-compile $PKG_UPDATE requirements-server.in
pip-compile $PKG_UPDATE requirements.in
