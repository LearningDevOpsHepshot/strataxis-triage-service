pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        LLM_API_KEY   = credentials('llm-api-key')
        EVAL_THRESHOLD = '0.85'
        PY             = 'venv\\Scripts\\python.exe'
        STAGING        = 'C:\\stx\\staging'
    }

    stages {
        stage('1. Checkout') {
            steps {
                echo 'Using the source revision checked out by Jenkins...'
                bat 'git rev-parse --short HEAD > commit.txt'
                bat 'type commit.txt'
            }
        }

        stage('2. Environment') {
            steps {
                echo 'Finding Python and creating an isolated environment...'
                bat '''
                    @echo off
                    where python.exe >nul 2>&1
                    if %ERRORLEVEL% EQU 0 (
                        python.exe -m venv venv
                        goto :venv_created
                    )

                    where py.exe >nul 2>&1
                    if %ERRORLEVEL% EQU 0 (
                        py.exe -3 -m venv venv
                        goto :venv_created
                    )

                    echo ERROR: Jenkins cannot find Python or the Python launcher.
                    echo Install Python for all users, add it to the system PATH, and restart Jenkins.
                    exit /b 1

                    :venv_created
                    if not exist "%PY%" (
                        echo ERROR: The Python virtual environment was not created.
                        exit /b 1
                    )
                '''
                bat '"%PY%" --version'
                bat '"%PY%" -m pip install --upgrade pip'
                bat '"%PY%" -m pip install -r requirements.txt'
            }
        }

        stage('3. Lint') {
            steps {
                echo 'Checking code style and obvious errors...'
                bat '"%PY%" -m ruff check app tests evals'
            }
        }

        stage('4. Unit Tests') {
            steps {
                echo 'Running unit and API smoke tests...'
                bat 'if not exist reports mkdir reports'
                bat '"%PY%" -m pytest tests -q --junitxml=reports\\junit.xml'
            }
        }

        stage('5. Evaluation Gate') {
            steps {
                echo 'Measuring AI quality against the labelled set...'
                bat '"%PY%" evals\\run_eval.py --threshold %EVAL_THRESHOLD%'
            }
        }

        stage('6. Package') {
            steps {
                echo 'Producing a versioned, shippable artifact...'
                bat 'if not exist dist mkdir dist'
                bat 'tar -a -c -f dist\\triage-%BUILD_NUMBER%.zip app requirements.txt'
            }
        }

        stage('7. Approval') {
            steps {
                script {
                    timeout(time: 15, unit: 'MINUTES') {
                        input message: 'Deploy build to Strataxis staging?',
                              ok: 'Approve deployment'
                    }
                }
            }
        }

        stage('8. Deploy to Staging') {
            steps {
                echo 'Releasing the approved artifact...'
                bat 'if not exist "%STAGING%" mkdir "%STAGING%"'
                bat 'copy /Y "dist\\triage-%BUILD_NUMBER%.zip" "%STAGING%\\"'
                bat 'echo %DATE% %TIME% build %BUILD_NUMBER% >> "%STAGING%\\log.txt"'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true,
                  testResults: 'reports/junit.xml'

            archiveArtifacts artifacts: 'dist/*.zip, reports/*',
                             allowEmptyArchive: true,
                             fingerprint: true

            // Re-enable this block after installing the HTML Publisher plugin.
            // publishHTML(target: [
            //     reportDir            : 'reports',
            //     reportFiles          : 'eval_report.html',
            //     reportName           : 'Evaluation Report',
            //     keepAll              : true,
            //     alwaysLinkToLastBuild: true,
            //     allowMissing         : true
            // ])
        }

        success {
            echo 'GREEN: this commit is safe to show the client.'
        }

        failure {
            echo 'RED: something regressed. Nothing was deployed.'
        }
    }
}
