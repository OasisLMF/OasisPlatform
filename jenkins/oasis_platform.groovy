node {
    hasFailed = false
    sh 'sudo /var/lib/jenkins/jenkins-chown'
    deleteDir() // wipe out the workspace

    // Build vars
    String build_repo = 'git@github.com:OasisLMF/build.git'
    String build_branch = params.BUILD_BRANCH
    String build_workspace = 'oasis_build'

    String  docker_api       = "Dockerfile.oasis_api_server"
    String  image_api        = "coreoasis/oasis_api_server"
    String  docker_worker    = "Dockerfile.model_execution_worker"
    String  image_worker     = "coreoasis/model_execution_worker"
    String  docker_keys_builtin = "docker/Dockerfile.builtin_keys_server"
    String  docker_keys_custom = "docker/Dockerfile.custom_keys_server"
    String  image_keys_builtin  = "coreoasis/builtin_keys_server"
    String  image_keys_custom  = "coreoasis/custom_keys_server"

	// platform vars
    String oasis_branch    = params.PLATFORM_BRANCH  // Git repo branch to build from
    String oasis_name      = 'OasisPlatform'
    String oasis_git_url   = "git@github.com:OasisLMF/${oasis_name}.git"
    String oasis_workspace = 'platform_workspace'
    String utils_sh        = '/buildscript/utils.sh'
    String oasis_func      = "oasis_server"

    // keys server base vars
    String keys_branch     = params.KEYSERVER_BRANCH  // Git repo branch to build from
    String keys_name       = 'oasis_keys_server'
    String keys_workspace  = 'keys_workspace'
    String keys_git_url    = "git@github.com:OasisLMF/${keys_name}.git"

    String script_dir = env.WORKSPACE + "/${build_workspace}"
    String git_creds  = "1335b248-336a-47a9-b0f6-9f7314d6f1f4"
    String PIPELINE   = script_dir + "/buildscript/pipeline.sh"

    // Set Global ENV
    env.PIPELINE_LOAD = script_dir + utils_sh       

    env.TAG_BASE         = params.BASE_TAG     //Build TAG for base set of images
    env.TAG_RELEASE      = params.RELEASE_TAG  //Build TAG for TARGET image 
    env.TAG_RUN_PLATFORM = params.RELEASE_TAG 
    env.COMPOSE_PROJECT_NAME = UUID.randomUUID().toString().replaceAll("-","")
    sh 'env'

     



    try {
        parallel(
            clone_oasis_build: {
                stage('Clone: ' + build_workspace) {
                    dir(build_workspace) {
                       git url: build_repo, credentialsId: git_creds, branch: build_branch 
                    }
                }
            },
            clone_oasis_keys_server: {
                stage('Clone: ' + keys_workspace) {
                    dir(keys_workspace) {
                       git url: keys_git_url, credentialsId: git_creds, branch: keys_branch 
                    }
                }
            },
            clone_oasis_platform: {
                stage('Clone: ' + oasis_func) {
                    sshagent (credentials: [git_creds]) {
                        dir(oasis_workspace) {
							sh "git clone -b ${oasis_branch} --recursive ${oasis_git_url} ."
                        }
                    }
                }
            }
        )
        stage('Shell Env'){
            sh  PIPELINE + ' print_model_vars'
        }
        parallel(
            build_oasis_api_server: {
                stage('Build: ' + oasis_func) {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_api} ${image_api} ${env.TAG_RELEASE} ${env.TAG_BASE}"
                    }
                }
            },
            build_model_execution_worker: {
                stage('Build: model exec worker') {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_worker} ${image_worker} ${env.TAG_RELEASE} ${env.TAG_BASE}"
                    }
                }
            },
            build_model_keys_server: {
                stage('Build: base keys server') {
                    dir(keys_workspace) {
                        sh PIPELINE + " build_image ${docker_keys_builtin} ${image_keys_builtin} ${env.TAG_RELEASE} ${env.TAG_BASE}"
                        sh PIPELINE + " build_image ${docker_keys_custom} ${image_keys_custom} ${env.TAG_RELEASE} ${env.TAG_BASE}"

                    }
                }
            }
        )
        if(params.UNITTEST)
        stage('Test: Tox unittesting'){
            dir(oasis_workspace) {
                sh 'set -eux && /usr/local/bin/tox' 
            }
        }
        if(params.FLAKE8){
            stage('Test: PEP8'){
                dir(oasis_workspace) {
                    sh 'set -eux && flake8' 
                }
            }
        }
        stage('Test: integration ' + oasis_func) {
            dir(build_workspace) {
                sh PIPELINE + " run_test_api"
            }
        }
        if (params.PUBLISH){
            parallel(
                publish_oasis_api_server: {
                    stage ('Publish: oasis_api_server') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_api} ${env.TAG_RELEASE}"
                        }
                    }
                },
                publish_model_execution_worker: {
                    stage('Publish: exceution_worker') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_worker} ${env.TAG_RELEASE}"
                        }
                    }
                },
                publish_model_keys_server: {
                    stage('Publish: keys_server') {
                        dir(keys_workspace) {
                            sh PIPELINE + " push_image ${image_keys_builtin} ${env.TAG_RELEASE}"
                            sh PIPELINE + " push_image ${image_keys_custom} ${env.TAG_RELEASE}"
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
            sh PIPELINE + " stop_docker ${env.COMPOSE_PROJECT_NAME}" 
            if(params.PURGE){
                sh PIPELINE + " purge_image ${image_api} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_worker} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_keys_builtin} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_keys_custom} ${env.TAG_RELEASE}"
            } 
        }

        if(params.SLACK_MESSAGE && (params.PUBLISH || hasFailed)){
            def slackColor = hasFailed ? '#FF0000' : '#27AE60'
            SLACK_GIT_URL = "https://github.com/OasisLMF/${oasis_name}/tree/${oasis_branch}"
            SLACK_MSG = "*${env.JOB_NAME}* - (<${env.BUILD_URL}|${env.RELEASE_TAG}>): " + (hasFailed ? 'FAILED' : 'PASSED')
            SLACK_MSG += "\nBranch: <${SLACK_GIT_URL}|${oasis_branch}>"
            SLACK_MSG += "\nMode: " + (params.PUBLISH ? 'Publish' : 'Build Test')
            SLACK_CHAN = (params.PUBLISH ? "#builds-release":"#builds-dev")
            slackSend(channel: SLACK_CHAN, message: SLACK_MSG, color: slackColor)
        }
        if(! hasFailed && params.PUBLISH){
            sshagent (credentials: [git_creds]) {
                dir(oasis_workspace) {
                    sh PIPELINE + " git_tag ${env.TAG_RELEASE}"
                }
                dir(keys_workspace) {
                    sh PIPELINE + " git_tag ${env.TAG_RELEASE}"
                }
            }
        }
        //Store logs
        dir(build_workspace) {
            archiveArtifacts artifacts: 'stage/log/**/*.*', excludes: '*stage/log/**/*.gitkeep'
        }
    }
}
