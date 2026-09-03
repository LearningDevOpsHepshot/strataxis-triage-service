"environment {
  LLM_API_KEY = credentials('llm-api-key')
}"


pipeline {
 
    // 'agent any' = run on any available machine.
    // On your standalone setup, that machine is your own laptop.
    agent any
 
    options {
        timestamps()                       // a clock beside every log line
        timeout(time: 20, unit: 'MINUTES') // never let a build hang forever
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }
 
    environment {
        EVAL_THRESHOLD = '0.85'                    // the agreed quality bar
        PY      = 'venv\\Scripts\\python.exe'      // Python inside our venv
        STAGING = 'C:\\stx\\staging'               // stands in for a server
    }
 
    stages {
 
        stage('1. Checkout') {
            steps {
                echo 'Fetching the exact commit that triggered this build...'
                checkout scm
                bat 'git rev-parse --short HEAD > commit.txt'
                bat 'type commit.txt'
            }
        }
 
        stage('2. Environment') {
            steps {
                echo 'Building a clean, isolated Python environment...'
                bat 'python -m venv venv'
                bat '%PY% -m pip install --upgrade pip'
                bat '%PY% -m pip install -r requirements.txt'
            }
        }
 
        stage('3. Lint') {
            steps {
                echo 'Checking code style and obvious errors...'
                bat '%PY% -m ruff check app tests evals'
            }
        }
 
        stage('4. Unit Tests') {
            steps {
                echo 'Running unit and API smoke tests...'
                bat '%PY% -m pytest tests -q --junitxml=reports/junit.xml'
            }
        }
 
        stage('5. Evaluation Gate') {
            steps {
                echo 'Measuring AI quality against the labelled set...'
                bat '%PY% evals\\run_eval.py --threshold %EVAL_THRESHOLD%'
            }
        }
 
        stage('6. Package') {
            steps {
                echo 'Producing a versioned, shippable artifact...'
                bat 'if not exist dist mkdir dist'
                bat 'tar -a -c -f dist/triage-%BUILD_NUMBER%.zip app requirements.txt'
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
                bat 'if not exist %STAGING% mkdir %STAGING%'
                bat 'copy /Y dist\\triage-%BUILD_NUMBER%.zip %STAGING%\\'
                bat 'echo %DATE% %TIME% build %BUILD_NUMBER% >> %STAGING%\\log.txt'
            }
        }
    }
 
    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/junit.xml'
            archiveArtifacts artifacts: 'dist/*.zip, reports/*',
                             allowEmptyArchive: true, fingerprint: true
            publishHTML(target: [
                reportDir            : 'reports',
                reportFiles          : 'eval_report.html',
                reportName           : 'Evaluation Report',
                keepAll              : true,
                alwaysLinkToLastBuild: true,
                allowMissing         : true
            ])
        }
        success {
            echo 'GREEN: this commit is safe to show the client.'
        }
        failure {
            echo 'RED: something regressed. Nothing was deployed.'
        }
    }
}
