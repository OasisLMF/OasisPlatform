pkg_list=(
    'celery==5.*'
    'django==3.*'
    azure-storage-blob
    coverage
    cryptography
    distlib
    django-celery-results
    django-request-logging
    drf-yasg
    filelock
    joblib
    numpy
    oasislmf
    pytest
    oauthlib
    ods-tools
    pandas
    parso
    pyopenssl
    psycopg2-binary
    ruamel.yaml
    scikit-learn
    scipy
    sklearn
    sqlalchemy
    text-unidecode
    virtualenv
    waitress
)

PKG_UPDATE=''
for pk in "${pkg_list[@]}"; do
    PKG_UPDATE=$PKG_UPDATE" --upgrade-package $pk"
done

rm requirements-worker.txt requirements-server.txt requirements.txt
set -e
pip-compile $PKG_UPDATE requirements-worker.in
pip-compile $PKG_UPDATE requirements-server.in
pip-compile $PKG_UPDATE requirements.in
