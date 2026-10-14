#!/usr/bin/python3
"""
Container entrypoint for the api_server image (installed as /usr/local/bin/startup).

Written in python as the hardened runtime image has no shell:
  1. wait for the server db, celery db and broker to accept TCP connections
  2. optionally run migrations (STARTUP_RUN_MIGRATIONS=true), with the Platform 2 fallback
  3. create / update the default admin user (set_default_user.py)
  4. exec the container command, e.g. ./wsgi/run-wsgi.py
"""
import os
import socket
import subprocess
import sys
import time

WAIT_TIMEOUT = 60

# Fallback migration between plat2 (older than 2.2.0) and plat2 (2.2.1+)
# For details see: https://github.com/OasisLMF/OasisPlatform/pull/862
PLAT2_MIGRATION_FALLBACK = [
    # Revert analysis_models
    ['analysis_models', '0004_analysismodel_deleted'],
    ['analysis_models', '0007_modelscalingoptions_worker_count_min', '--fake'],
    # Revert analyses
    ['analyses', '0010_auto_20200224_1213'],
    ['analyses', '0011_auto_20230724_1134', '--fake'],
    # Revert data_files
    ['data_files', '0006_datafile_file_category'],
    ['data_files', '0007_auto_20230724_1134', '--fake'],
    # Revert files
    ['files', '0005_relatedfile_oed_validated'],
    ['files', '0006_relatedfile_groups', '--fake'],
    # Revert portfolios
    ['portfolios', '0002_auto_20190619_1226'],
    ['portfolios', '0003_auto_20230724_1134', '--fake'],
    # ReRun Migrations
    [],
]


def log(msg):
    print(msg, flush=True)


def wait_for(address, timeout=WAIT_TIMEOUT):
    """Wait for 'host:port' to accept a TCP connection (same behaviour as wait-for-it.sh)"""
    parts = address.split(':')
    host, port = parts[0], parts[1] if len(parts) > 1 else ''
    if not host or not port:
        log(f'wait-for-it: Error: you need to provide a host and port to test, got "{address}"')
        sys.exit(1)

    log(f'wait-for-it: waiting {timeout} seconds for {host}:{port}')
    start = time.monotonic()
    while True:
        try:
            with socket.create_connection((host, int(port)), timeout=1):
                log(f'wait-for-it: {host}:{port} is available after {int(time.monotonic() - start)} seconds')
                return
        except OSError:
            if time.monotonic() - start >= timeout:
                log(f'wait-for-it: timeout occurred after waiting {timeout} seconds for {host}:{port}')
                sys.exit(124)
            time.sleep(1)


def manage(*args, **kwargs):
    return subprocess.run([sys.executable, 'manage.py', *args], **kwargs)


def run_migrations():
    exitcode = manage('migrate').returncode
    if exitcode > 0:
        # Apply Platform2 compatibility Migration as fallback
        showmigrations = manage('showmigrations', capture_output=True, text=True).stdout
        if '[ ] 0005_auto_20220510_1103' in showmigrations:
            for migration in PLAT2_MIGRATION_FALLBACK:
                exitcode = manage('migrate', *migration).returncode

    if exitcode > 0:
        sys.exit(exitcode)


def main():
    os.environ['OASIS_API_INI_PATH'] = './conf.ini'

    wait_for(f"{os.environ.get('OASIS_SERVER_DB_HOST', '')}:{os.environ.get('OASIS_SERVER_DB_PORT', '')}")
    wait_for(f"{os.environ.get('OASIS_CELERY_DB_HOST', '')}:{os.environ.get('OASIS_CELERY_DB_PORT', '')}")
    wait_for(os.environ.get('OASIS_CELERY_BROKER_URL', ''))

    if os.environ.get('STARTUP_RUN_MIGRATIONS') == 'true':
        run_migrations()

    # Create default admin if `$OASIS_SERVICE_USERNAME_OR_ID` && `$OASIS_SERVICE_PASSWORD_OR_SECRET` are set
    # These will only be set by the script if "simple" apiAuthType is set.
    # For OIDC, the users are created by the OIDC provider and backend classes.
    exitcode = subprocess.run([sys.executable, 'set_default_user.py']).returncode
    if exitcode > 0:
        sys.exit(exitcode)

    if len(sys.argv) > 1:
        os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == '__main__':
    main()
