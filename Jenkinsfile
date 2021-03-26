pipeline {
    agent {
        node {
            label "V13.saas.stage.cnc"
        }
    }
    environment {
        GITHUB_DEPLOYMENT_KEY = credentials('github-deployment-key')
        BITBUCKET_DEPLOYMENT_KEY = credentials('bitbucket-deployment-key')
    }
    stages {
        stage("Build edxapp-base image"){
            steps {
                
                // https://www.jenkins.io/doc/book/pipeline/docker/#building-containers
                commit_sha = sh(returnStdout: true, script: 'git rev-parse HEAD').trim() 
                echo "Build image"
                sh """
                    docker build . -f Dockerfile -t ednxops/edxapp-base --build-arg SSH_PRIVATE_KEY="\$(cat $GITHUB_DEPLOYMENT_KEY)"
                """

                echo "Tag image"
                sh """
                    docker tag ednxops/edxapp-base:latest ednxops/edxapp-base:$commit_sha
                """        
            }
        }
        stage('Run edx-platform test suite') {
            steps {
                //Please check Jenkins files located in the folder scripts/jenkinsfiles to get more information about edx run tests using Jenkins
                // These repos can be useful too:
                // - https://github.com/edx/jenkins-job-dsl
                // - https://github.com/edx/jenkins-configuration
                // - https://github.com/edx/testeng-ci

                sh "bash scripts/all-tests.sh"
            }
        }
        stage('Push edxapp-base image') {

            steps {withCredentials([usernamePassword(credentialsId: 'docker-credentials', passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                commit_sha = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                sh """
                docker login -u ${DOCKER_USERNAME} -p ${DOCKER_PASSWORD}
                docker push ednxops/edxapp-base:$commit_sha
                """
            }
        }
    }
}
