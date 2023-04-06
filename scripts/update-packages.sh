pkg_list=(
    'ods-tools==3.*'
    'oasislmf==1.27.*'
    'pandas==1.*'
    joblib
    cryptography
    oauthlib
    parso
    certifi
    wheel
    ruamel.yaml
    distlib
    'sqlalchemy==1.*'
    'django==3.*'
    django-celery-results
    'celery==5.*'
    virtualenv
    filelock
    text-unidecode
    azure-storage-blob
    coverage
    django-request-logging
    drf-yasg
    scipy
    waitress
    sklearn
    psycopg2-binary
    scikit-learn
)


PKG_UPDATE=''
for pk in "${pkg_list[@]}"; do
    PKG_UPDATE=$PKG_UPDATE" --upgrade-package $pk"
done

set -e
pip-compile $PKG_UPDATE requirements-worker.in
pip-compile $PKG_UPDATE requirements-server.in
pip-compile $PKG_UPDATE requirements.in
