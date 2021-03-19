pipeline {
    agent {
        node {
            label "V13.saas.stage.cnc"
        }
    }
    stages {
        stage("Build"){
            steps {
                
                // sh 'rm -rf /home/robonext/tutor'
                // sh 'rm -rf /home/robonext/tutor-plugins'

                // withPythonEnv('/usr/local/bin/python3.8'){
                //     sh 'pip install -e git+https://github.com/eduNEXT/tutor.git@e4fa7f553bb665c4a6c2c01f48fe448b2ac5a427#egg=tutor-openedx'
                //     sh 'tutor config printroot'
                //     dir("/home/robonext/tutor-plugins") {
                //         git credentialsId: 'a29e1386-41b4-413f-a6f2-42e53fe9bf44', url: 'git@bitbucket.org:edunext/ednx_tutor_plugins.git', branch: 'eric/mvp'
                //     }
                //     sh 'tutor plugins enable ednx_secrets ednx_general ednx_edxapp ednx_hosts ednx_docker ednx_databases ednx_forum ednx_k8s'
                //     sh 'tutor plugins list'
                //     sh 'tutor config save'
                // }

                // steps {withCredentials([usernamePassword(credentialsId: 'YOUR_ID_DEFINED', passwordVariable: 'YOUR_PW_DEFINED', usernameVariable: 'YOUR_ACCOUNT_DEFINED')]) {
                //             sh """
                //             docker login ${REGISTRY_URI} -u ${YOUR_ACCOUNT_DEFINED} -p ${YOUR_PW_DEFINED}
                //             """
                //         }
                echo "Docker Build"
                sh """
                    docker build . -f Dockerfile --target edxapp-base -t ednxops/edxapp-base
                """

                // echo "Docker Tag"
                // sh """
                //     docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${REGISTRY_URI}/${REGISTRY_NAME}/${IMAGE_NAME}:${GIT_BRANCH}-${GIT_COMMIT}
                //     docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${REGISTRY_URI}/${REGISTRY_NAME}/${IMAGE_NAME}:${GIT_BRANCH}-${BUILD_NUMBER}
                //     docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${REGISTRY_URI}/${REGISTRY_NAME}/${IMAGE_NAME}:${GIT_BRANCH}-${LATEST}
                // """
                        
                // echo "Docker Push"
                // sh """
                //     docker push ${REGISTRY_URI}/${REGISTRY_NAME}/${IMAGE_NAME}:${GIT_BRANCH}-${GIT_COMMIT}
                //     docker push ${REGISTRY_URI}/${REGISTRY_NAME}/${IMAGE_NAME}:${GIT_BRANCH}-${BUILD_NUMBER}
                //     docker push ${REGISTRY_URI}/${REGISTRY_NAME}/${IMAGE_NAME}:${GIT_BRANCH}-${LATEST}
                // """
         
            }
            post{
                success{
                    echo "Build and Push Successfully"
                }
                failure{
                    echo "Build and Push Failed"
                }
            }
        }
        stage('Image Scan') {
            steps {
                //Put your image scanning tool 
                echo 'Image Scanning Start'
            }
            post{
                success{
                    echo "Image Scanning Successfully"
                }
                failure{
                    echo "Image Scanning Failed"
                }
            }
        }
    
    }
}
