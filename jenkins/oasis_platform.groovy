node {
    hasFailed = false
    sh 'sudo /var/lib/jenkins/jenkins-chown'
    deleteDir() // wipe out the workspace

    properties([
      parameters([
        [$class: 'StringParameterDefinition',  name: 'PLATFORM_BRANCH', defaultValue: BRANCH_NAME],
        [$class: 'StringParameterDefinition',  name: 'BUILD_BRANCH', defaultValue: 'master'],
        [$class: 'StringParameterDefinition',  name: 'MODEL_BRANCH', defaultValue: 'develop'],
        [$class: 'StringParameterDefinition',  name: 'MDK_BRANCH', defaultValue: 'develop'],
        [$class: 'StringParameterDefinition',  name: 'MODEL_NAME', defaultValue: 'OasisPiWind'],
        [$class: 'StringParameterDefinition',  name: 'BASE_TAG', defaultValue: 'latest'],
        [$class: 'StringParameterDefinition',  name: 'RELEASE_TAG', defaultValue: BRANCH_NAME.split('/').last() + "-${BUILD_NUMBER}"],
        [$class: 'StringParameterDefinition',  name: 'RUN_TESTS', defaultValue: '0_case 1_case 2_case'],
        [$class: 'TextParameterDefinition',    name: 'APPEND_CHANGELOG', defaultValue: '\n\n'],
        [$class: 'TextParameterDefinition',    name: 'APPEND_RELEASE', defaultValue: '\n\n'],
        [$class: 'BooleanParameterDefinition', name: 'UNITTEST', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'PURGE', defaultValue: Boolean.valueOf(true)],
        [$class: 'BooleanParameterDefinition', name: 'PUBLISH', defaultValue: Boolean.valueOf(false)],
        [$class: 'BooleanParameterDefinition', name: 'SLACK_MESSAGE', defaultValue: Boolean.valueOf(true)]
      ])
    ])

    // Build vars
    String build_repo = 'git@github.com:OasisLMF/build.git'
    String build_branch = params.BUILD_BRANCH
    String build_workspace = 'oasis_build'

    // docker vars
    String docker_api_base = "Dockerfile.api_server.base"
    String image_api_base  = "coreoasis/api_base"
    String docker_api_sql  = "Dockerfile.api_server.mysql"
    String image_api_sql   = "coreoasis/api_server"
    String docker_worker   = "Dockerfile.model_worker"
    String image_worker    = "coreoasis/model_worker"

    // platform vars
    String oasis_branch    = params.PLATFORM_BRANCH  // Git repo branch to build from
    String mdk_branch      = params.MDK_BRANCH
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

    // Update MDK branch based on model branch
    if (BRANCH_NAME.matches("master") || BRANCH_NAME.matches("hotfix/(.*)")){
        params.MDK_BRANCH='master'
        params.MODEL_BRANCH='master'
    } 

    // Set Global ENV
    env.PIPELINE_LOAD = script_dir + utils_sh

    env.OASIS_MODEL_DATA_DIR = "${env.WORKSPACE}/${model_workspace}"
    env.TAG_BASE             = params.BASE_TAG     //Build TAG for base set of images
    env.TAG_RELEASE          = params.RELEASE_TAG  //Build TAG for TARGET image
    env.TAG_RUN_PLATFORM     = params.RELEASE_TAG
    env.TAG_RUN_WORKER       = params.RELEASE_TAG
    env.COMPOSE_PROJECT_NAME = UUID.randomUUID().toString().replaceAll("-","")

    env.IMAGE_WORKER   = image_worker
    // Should read these values from test/conf.ini
    env.TEST_MAX_RUNTIME = '190'
    env.TEST_DATA_DIR = "${env.WORKSPACE}/${model_workspace}/tests"
    env.MODEL_SUPPLIER = 'OasisLMF'
    env.MODEL_VARIENT  = 'PiWind'
    env.MODEL_ID       = '1'
    sh 'env'


    // Param Publish Guards
    if (params.PUBLISH && ! ( oasis_branch.matches("release/(.*)") || oasis_branch.matches("hotfix/(.*)")) ){
        println("Publish Only allowed on a release/* or hotfix/* branches")
        sh "exit 1"
    }
    if (params.PUBLISH && ! params.APPEND_CHANGELOG) {
        println("Must note changes in APPEND_CHANGELOG")
        sh "exit 1"
    }
    if (params.PUBLISH && ! params.APPEND_RELEASE) {
        println("Must note changes in APPEND_RELEASE")
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
        }
        if (mdk_branch){
            stage('Git install MDK'){
                dir(oasis_workspace) {
                    sh "sed -i 's|.*oasislmf.*|-e git+git://github.com/OasisLMF/OasisLMF.git@${mdk_branch}#egg=oasislmf|g' requirements.txt"
                }
            }
        }
        parallel(
            build_oasis_api_server: {
                stage('Build: API server') {
                    dir(oasis_workspace) {
                        sh PIPELINE + " build_image ${docker_api_base} ${image_api_base} ${env.TAG_RELEASE}"
                        sh PIPELINE + " build_image ${docker_api_sql} ${image_api_sql} ${env.TAG_RELEASE} ${env.TAG_RELEASE}"

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
        if (params.UNITTEST){
            stage('Run: unittest') {
                dir(oasis_workspace) {
                    sh " ./runtests.sh"
                }
            }
        }
        stage('Run: API Server') {
            dir(build_workspace) {
                sh PIPELINE + " start_model"
            }
        }

        api_server_tests = params.RUN_TESTS.split()
        for(int i=0; i < api_server_tests.size(); i++) {
            stage("Run : ${api_server_tests[i]}"){
                dir(build_workspace) {
                    sh PIPELINE + " run_test --test-case ${api_server_tests[i]}"
                }
            }
        }
        
        if (params.PUBLISH){
            parallel(
                publish_api_base: {
                    stage ('Publish: api_base') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_api_base} ${env.TAG_RELEASE}"
                        }
                    }
                },
                publish_api_server: {
                    stage ('Publish: api_server') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_api_sql} ${env.TAG_RELEASE}"
                        }
                    }
                },
                publish_model_worker: {
                    stage('Publish: model_worker') {
                        dir(build_workspace) {
                            sh PIPELINE + " push_image ${image_worker} ${env.TAG_RELEASE}"
                        }
                    }
                }
            )
        }

        if(! hasFailed && params.PUBLISH){
            stage ('Publish: Update Changelog + Release notes') {
                sshagent (credentials: [git_creds]) {
                    dir(oasis_workspace) {
                        if (params.APPEND_CHANGELOG) {
                            // Insert Git Diff
                            String cmd = /cat CHANGELOG.rst | grep \` -m 1 | awk -F "\`" 'NR==1 {print $2}'/
                            prev_version = sh(script: cmd, returnStdout: true)
                            cmd = "sed -i '/AUTO_INSERT-CHANGE_DIFF/a .. _`%s`:  https://github.com/OasisLMF/OasisPlatform/compare/%s...%s' CHANGELOG.rst"
                            sh String.format(cmd, env.TAG_RELEASE, prev_version.trim(), env.TAG_RELEASE)

                            // Insert Changelog lines
                            l = params.APPEND_CHANGELOG.split('\n')
                            f = 'CHANGELOG.rst'
                            for (int i=1; i<=l.size(); i++){    
                                s = l[l.size() - i]
                                if(s.trim()){
                                    str_insert = s
                                } else {
                                    str_insert = "\n"
                                }
                                sh "sed -i '/AUTO_INSERT-CHANGE_LIST/a\\ ${str_insert}' ${f}"
                            }
                            // Insert Changelog Header 
                            sh "sed -i '/AUTO_INSERT-CHANGE_LIST/a --------' ${f}"
                            sh "sed -i '/AUTO_INSERT-CHANGE_LIST/a `${env.TAG_RELEASE}`_ ' ${f}"

                            // Commit and push changelog 
                            sh 'git add CHANGELOG.rst'
                            sh 'git commit -m "Update CHANGELOG.rst"'
                            sh 'git push'
                        }

                        if (params.APPEND_RELEASE){
                            // Insert RELEASE NOTES lines
                            l = params.APPEND_RELEASE.split('\n')
                            f = 'RELEASE.md'
                            for (int i=1; i<=l.size(); i++){    
                                s = l[l.size() - i]
                                if(s.trim()){
                                    str_insert = s
                                } else {
                                    str_insert = "\n"
                                }
                                sh "sed -i '/AUTO_INSERT-RELEASE/a\\ ${str_insert}' ${f}"
                            }

                            // Insert RELEASE HEADER
                            def current_date = new Date()
                            publush_date = current_date.format('(dd/MM/yyyy)')
                            sh "sed -i '/AUTO_INSERT-RELEASE/a # ${env.TAG_RELEASE} ${publush_date}' ${f}"

                            // Commit and push RELEASE notes 
                            sh 'git add RELEASE.md'
                            sh 'git commit -m "Update RELEASE.md"'
                            sh 'git push'
                        }
                    }
                }
            }
            stage ('Publish: Git Tag') {
                sshagent (credentials: [git_creds]) {
                    // Tag the OasisPlatform
                    dir(oasis_workspace) {
                        sh PIPELINE + " git_tag ${env.TAG_RELEASE}"
                    }
                    // Tag PiWind 
                    dir(model_workspace) {
                        sh PIPELINE + " git_tag ${env.TAG_RELEASE}"
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
                sh PIPELINE + " purge_image ${image_api_base} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_api_sql} ${env.TAG_RELEASE}"
                sh PIPELINE + " purge_image ${image_worker} ${env.TAG_RELEASE}"
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
    }
}
