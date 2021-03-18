pipeline {
    agent {
        label "V13.saas.stage.cnc"
    }
    stages {
        stage("Build"){
            steps {
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
