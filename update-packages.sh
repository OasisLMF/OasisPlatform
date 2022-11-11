pkg_list=(
    sqlalchemy
    joblib
    oauthlib
    parso
    #pandas
    ruamel.yaml
    distlib
    ods-tools
    'oasislmf==1.23.*'
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
    #numpy
    scipy
    waitress
    sklearn
    psycopg2-binary
    scikit-learn
)


for pk in "${pkg_list[@]}"; do
    pip-compile --upgrade-package $pk requirements-worker.in
    pip-compile --upgrade-package $pk requirements-server.in
    pip-compile --upgrade-package $pk requirements.in

#    if [[ `git status --porcelain --untracked-files=no` ]]; then
#        echo "$pk - updated"
#        git add -u
#        git commit -m "Updated package $pk"
#    else 
#        echo "$pk - no update found"
#    fi     
done 

