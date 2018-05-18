import shutil
import argparse
import os
import time
from subprocess import Popen

parser = argparse.ArgumentParser(description='Build and publish Oasis ARA.')
parser.add_argument(
    '-g', '--github_uname', metavar='N', type=str, required=True,
    help='The username for GitHub.')
parser.add_argument(
    '-G', '--github_password', metavar='N', type=str, required=True,
    help='The password for GitHub.')
parser.add_argument(
    '-d', '--docker_uname', type=str, default='',
    help="The username for DockerHub.")
parser.add_argument(
    '-D', '--docker_password', type=str, default='',
    help="The password for DockerHub.")
parser.add_argument(
    '-r', '--release_tag', type=str, default='',
    help="The release tag.")
parser.add_argument(
    '-b', '--build', action='store_true',
    help='Checkout of github and build.')
parser.add_argument(
    '-c', '--clean', action='store_true',
    help='Clean all Docker images and containers.')
parser.add_argument(
    '-p', '--publish', action='store_true',
    help='Publish to DockerHub.')
parser.add_argument(
    '-t', '--integration_tests', action='store_true',
    help='Run integration tests.')

args = parser.parse_args()

github_uname = args.github_uname
github_password = args.github_password
docker_uname = args.docker_uname
docker_password = args.docker_password
release_tag = args.release_tag
do_clean_docker = args.clean
do_publish = args.publish
do_integration_tests = args.integration_tests
do_build = args.build

do_github_tags = True
do_docker_tags = True


def run_command(desc, cmd, exit_on_fail=True, retry=False):
    proc = Popen(cmd, shell=True)
    proc.wait()
    if (proc.returncode > 0 and exit_on_fail):
        print("FAIL: {}".format(desc))
        if retry:
            print("RETRY: {}".format(desc))
            run_command(desc, cmd, True, False)
        else:
            exit(255)


if do_clean_docker:
    run_command(
        "Stop all running docker containers",
        "docker ps -aq | xargs docker rm -f", False)

    # run_command(
    #     "Delete all docker images",
    #     "docker images -q | xargs docker rmi -f", False)

    run_command(
        "Remove existing directories",
        "rm -rf ktools; rm -rf oasisapi; rm -rf ara")

    run_command(
        "Clone ktools",
        "git clone --recursive https://{}:{}@github.com/oasislmf/ktools".format(
            github_uname, github_password))

    run_command(
        "Clone oasisapi",
        "git clone --recursive https://{}:{}@github.com/oasislmf/oasisapi".format(
            github_uname, github_password))

if do_build:

    os.chdir("ktools")
    run_command(
        "Build ktools image",
        "docker build --no-cache=true -t ktools -f Dockerfile.ktools .")

    if do_github_tags:
        run_command(
            "Tag ktools repo",
            "git tag -f {}".format(release_tag))
        run_command(
            "Push ktools tag",
            "git push origin {}".format(release_tag))

    os.chdir("..")

    os.chdir("oasisapi")
    run_command(
        "Build oasis_api_server image",
        "docker build --no-cache=true -t oasis_api_server -f Dockerfile.oasis_api_server .")
    run_command(
        "Build model_execution_worker image",
        "docker build --no-cache=true -t model_execution_worker -f Dockerfile.model_execution_worker .")
    run_command(
        "Build api_runner image",
        "docker build --no-cache=true -t api_runner -f Dockerfile.api_runner .")
    run_command(
        "Build test_env image",
        "docker build --no-cache=true -t test_env -f Dockerfile.test_env .")
    if do_github_tags:
        run_command(
            "Tag oasisapi repo",
            "git tag -f {}".format(release_tag))
        run_command(
            "Push oasisapi tag",
            "git push origin {}".format(release_tag))

    os.chdir("..")

run_command(
    "Tag oasis_api_server image",
    "docker tag oasis_api_server coreoasis/oasis_api_server:{}".format(release_tag))
run_command(
    "Tag api_runner image",
    "docker tag api_runner coreoasis/api_runner:{}".format(release_tag))
run_command(
    "Tag model_execution_worker image",
    "docker tag model_execution_worker coreoasis/model_execution_worker:{}".format(release_tag))
run_command(
    "Tag test_env image",
    "docker tag test_env coreoasis/test_env:{}".format(release_tag))

if do_publish:
    run_command(
        "Login to DockerHub",
        "docker login -p {} -u {}".format(docker_password, docker_uname),
        True)
    run_command(
        "Push oasis_api_server to DockerHub",
        "docker push coreoasis/oasis_api_server:{}".format(release_tag),
        True)
    run_command(
        "Push api_runner to DockerHub",
        "docker push coreoasis/api_runner:{}".format(release_tag),
        True)
    run_command(
        "Push model_execution_worker to DockerHub",
        "docker push coreoasis/model_execution_worker:{}".format(release_tag),
        True)
    run_command(
        "Push test_env to DockerHub",
        "docker push coreoasis/test_env:{}".format(release_tag),
        True)

# Create the docker-compose file
shutil.copyfile("docker-compose.yml", "./docker-compose:{}.yml".format(release_tag))
run_command(
    "Update docker-compose with release tag",
    "sed -i -e s/RELEASE_TAG/{}/g docker-compose:{}.yml".format(release_tag, release_tag))

if do_integration_tests:
    run_command(
        "Start docker images",
        "docker-compose -f docker-compose:{}.yml up -d".format(release_tag))
    time.sleep(5)
    run_command(
        "Run integration tests",
        "docker exec build_runner_1 sh run_api_test_analysis.sh")
