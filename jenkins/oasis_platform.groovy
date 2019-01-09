node {
    hasFailed = false
    sh 'sudo /var/lib/jenkins/jenkins-chown'
    deleteDir() // wipe out the workspace

    // Default Multibranch config
    try {
        auto_set_branch = CHANGE_BRANCH
    } catch (MissingPropertyException e) {
        auto_set_branch = BRANCH_NAME
    }
    properties([
      parameters([
        [$class: 'StringParameterDefinition',  name: 'PLATFORM_BRANCH', defaultValue: auto_set_branch],
        [$class: 'StringParameterDefinition',  name: 'BUILD_BRANCH', defaultValue: 'master'],
        [$class: 'StringParameterDefinition',  name: 'MODEL_BRANCH', defaultValue: 'master'],
        [$class: 'StringParameterDefinition',  name: 'MODEL_NAME', defaultValue: 'OasisPiWind'],
        [$class: 'StringParameterDefinition',  name: 'BASE_TAG', defaultValue: 'latest'],
        [$class: 'StringParameterDefinition',  name: 'RELEASE_TAG', defaultValue: "build-${BUILD_NUMBER}"],
        [$class: 'BooleanParameterDefinition', name: 'UNITTEST', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'FLAKE8', defaultValue: Boolean.valueOf(false)],
        [$class: 'BooleanParameterDefinition', name: 'PURGE', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'PUBLISH', defaultValue: Boolean.valueOf(false)],
        [$class: 'BooleanParameterDefinition', name: 'SLACK_MESSAGE', defaultValue: Boolean.valueOf(false)]
      ])
    ])

    // Build vars
    String build_repo = 'git@github.com:OasisLMF/build.git'
    String build_branch = params.BUILD_BRANCH
    String build_workspace = 'oasis_build'

    String docker_api_base = "Dockerfile.oasis_api_server.base"
    String image_api_base = "coreoasis/oasis_api_base"

    String docker_api_sql = "Dockerfile.oasis_api_server.mysql"
    String image_api_sql = "coreoasis/oasis_api_server"

    String  docker_worker    = "Dockerfile.model_execution_worker"
    String  image_worker     = "coreoasis/model_execution_worker"


	// platform vars
    String oasis_branch    = params.PLATFORM_BRANCH  // Git repo branch to build from
    String oasis_name      = 'OasisPlatform'
    String oasis_git_url   = "git@github.com:OasisLMF/${oasis_name}.git"
    String oasis_workspace = 'platform_workspace'
    String utils_sh        = '/buildscript/utils.sh'
    String oasis_func      = "oasis_server"

    // oasis model test
    String model_branch     = params.MODEL_BRANCH  // Git repo branch to build from
    String model_name       = params.MODEL_NAME
    String model_workspace  = "${model_name}_workspace"
    String model_git_url    = "git@github.com:OasisLMF/${model_name}.git"

    String script_dir = env.WORKSPACE + "/${build_workspace}"
    String git_creds  = "1335b248-336a-47a9-b0f6-9f7314d6f1f4"
    String PIPELINE   = script_dir + "/buildscript/pipeline.sh"

    // Set Global ENV
    env.PIPELINE_LOAD = script_dir + utils_sh       

    env.OASIS_API_PIWIND_DATA_DIR = model_workspace
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
                stage('Build: API server') {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_api_base} ${image_api_base} ${env.TAG_RELEASE} ${env.TAG_BASE}"
                        sh PIPELINE + " build_image ${docker_api_sql} ${image_api_sql} ${env.TAG_RELEASE} ${env.TAG_BASE}"

                    }
                }
            },
            build_model_execution_worker: {
                stage('Build: model exec worker') {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_worker} ${image_worker} ${env.TAG_RELEASE} ${env.TAG_BASE}"
                    }
                }
            }
        )
        stage('Run: unittest' + oasis_func) {
            dir(oasis_workspace) {
                sh " ./runtests.sh"
            }
        }
        /*
        stage('Run: Intergration tests' + oasis_func) {
            dir(build_workspace) {
                sh PIPELINE + " run_test_api"
            }
        }
         **/ 
        

        if (params.PUBLISH){
            parallel(
                publish_oasis_api_server: {
                    stage ('Publish: oasis_api_server') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_api_sql} ${env.TAG_RELEASE}"
                        }
                    }
                },
                publish_model_execution_worker: {
                    stage('Publish: exceution_worker') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_worker} ${env.TAG_RELEASE}"
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
                sh PIPELINE + " purge_image ${image_api_base} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_api_sql} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_worker} ${env.TAG_RELEASE}"
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
        dir(oasis_workspace) {
            archiveArtifacts artifacts: 'reports/**/*.*'
            //archiveArtifacts artifacts: 'stage/log/**/*.*', excludes: '*stage/log/**/*.gitkeep'
        }
    }
}
