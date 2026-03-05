pipeline {
    agent any

    // Path to Python inside the project venv – adjust if Jenkins checks out
    // to a different location or you want a system-wide Python instead.
    environment {
        PYTHON      = "${WORKSPACE}\\venv\\Scripts\\python.exe"
        PIP         = "${WORKSPACE}\\venv\\Scripts\\pip.exe"
        OUTPUT_DIR  = "C:\\Users\\thima\\OneDrive\\Desktop\\ETL\\test-data"
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

        stage('Setup Python Environment') {
            steps {
                powershell '''
                    # Create venv if it doesn't already exist
                    if (-Not (Test-Path "$env:WORKSPACE\\venv")) {
                        Write-Host "Creating virtual environment..."
                        python -m venv "$env:WORKSPACE\\venv"
                    } else {
                        Write-Host "Virtual environment already exists, skipping creation."
                    }

                    # Upgrade pip and install dependencies
                    & "$env:WORKSPACE\\venv\\Scripts\\pip.exe" install --upgrade pip --quiet
                    & "$env:WORKSPACE\\venv\\Scripts\\pip.exe" install -r "$env:WORKSPACE\\requirements.txt" --quiet
                    Write-Host "Dependencies installed."
                '''
            }
        }

        stage('Run ETL') {
            steps {
                // Credentials stored in Jenkins as "Username with password"
                // Manage Jenkins > Credentials > Global > Add Credentials
                // Kind: Username with password  |  ID: copernicus-marine-credentials
                withCredentials([
                    usernamePassword(
                        credentialsId: 'copernicus-marine-credentials',
                        usernameVariable: 'COPERNICUSMARINE_USERNAME',
                        passwordVariable: 'COPERNICUSMARINE_PASSWORD'
                    )
                ]) {
                    withEnv(["ETL_OUTPUT_DIR=${OUTPUT_DIR}"]) {
                    powershell '''
                        New-Item -ItemType Directory -Force -Path "$env:OUTPUT_DIR" | Out-Null
                        & "$env:PYTHON" "$env:WORKSPACE\\run.py"
                        if ($LASTEXITCODE -ne 0) {
                            throw "run.py exited with code $LASTEXITCODE"
                        }
                    '''
                    } // withEnv
                }
            }
        }

        stage('Archive Outputs') {
            steps {
                // Copy from local output dir into the Jenkins workspace so
                // archiveArtifacts (which is workspace-relative) can find them.
                powershell '''
                    $dest = "$env:WORKSPACE\\test-data"
                    New-Item -ItemType Directory -Force -Path $dest | Out-Null
                    Copy-Item -Path "$env:OUTPUT_DIR\\*.nc" -Destination $dest -Force
                '''
                archiveArtifacts artifacts: 'test-data/*.nc', fingerprint: true, allowEmptyArchive: false
            }
        }
    }

    post {
        success {
            echo "ETL pipeline completed successfully. Artifacts archived."
        }
        failure {
            echo "ETL pipeline failed. Check the console output for details."
        }
    }
}
