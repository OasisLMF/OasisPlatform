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


    properties([
      parameters([
        [$class: 'StringParameterDefinition',  name: 'PLATFORM_BRANCH', defaultValue: BRANCH_NAME],
        [$class: 'StringParameterDefinition',  name: 'BUILD_BRANCH', defaultValue: 'master'],
        [$class: 'StringParameterDefinition',  name: 'MDK_BRANCH', defaultValue: 'develop'],
        [$class: 'StringParameterDefinition',  name: 'RELEASE_TAG', defaultValue: BRANCH_NAME.split('/').last() + "-${BUILD_NUMBER}"],
        [$class: 'TextParameterDefinition',    name: 'MODEL_REGRESSION', defaultValue: model_regression_list],
        [$class: 'BooleanParameterDefinition', name: 'UNITTEST', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'CHECK_COMPATIBILITY', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'CHECK_S3', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'RUN_REGRESSION', defaultValue: Boolean.valueOf(false)],
        [$class: 'BooleanParameterDefinition', name: 'PURGE', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'PUBLISH', defaultValue: Boolean.valueOf(false)],
        [$class: 'BooleanParameterDefinition', name: 'AUTO_MERGE', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'SLACK_MESSAGE', defaultValue: Boolean.valueOf(true)]
      ])
    ])

    // Build vars
    String build_repo = 'git@github.com:OasisLMF/build.git'
    String build_branch = params.BUILD_BRANCH
    String build_workspace = 'oasis_build'

    // docker vars (main)
    String docker_api    = "Dockerfile.api_server"
    String image_api     = "coreoasis/api_server"
    String docker_worker = "Dockerfile.model_worker"
    String image_worker  = "coreoasis/model_worker"

    // docker vars (slim)
    String docker_api_slim    = "docker/Dockerfile.api_server_alpine"
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
    String model_branch     = 'develop'
    String model_name       = 'OasisPiWind'
    String model_tests      = 'control_set'
    String model_workspace  = "${model_name}_workspace"
    String model_git_url    = "git@github.com:OasisLMF/${model_name}.git"
    String model_test_dir  = "${env.WORKSPACE}/${model_workspace}/tests/"
    String model_test_ini  = "test-config.ini"


    String script_dir = env.WORKSPACE + "/${build_workspace}"
    String git_creds  = "1335b248-336a-47a9-b0f6-9f7314d6f1f4"
    String PIPELINE   = script_dir + "/buildscript/pipeline.sh"

    // Update MDK branch based on model branch
    if (BRANCH_NAME.matches("master") || BRANCH_NAME.matches("hotfix/(.*)")){
        MDK_BRANCH='master'
        MODEL_BRANCH='master'
    }

    // Set Global ENV
    env.PIPELINE_LOAD = script_dir + utils_sh

    env.OASIS_MODEL_DATA_DIR = "${env.WORKSPACE}/${model_workspace}"
    //env.TAG_BASE             = params.BASE_TAG     //Build TAG for base set of images
    env.TAG_RELEASE          = params.RELEASE_TAG  //Build TAG for TARGET image
    env.TAG_RUN_PLATFORM     = params.RELEASE_TAG
    env.TAG_RUN_WORKER       = params.RELEASE_TAG
    env.COMPOSE_PROJECT_NAME = UUID.randomUUID().toString().replaceAll("-","")

    env.IMAGE_WORKER   = image_worker
    // Should read these values from test/conf.ini
    env.TEST_MAX_RUNTIME = '190'
    env.TEST_DATA_DIR = model_test_dir
    env.MODEL_SUPPLIER = 'OasisLMF'
    env.MODEL_VARIENT  = 'PiWind'
    env.MODEL_ID       = '1'
    sh 'env'


    // Param Publish Guards
    if (params.PUBLISH && ! ( oasis_branch.matches("release/(.*)") || oasis_branch.matches("hotfix/(.*)")) ){
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
        stage('Shell Env'){
            sh  PIPELINE + ' print_model_vars'
            if (params.CHECK_COMPATIBILITY) {
                dir(oasis_workspace) {
                    sh "curl https://api.github.com/repos/OasisLMF/OasisPlatform/tags | jq -r '( first ) | .name' > last_release_tag"
                    env.LAST_RELEASE_TAG = readFile('last_release_tag').trim()
                    println("LAST_RELEASE = $env.LAST_RELEASE_TAG")
                }
            }
        }
        if (mdk_branch && ! params.PUBLISH){
            stage('Git install MDK'){
                dir(oasis_workspace) {
                    // update worker and server install lists
                    sh "sed -i 's|^oasislmf.*| git+git://github.com/OasisLMF/OasisLMF.git@${mdk_branch}#egg=oasislmf|g' requirements-worker.txt"
                    sh "sed -i 's|^oasislmf.*| git+git://github.com/OasisLMF/OasisLMF.git@${mdk_branch}#egg=oasislmf|g' requirements.txt"
                }
            }
        }
        stage('Set version file'){
            dir(oasis_workspace){
                sh "echo ${env.TAG_RELEASE} - " + '$(git rev-parse --short HEAD), $(date) > VERSION'
            }
        }
        parallel(
            build_oasis_api_server: {
                stage('Build: API server') {
                    dir(oasis_workspace) {
                        if (params.PUBLISH) {
                            sh PIPELINE + " build_image ${docker_api_slim} ${image_api} ${env.TAG_RELEASE}-slim"
                        }
                        sh PIPELINE + " build_image ${docker_api} ${image_api} ${env.TAG_RELEASE}"

                    }
                }
            },
            build_model_execution_worker: {
                stage('Build: model exec worker') {
                    dir(oasis_workspace) {
                        if (params.PUBLISH) {
                            sh PIPELINE + " build_image ${docker_worker_slim} ${image_worker} ${env.TAG_RELEASE}-slim"
                        }
                        sh PIPELINE + " build_image ${docker_worker} ${image_worker} ${env.TAG_RELEASE}"
                    }
                }
            }
        )
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
                    }
                }
            }

           // CHECK last release compatibility
           stage("Compatibility with worker:${env.LAST_RELEASE_TAG}") {
               dir(build_workspace) {
                   // Set tags
                   env.TAG_RUN_PLATFORM = params.RELEASE_TAG
                   env.TAG_RUN_WORKER = env.LAST_RELEASE_TAG

                   // Setup containers
                   sh PIPELINE + " start_model"

                   // run test
                    sh PIPELINE + " run_test --config /var/oasis/test/${model_test_ini} --test-case ${api_server_tests[0]}"
               }
           }
           stage("Compatibility with server:${env.LAST_RELEASE_TAG}") {
               dir(build_workspace) {
                   // reset db-data
                   sh PIPELINE + " stop_docker ${env.COMPOSE_PROJECT_NAME}"
                   env.OASIS_DOCKER_DB_DATA_DIR = './db-data_pre-ver'

                   // Set tags
                   env.TAG_RUN_PLATFORM = env.LAST_RELEASE_TAG
                   env.TAG_RUN_WORKER = params.RELEASE_TAG

                   // Setup containers
                   sh PIPELINE + " start_model"

                   // run test
                   sh PIPELINE + " run_test --config /var/oasis/test/${model_test_ini} --test-case ${api_server_tests[0]}"
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
                   env.TAG_RUN_PLATFORM = params.RELEASE_TAG
                   env.TAG_RUN_WORKER = params.RELEASE_TAG

                   // run test
                   sh PIPELINE + " run_test_s3 --config /var/oasis/test/${model_test_ini} --test-case ${model_tests}"
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

       if (params.PUBLISH){
            parallel(
                publish_api_server: {
                    stage ('Publish: api_server') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_worker} ${env.TAG_RELEASE}-slim"
                            sh PIPELINE + " push_image ${image_api} ${env.TAG_RELEASE}"
                        }
                    }
                },
                publish_model_worker: {
                    stage('Publish: model_worker') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_api} ${env.TAG_RELEASE}-slim"
                            sh PIPELINE + " push_image ${image_worker} ${env.TAG_RELEASE}"
                        }
                    }
                }
            )
        }

        if(params.PUBLISH){
            stage ('Create Release: GitHub') {
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

                // Create Release
                withCredentials([string(credentialsId: 'github-api-token', variable: 'gh_token')]) {
                    dir(oasis_workspace) {
                        String repo = "OasisLMF/OasisPlatform"

                        def json_request = readJSON text: '{}'
                        json_request['tag_name'] = RELEASE_TAG
                        json_request['target_commitish'] = 'master'
                        json_request['name'] = RELEASE_TAG
                        json_request['body'] = ""
                        json_request['draft'] = false
                        json_request['prerelease'] = false
                        writeJSON file: 'gh_request.json', json: json_request
                        sh 'curl -XPOST -H "Authorization:token ' + gh_token + "\" --data @gh_request.json https://api.github.com/repos/$repo/releases > gh_response.json"

                        // Fetch release ID and post json schema
                        def response = readJSON file: "gh_response.json"
                        release_id = response['id']
                        dir('reports') {
                            filename='openapi-schema.json'
                            sh 'curl -XPOST -H "Authorization:token ' + gh_token + '" -H "Content-Type:application/octet-stream" --data-binary @' + filename + " https://uploads.github.com/repos/$repo/releases/$release_id/assets?name=" + "openapi-schema-${RELEASE_TAG}.json"
                        }

                        // Create milestone
                        sh PIPELINE + " create_milestone ${gh_token} ${repo} ${env.TAG_RELEASE} CHANGELOG.rst"
                    }
                }
            }
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

                if (params.PUBLISH) {
                    sh PIPELINE + " purge_image ${image_api} ${env.TAG_RELEASE}-slim"
                    sh PIPELINE + " purge_image ${image_worker} ${env.TAG_RELEASE}-slim"
                }
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
        //Store reports
        if (params.UNITTEST){
            dir(oasis_workspace){
                archiveArtifacts artifacts: 'reports/**/*.*'
            }
        }
        // Run merge back if publish
        if (params.PUBLISH && params.AUTO_MERGE){
            dir(oasis_workspace) {
                sshagent (credentials: [git_creds]) {
                    sh "git stash"
                    sh "git checkout master && git pull"
                    sh "git merge ${oasis_branch} && git push"
                    sh "git checkout develop && git pull"
                    sh "git merge master && git push"
                }
            }
        }
    }
}
