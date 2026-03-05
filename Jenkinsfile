pipeline {
    agent any

    environment {
        IMAGE_NAME  = "copernicus-etl"
        IMAGE_TAG   = "${BUILD_NUMBER}"
        OUTPUT_DIR  = "${WORKSPACE}/test-data"
    }

    options {
        timestamps()
        timeout(time: 2, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Image') {
            steps {
                script {
                    docker.build("${IMAGE_NAME}:${IMAGE_TAG}")
                }
            }
        }

        stage('Run ETL') {
            steps {
                // Credentials stored in Jenkins as a "Username with password"
                // credential with ID: copernicus-marine-credentials
                withCredentials([
                    usernamePassword(
                        credentialsId: 'copernicus-marine-credentials',
                        usernameVariable: 'CMEMS_USER',
                        passwordVariable: 'CMEMS_PASS'
                    )
                ]) {
                    script {
                        // Ensure the output directory exists on the host
                        sh "mkdir -p ${OUTPUT_DIR}"

                        docker.image("${IMAGE_NAME}:${IMAGE_TAG}").inside(
                            "--env COPERNICUSMARINE_USERNAME=${CMEMS_USER} " +
                            "--env COPERNICUSMARINE_PASSWORD=${CMEMS_PASS} " +
                            "-v ${OUTPUT_DIR}:/app/test-data"
                        ) {
                            sh 'python run.py'
                        }
                    }
                }
            }
        }

        stage('Archive Outputs') {
            steps {
                archiveArtifacts artifacts: 'test-data/*.nc', fingerprint: true, allowEmptyArchive: false
            }
        }
    }

    post {
        always {
            // Remove the image to keep the agent clean
            sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true"
        }
        success {
            echo "ETL pipeline completed successfully. Artifacts archived."
        }
        failure {
            echo "ETL pipeline failed. Check the console output for details."
        }
    }
}
