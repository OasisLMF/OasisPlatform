//JOB TEMPLATE
def createStage(stage_name, stage_params, propagate_flag) {
    return {
        stage("Test: ${stage_name}") {
            build job: "${stage_name}", parameters: stage_params, propagate: propagate_flag
        }
    }
}

// LIST of default models sub-jobs to trigger as part of regression testing
def model_regression_list = """
oasis_PiWind/develop
GemFoundation_GMO/master
corelogic_quake/develop
"""

node {
    hasFailed = false
    sh 'sudo /var/lib/jenkins/jenkins-chown'
    deleteDir() // wipe out the workspace

    // Check if this is an LTS branch
    if (BRANCH_NAME.matches("backports/(.*)")) {
        default_branch=BRANCH_NAME
        is_lts_branch = true
    } else {
        default_branch = 'develop'
        is_lts_branch = false
    }

    properties([
      parameters([
        [$class: 'StringParameterDefinition',  description: "Oasis Build scripts branch",          name: 'BUILD_BRANCH', defaultValue: 'master'],
        [$class: 'StringParameterDefinition',  description: "OasisPlatform branch",                name: 'PLATFORM_BRANCH', defaultValue: BRANCH_NAME],
        [$class: 'StringParameterDefinition',  description: "Install OasisLMF from branch",        name: 'MDK_BRANCH', defaultValue: default_branch],
        [$class: 'StringParameterDefinition',  description: "Test API/Worker using PiWind branch", name: 'PIWIND_BRANCH', defaultValue: default_branch],
        [$class: 'StringParameterDefinition',  description: "Release tag to publish",              name: 'RELEASE_TAG', defaultValue: BRANCH_NAME.split('/').last() + "-${BUILD_NUMBER}"],
        [$class: 'StringParameterDefinition',  description: "Last release, for changelog",         name: 'PREV_RELEASE_TAG', defaultValue: ""],
        [$class: 'StringParameterDefinition',  description: "OasisLMF release notes ref",          name: 'OASISLMF_TAG', defaultValue: ""],
        [$class: 'StringParameterDefinition',  description: "OasisLMF prev release notes ref",     name: 'OASISLMF_PREV_TAG', defaultValue: ""],
        [$class: 'StringParameterDefinition',  description: "Ktools release notes ref",            name: 'KTOOLS_TAG', defaultValue: ""],
        [$class: 'StringParameterDefinition',  description: "Ktools prev release notes ref",       name: 'KTOOLS_PREV_TAG', defaultValue: ""],
        [$class: 'StringParameterDefinition',  description: "CVE Rating that fails a build",       name: 'SCAN_IMAGE_VULNERABILITIES', defaultValue: "HIGH,CRITICAL"],
        [$class: 'StringParameterDefinition',  description: "CVE Rating that fails a build",       name: 'SCAN_REPO_VULNERABILITIES', defaultValue: "CRITICAL"],
        [$class: 'TextParameterDefinition',    description: "List of models for Regression tests", name: 'MODEL_REGRESSION', defaultValue: model_regression_list],
        [$class: 'BooleanParameterDefinition', description: "Test previous API and Worker",        name: 'CHECK_COMPATIBILITY', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', description: "Test S3 storage using LocalStack",    name: 'CHECK_S3', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', description: "Run API unittests",                   name: 'UNITTEST', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', description: "Run Regression checks",               name: 'RUN_REGRESSION', defaultValue: Boolean.valueOf(false)],
        [$class: 'BooleanParameterDefinition', description: "Purge docker images on completion",   name: 'PURGE', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', description: "Create release if checked",           name: 'PUBLISH', defaultValue: Boolean.valueOf(false)],
        [$class: 'BooleanParameterDefinition', description: "Mark as pre-released software",       name: 'PRE_RELEASE', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', description: "Perform a gitflow merge",             name: 'AUTO_MERGE', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', description: "Send build status to slack",          name: 'SLACK_MESSAGE', defaultValue: Boolean.valueOf(true)]
      ])
    ])

    // Build vars
    String build_repo = 'git@github.com:OasisLMF/build.git'
    String build_branch = params.BUILD_BRANCH
    String build_workspace = 'oasis_build'

    // docker vars (main)
    String docker_api    = "Dockerfile.api_server"
    String docker_worker = "Dockerfile.model_worker"
    String docker_worker_debian = "Dockerfile.model_worker_debian"
    String docker_piwind = "docker/Dockerfile.piwind_worker"

    String image_api     = "coreoasis/api_server"
    String image_worker  = "coreoasis/model_worker"
    String image_piwind  = "coreoasis/piwind_worker"

    // docker vars (slim)
    //String docker_api_slim    = "docker/Dockerfile.api_server_alpine"
    String docker_worker_slim = "docker/Dockerfile.model_worker_slim"

    // platform vars
    String oasis_branch    = params.PLATFORM_BRANCH  // Git repo branch to build from
    String mdk_branch      = params.MDK_BRANCH
    String oasis_name      = 'OasisPlatform'
    String oasis_git_url   = "git@github.com:OasisLMF/${oasis_name}.git"
    String oasis_workspace = 'platform_workspace'
    String utils_sh        = '/buildscript/utils.sh'
    String oasis_func      = "oasis_server"

    // oasis base model test
    String model_branch     = params.PIWIND_BRANCH
    String model_name       = 'OasisPiWind'
    String model_tests      = 'control_set'
    String model_workspace  = "${model_name}_workspace"
    String model_git_url    = "git@github.com:OasisLMF/${model_name}.git"
    String model_test_dir  = "${env.WORKSPACE}/${model_workspace}/tests/"
    String model_test_ini  = "test-config.ini"
    String RELEASE_NUM_ONLY = ""

    String script_dir = env.WORKSPACE + "/${build_workspace}"
    String git_creds  = "1335b248-336a-47a9-b0f6-9f7314d6f1f4"
    String PIPELINE   = script_dir + "/buildscript/pipeline.sh"

    // Docker image scanning
    String mnt_docker_socket = "-v /var/run/docker.sock:/var/run/docker.sock"
    String mnt_output_report = "-v ${env.WORKSPACE}/${oasis_workspace}/image_reports:/tmp"
    String mnt_scan_report = "-v ${env.WORKSPACE}/${oasis_workspace}/scan_reports:/tmp"
    String mnt_repo = "-v ${env.WORKSPACE}/${oasis_workspace}:/mnt"
    String mnt_server_deps = "-v ${env.WORKSPACE}/${oasis_workspace}/requirements-server.txt:/mnt/requirements.txt"
    String mnt_worker_deps = "-v ${env.WORKSPACE}/${oasis_workspace}/requirements-worker.txt:/mnt/requirements.txt"

    // Update MDK branch based on model branch
    if (BRANCH_NAME.matches("master") || BRANCH_NAME.matches("hotfix/(.*)")){
        MDK_BRANCH='master'
        MODEL_BRANCH='master'
    }

    //make sure release candidate versions are tagged correctly
    if (params.PUBLISH && params.PRE_RELEASE && ! params.RELEASE_TAG.matches('^(\\d+\\.)(\\d+\\.)(\\*|\\d+)rc(\\d+)$')) {
        sh "echo release candidates must be tagged {version}rc{N}, example: 1.0.0rc1"
        sh "exit 1"
    }


    if (is_lts_branch){
        //Make sure releases are tagged as LTS
        if (params.PUBLISH &&  ! params.PRE_RELEASE && ! params.RELEASE_TAG.matches('^(\\d+\\.)(\\d+\\.)(\\*|\\d+)-lts')) {
            sh "echo release candidates must be tagged {version}-lts, example: 1.0.0-lts"
            sh "exit 1"
        }

        if (params.PUBLISH && params.RELEASE_TAG.matches('^(\\d+\\.)(\\d+\\.)(\\*|\\d+)-lts')){
            RELEASE_NUM_ONLY = ( params.RELEASE_TAG =~ '^(\\d+\\.)(\\d+\\.)(\\*|\\d+)' )[0][0]
        }
    }

    // Set Global ENV
    env.PIPELINE_LOAD = script_dir + utils_sh

    env.OASIS_MODEL_DATA_DIR = "${env.WORKSPACE}/${model_workspace}"
    //env.TAG_BASE             = params.BASE_TAG     //Build TAG for base set of images
    env.TAG_RELEASE          = params.RELEASE_TAG  //Build TAG for TARGET image
    env.TAG_RUN_PLATFORM     = params.RELEASE_TAG
    env.TAG_RUN_WORKER       = params.RELEASE_TAG
    env.COMPOSE_PROJECT_NAME = UUID.randomUUID().toString().replaceAll("-","")

    env.IMAGE_WORKER   = image_piwind
    // Should read these values from test/conf.ini
    env.TEST_MAX_RUNTIME = '190'
    env.TEST_DATA_DIR = model_test_dir
    env.MDK_CONFIG = '/home/worker/model/oasislmf.json'
    env.MODEL_SUPPLIER = 'OasisLMF'
    env.MODEL_VARIENT  = 'PiWind'
    env.MODEL_ID       = '1'
    sh 'env'


    // Param Publish Guards
    if (params.PUBLISH && ! ( oasis_branch.matches("release/(.*)") || oasis_branch.matches("hotfix/(.*)") || oasis_branch.matches("backports/(.*)")) ){
        println("Publish Only allowed on a release/* or hotfix/* branches")
        sh "exit 1"
    }

    try {
        parallel(
            clone_oasis_build: {
                stage('Clone: ' + build_workspace) {
                    dir(build_workspace) {
                       git url: build_repo, credentialsId: git_creds, branch: build_branch
                    }
                }
            },
            clone_oasis_model: {
                stage('Clone: ' + model_workspace) {
                    dir(model_workspace) {
                       git url: model_git_url, credentialsId: git_creds, branch: model_branch
                    }
                }
            },
            clone_oasis_platform: {
                stage('Clone: ' + oasis_func) {
                    sshagent (credentials: [git_creds]) {
                        dir(oasis_workspace) {
                            sh "git clone --recursive ${oasis_git_url} ."
                            if (oasis_branch.matches("PR-[0-9]+")){
                                // Checkout PR and merge into target branch, test on the result
                                sh "git fetch origin pull/$CHANGE_ID/head:$BRANCH_NAME"
                                sh "git checkout $CHANGE_TARGET"
                                sh "git merge $BRANCH_NAME"
                            } else {
                                // Checkout branch
                                sh "git checkout ${oasis_branch}"
                            }
                        }
                    }
                }
            }
        )

        if (params.SCAN_REPO_VULNERABILITIES){
            parallel(
                scan_platform_repo: {
                    stage('Scan: repo config') {
                        dir(oasis_workspace) {
                            withCredentials([string(credentialsId: 'github-tkn-read', variable: 'gh_token')]) {
                                sh "docker run -e GITHUB_TOKEN=${gh_token} ${mnt_repo} ${mnt_scan_report} aquasec/trivy fs --exit-code 1 --severity ${params.SCAN_REPO_VULNERABILITIES} --output /tmp/cve_repo_general.txt  --security-checks vuln,config,secret /mnt"
                            }
                        }
                    }
                },
                scan_server_deps: {
                    stage('Scan: requirments-server.txt') {
                        dir(oasis_workspace) {
                            withCredentials([string(credentialsId: 'github-tkn-read', variable: 'gh_token')]) {
                                sh "docker run -e GITHUB_TOKEN=${gh_token} ${mnt_server_deps} ${mnt_scan_report} aquasec/trivy fs --exit-code 1 --severity ${params.SCAN_REPO_VULNERABILITIES} --output /tmp/cve_python_server.txt /mnt/requirements.txt"
                            }
                        }
                    }
                },
                scan_worker_deps: {
                    stage('Scan: requirments-worker.txt') {
                        dir(oasis_workspace) {
                            withCredentials([string(credentialsId: 'github-tkn-read', variable: 'gh_token')]) {
                                sh "docker run -e GITHUB_TOKEN=${gh_token} ${mnt_worker_deps} ${mnt_scan_report} aquasec/trivy fs --exit-code 1 --severity ${params.SCAN_REPO_VULNERABILITIES} --output /tmp/cve_python_worker.txt /mnt/requirements.txt"
                            }
                        }
                    }
                }
            )
        }

        stage('Shell Env'){
            sh  PIPELINE + ' print_model_vars'
            if (params.CHECK_COMPATIBILITY) {
                dir(oasis_workspace) {
                    if (params.PREV_RELEASE_TAG){
                        env.LAST_RELEASE_TAG = params.PREV_RELEASE_TAG
                    } else {
                        sh "curl https://api.github.com/repos/OasisLMF/OasisPlatform/releases | jq -r '( first ) | .name' > last_release_tag"
                        env.LAST_RELEASE_TAG = readFile('last_release_tag').trim()
                    }
                    println("LAST_RELEASE = $env.LAST_RELEASE_TAG")
                }
            }
        }
        if (mdk_branch && ! params.PUBLISH){
            stage('Git install MDK'){
                dir(oasis_workspace) {
                    // update worker and server install lists
                    sh "sed -i 's|^oasislmf.*| git+https://github.com/OasisLMF/OasisLMF.git@${mdk_branch}#egg=oasislmf[extra]|g' requirements-worker.txt"
                    sh "sed -i 's|^oasislmf.*| git+https://github.com/OasisLMF/OasisLMF.git@${mdk_branch}#egg=oasislmf[extra]|g' requirements.txt"
                }
            }
        }
        stage('Set version'){
            dir(oasis_workspace){
                sh "echo ${env.TAG_RELEASE} - " + '$(git rev-parse --short HEAD), $(date) > VERSION'
            }
            println("Publishing images as: '${RELEASE_NUM_ONLY}', '${params.RELEASE_TAG}' and  'latest-lts'")
        }
        parallel(
            build_api_server: {
                stage('Build: API server') {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_api} ${image_api} ${env.TAG_RELEASE}"

                    }
                }
            },
            build_model_worker_ubuntu: {
                stage('Build: Model worker - Ubuntu') {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_worker} ${image_worker} ${env.TAG_RELEASE}"
                    }
                }
            },
            build_model_worker_debian: {
                stage('Build: Model worker - Debian') {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_worker_debian} ${image_worker} ${env.TAG_RELEASE}-debian"
                    }
                }
            }
        )
        if(params.PUBLISH){
            // Build chanagelog image
            stage("Create Changelog builder") {
                dir(build_workspace) {
                    sh "docker build -f docker/Dockerfile.release-notes -t release-builder ."
                }
            }
        }

        if (params.SCAN_IMAGE_VULNERABILITIES.replaceAll(" \\s","")){
            parallel(
                scan_api_server: {
                    stage('Scan: API server'){
                        dir(oasis_workspace) {
                            // Scan for Image Efficient
                            sh " ./imagesize.sh  ${image_api}:${env.TAG_RELEASE} image_reports/size_api-server.txt"

                            // Scan for CVE
                            withCredentials([string(credentialsId: 'github-tkn-read', variable: 'gh_token')]) {
                                sh "docker run -e GITHUB_TOKEN=${gh_token} ${mnt_docker_socket} ${mnt_output_report} aquasec/trivy image --exit-code 1 --severity ${params.SCAN_IMAGE_VULNERABILITIES} --output /tmp/cve_api-server.txt ${image_api}:${env.TAG_RELEASE}"
                            }
                        }
                    }
                },
                scan_model_worker: {
                    stage('Scan: Model worker'){
                        dir(oasis_workspace) {
                            // Scan for Image Efficient
                            sh " ./imagesize.sh  ${image_worker}:${env.TAG_RELEASE} image_reports/size_model-worker.txt"

                            // Scan for CVE
                            withCredentials([string(credentialsId: 'github-tkn-read', variable: 'gh_token')]) {
                                sh "docker run -e GITHUB_TOKEN=${gh_token} ${mnt_docker_socket} ${mnt_output_report} aquasec/trivy image --exit-code 1 --severity ${params.SCAN_IMAGE_VULNERABILITIES} --output /tmp/cve_model-worker.txt ${image_worker}:${env.TAG_RELEASE}"
                            }
                        }
                    }
                },
                scan_model_worker_deb: {
                    stage('Scan: Debian Model worker'){
                        dir(oasis_workspace) {
                            // Scan for Image Efficient
                            sh " ./imagesize.sh  ${image_worker}:${env.TAG_RELEASE} image_reports/size_model-worker-deb.txt"

                            // Scan for CVE
                            withCredentials([string(credentialsId: 'github-tkn-read', variable: 'gh_token')]) {
                                sh "docker run -e GITHUB_TOKEN=${gh_token} ${mnt_docker_socket} ${mnt_output_report} aquasec/trivy image --output /tmp/cve_model-worker-deb.txt ${image_worker}:${env.TAG_RELEASE}-debian"
                                //sh "docker run -e GITHUB_TOKEN=${gh_token} ${mnt_docker_socket} aquasec/trivy image --exit-code 1 --severity ${params.SCAN_IMAGE_VULNERABILITIES} ${image_worker}:${env.TAG_RELEASE}-debian"
                            }
                        }
                    }
                }
            )
        }
        if (params.UNITTEST){
            stage('Run: unittest') {
                dir(oasis_workspace) {
                    sh " ./runtests.sh"
                }
            }
            stage('Run: Test API schema') {
                dir(oasis_workspace) {
                    sh " ./build-maven.sh ${env.TAG_RELEASE}"
                }
            }
        }

       if (params.CHECK_S3 || params.CHECK_COMPATIBILITY) {
            // Build PiWind worker from new worker
            stage('Build: PiWind worker') {
                dir(model_workspace) {
                    sh "docker build --build-arg worker_ver=${env.TAG_RELEASE} -f ${docker_piwind} -t ${image_piwind}:${env.TAG_RELEASE} ."
                }
            }
       }

       if (params.CHECK_COMPATIBILITY) {

            // START API for base model tests
            stage('Run: API Server') {
                dir(build_workspace) {
                    sh PIPELINE + " start_model"
                }
            }

            // RUN and test piwind
            api_server_tests = model_tests.split()
            for(int i=0; i < api_server_tests.size(); i++) {
                stage("Run : ${api_server_tests[i]}"){
                    dir(build_workspace) {
                       sh PIPELINE + " run_test --config /var/oasis/test/${model_test_ini} --test-case ${api_server_tests[i]}"

                       // show docker logs
                       sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs server'
                       sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker'
                       sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker-monitor'
                    }
                }
            }

           // CHECK last release compatibility
           stage("Compatibility with worker:${env.LAST_RELEASE_TAG}") {
               dir(build_workspace) {
                   // Set tags
                   env.IMAGE_WORKER = image_worker
                   env.TAG_RUN_PLATFORM = params.RELEASE_TAG
                   env.TAG_RUN_WORKER = env.LAST_RELEASE_TAG

                   // Setup containers
                   sh PIPELINE + " start_model"

                   // run test
                    sh PIPELINE + " run_test --config /var/oasis/test/${model_test_ini} --test-case ${api_server_tests[0]}"

                   // show docker logs
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs server'
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker'
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker-monitor'
               }
           }
           stage("Compatibility with server:${env.LAST_RELEASE_TAG}") {
               dir(build_workspace) {
                   // reset db-data
                   sh PIPELINE + " stop_docker ${env.COMPOSE_PROJECT_NAME}"
                   env.OASIS_DOCKER_DB_DATA_DIR = './db-data_pre-ver'

                   // Set tags
                   env.IMAGE_WORKER = image_worker
                   env.TAG_RUN_PLATFORM = env.LAST_RELEASE_TAG
                   env.TAG_RUN_WORKER = params.RELEASE_TAG

                   // Setup containers
                   sh PIPELINE + " start_model"

                   // run test
                   sh PIPELINE + " run_test --config /var/oasis/test/${model_test_ini} --test-case ${api_server_tests[0]}"

                   // show docker logs
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs server'
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker'
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker-monitor'
               }
           }
       }

       if (params.CHECK_S3) {
           stage("Check S3 storage"){
               dir(build_workspace) {
                   // Stop prev
                   if (params.CHECK_COMPATIBILITY) {
                       sh PIPELINE + " stop_docker ${env.COMPOSE_PROJECT_NAME}"
                   }

                   // Start S3 compose files
                   sh PIPELINE + " start_model_s3"

                   // Reset tags
                   env.IMAGE_WORKER = image_worker
                   env.TAG_RUN_PLATFORM = params.RELEASE_TAG
                   env.TAG_RUN_WORKER = params.RELEASE_TAG

                   // run test
                   sh PIPELINE + " run_test_s3 --config /var/oasis/test/${model_test_ini} --test-case ${model_tests}"

                   // show docker logs
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs server'
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker'
                   sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker-monitor'
               }
           }
       }
       if (params.RUN_REGRESSION) {
           // RUN model regression tests
           job_params = [
                [$class: 'StringParameterValue',  name: 'TAG_OASIS', value: params.RELEASE_TAG]
           ]
            //RUN SEQUENTIAL JOBS -  Fail on error
            if (params.MODEL_REGRESSION){
                jobs_sequential = params.MODEL_REGRESSION.split()
                for (pipeline in jobs_sequential){
                    createStage(pipeline, job_params, true).call()
                }
            }
            /*
            //RUN PARALLEL JOBS
            if (params.MODEL_REGRESSION){
                jobs_parallel   = params.MODEL_REGRESSION.split()
                parallel jobs_parallel.collectEntries {
                    ["${it}": createStage(it, job_params, true)]
                }
            }

            //RUN SEQUENTIAL JOBS - Continue on error
            if (params.SEQUENTIAL_JOB_LIST_NOFAIL){
                jobs_sequential = params.SEQUENTIAL_JOB_LIST_NOFAIL.split()
                for (pipeline in jobs_sequential){
                    createStage(pipeline, job_params, false).call()
                }
            }
            **/
       }

        if(params.PUBLISH){
            // Tag OasisPlatform / PiWind
            stage("Tag release") {
                sshagent (credentials: [git_creds]) {
                    dir(model_workspace) {
                        // Tag PiWind
                        sh PIPELINE + " git_tag ${env.TAG_RELEASE}"
                    }
                    dir(oasis_workspace) {
                        // Tag the OasisPlatform
                        sh PIPELINE + " git_tag ${env.TAG_RELEASE}"
                    }
                }
            }

            // Create release notes
            stage('Create Changelog'){
                dir(oasis_workspace){
                    withCredentials([string(credentialsId: 'github-api-token', variable: 'gh_token')]) {
                        sh "docker run -v ${env.WORKSPACE}/${oasis_workspace}:/tmp release-builder build-changelog --repo OasisPlatform --from-tag ${params.PREV_RELEASE_TAG} --to-tag ${params.RELEASE_TAG} --github-token ${gh_token} --local-repo-path ./ --output-path ./CHANGELOG.rst --apply-milestone"
                        sh "docker run -v ${env.WORKSPACE}/${oasis_workspace}:/tmp release-builder build-release-platform --platform-from-tag ${params.PREV_RELEASE_TAG} --platform-to-tag ${params.RELEASE_TAG} --lmf-from-tag ${params.OASISLMF_PREV_TAG} --lmf-to-tag ${params.OASISLMF_TAG} --ktools-from-tag ${params.KTOOLS_PREV_TAG} --ktools-to-tag ${params.KTOOLS_TAG} --github-token ${gh_token} --output-path ./RELEASE.md"
                    }
                    sshagent (credentials: [git_creds]) {
                        sh "git add ./CHANGELOG.rst"
                        sh "git commit -m 'Update changelog ${params.RELEASE_TAG}'"
                        sh "git push"
                    }
                }
            }
            stage ('Create Release: GitHub') {
                // Create Release
                withCredentials([string(credentialsId: 'github-api-token', variable: 'gh_token')]) {
                    dir(oasis_workspace) {
                        String repo = "OasisLMF/OasisPlatform"
                        def release_body = readFile(file: "${env.WORKSPACE}/${oasis_workspace}/RELEASE.md")
                        def json_request = readJSON text: '{}'
                        json_request['tag_name'] = RELEASE_TAG
                        json_request['target_commitish'] = 'master'
                        json_request['name'] = RELEASE_TAG
                        json_request['body'] = release_body
                        json_request['draft'] = false
                        json_request['prerelease'] = params.PRE_RELEASE
                        writeJSON file: 'gh_request.json', json: json_request
                        sh 'curl -XPOST -H "Authorization:token ' + gh_token + "\" --data @gh_request.json https://api.github.com/repos/$repo/releases > gh_response.json"

                        // Fetch release ID and post json schema
                        def response = readJSON file: "gh_response.json"
                        release_id = response['id']
                        dir('reports') {
                            filename='openapi-schema.json'
                            sh 'curl -XPOST -H "Authorization:token ' + gh_token + '" -H "Content-Type:application/octet-stream" --data-binary @' + filename + " https://uploads.github.com/repos/$repo/releases/$release_id/assets?name=" + "openapi-schema-${RELEASE_TAG}.json"
                        }
                    }
                }
            }
            parallel(
                publish_api_server: {
                    stage ('Publish: api_server') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_api} ${env.TAG_RELEASE}"

                            if (is_lts_branch) {
                                // Publish image as LTS release
                                sh "docker tag ${image_api}:${env.TAG_RELEASE} ${image_api}:latest-lts"
                                sh "docker tag ${image_api}:${env.TAG_RELEASE} ${image_api}:${RELEASE_NUM_ONLY}"

                                sh "docker push ${image_api}:latest-lts"
                                sh "docker push ${image_api}:${RELEASE_NUM_ONLY}"
                            } else {
                                // Update latest tag for Monthly release
                                if (! params.PRE_RELEASE){
                                    sh PIPELINE + " push_image ${image_api} latest"
                                }
                            }
                        }
                    }
                },
                publish_model_worker: {
                    stage('Publish: model_worker') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_worker} ${env.TAG_RELEASE}-debian"
                            sh PIPELINE + " push_image ${image_worker} ${env.TAG_RELEASE}"

                            if (is_lts_branch) {
                                // Publish image as LTS release
                                sh "docker tag ${image_worker}:${env.TAG_RELEASE} ${image_worker}:latest-lts"
                                sh "docker tag ${image_worker}:${env.TAG_RELEASE} ${image_worker}:${RELEASE_NUM_ONLY}"
                                sh "docker push ${image_worker}:latest-lts"
                                sh "docker push ${image_worker}:${RELEASE_NUM_ONLY}"
                            } else {
                                // Update latest tag for Monthly release
                                if (! params.PRE_RELEASE){
                                    sh PIPELINE + " push_image ${image_worker} latest"
                                }
                            }
                        }
                    }
                },
                publish_piwind_worker: {
                    stage('Publish: model_worker') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_piwind} ${env.TAG_RELEASE}"

                            if (is_lts_branch) {
                                // Push LTS image tags
                                sh "docker tag ${image_piwind}:${env.TAG_RELEASE} ${image_piwind}:latest-lts"
                                sh "docker tag ${image_piwind}:${env.TAG_RELEASE} ${image_piwind}:${RELEASE_NUM_ONLY}"
                                sh "docker push ${image_piwind}:latest-lts"
                                sh "docker push ${image_piwind}:${RELEASE_NUM_ONLY}"
                            } else {
                                // Update latest tag for Monthly release
                                if (! params.PRE_RELEASE){
                                    sh PIPELINE + " push_image ${image_piwind} latest"
                                }
                            }
                        }
                    }
                }
            )
        }
    } catch(hudson.AbortException | org.jenkinsci.plugins.workflow.steps.FlowInterruptedException buildException) {
        hasFailed = true
        error('Build Failed')
    } finally {
        dir(build_workspace) {
            sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs server-db      > ./stage/log/server-db.log '
            sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs server         > ./stage/log/server.log '
            sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs celery-db      > ./stage/log/celery-db.log '
            sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs rabbit         > ./stage/log/rabbit.log '
            sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker         > ./stage/log/worker.log '
            sh 'docker-compose -f compose/oasis.platform.yml -f compose/model.worker.yml logs worker-monitor > ./stage/log/worker-monitor.log '
            sh PIPELINE + " stop_docker ${env.COMPOSE_PROJECT_NAME}"
            if(params.PURGE){
                sh PIPELINE + " purge_image ${image_api} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_worker} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_worker} ${env.TAG_RELEASE}-debian"
                sh PIPELINE + " purge_image ${image_piwind} ${env.TAG_RELEASE}"
            }
        }

        if(params.SLACK_MESSAGE && (params.PUBLISH || hasFailed)){
            def slackColor = hasFailed ? '#FF0000' : '#27AE60'
            JOB = env.JOB_NAME.replaceAll('%2F','/')
            SLACK_GIT_URL = "https://github.com/OasisLMF/${oasis_name}/tree/${oasis_branch}"
            SLACK_MSG = "*${JOB}* - (<${env.BUILD_URL}|${env.RELEASE_TAG}>): " + (hasFailed ? 'FAILED' : 'PASSED')
            SLACK_MSG += "\nBranch: <${SLACK_GIT_URL}|${oasis_branch}>"
            SLACK_MSG += "\nMode: " + (params.PUBLISH ? 'Publish' : 'Build Test')
            SLACK_CHAN = (params.PUBLISH ? "#builds-release":"#builds-dev")
            slackSend(channel: SLACK_CHAN, message: SLACK_MSG, color: slackColor)
        }
        //Store logs
        dir(build_workspace) {
            archiveArtifacts artifacts: "stage/log/**/*.*", excludes: '*stage/log/**/*.gitkeep'
            archiveArtifacts artifacts: "stage/output/**/*.*"
        }
        //Store repo scan reports
        if (params.SCAN_IMAGE_VULNERABILITIES.replaceAll(" \\s","")){
            dir(oasis_workspace){
                archiveArtifacts artifacts: 'scan_reports/**/*.*'
            }

        }
        //Store Docker image reports
        if (params.SCAN_IMAGE_VULNERABILITIES.replaceAll(" \\s","")){
            dir(oasis_workspace){
                archiveArtifacts artifacts: 'image_reports/**/*.*'
            }

        }
        //Store reports
        if (params.UNITTEST){
            dir(oasis_workspace){
                archiveArtifacts artifacts: 'reports/**/*.*'
            }
        }
        // Run merge back if publish
        if (params.PUBLISH && params.AUTO_MERGE && ! hasFailed){
            dir(oasis_workspace) {
                sshagent (credentials: [git_creds]) {
                    if (! params.PRE_RELEASE) {
                        // Release merge back into master
                        sh "git stash"
                        sh "git checkout master && git pull"
                        sh "git merge ${oasis_branch} && git push"
                        sh "git checkout develop && git pull"
                        sh "git merge master && git push"
                    } else {
                        // pre_pelease merge back into develop
                        sh "git stash"
                        sh "git checkout develop && git pull"
                        sh "git merge ${oasis_branch} && git push"
                    }
                }
            }
        }
    }
}
