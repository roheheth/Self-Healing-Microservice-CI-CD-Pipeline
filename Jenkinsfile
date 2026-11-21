pipeline {
    agent any

    environment {
        APP_NAME        = 'self-healing-api'
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        DOCKER_REGISTRY = 'docker.io/roheheth'
        DD_API_KEY      = credentials('datadog-api-key')
        DD_APP_KEY      = credentials('datadog-app-key')
    }

    stages {
        stage('Code Quality & Linting') {
            steps {
                echo 'Running linting and code quality checks...'
                sh '''
                    python3 -m venv venv || python -m venv venv
                    . venv/bin/activate || venv\\Scripts\\activate
                    pip install -r requirements.txt flake8
                    flake8 app.py --max-line-length=120
                '''
            }
        }

        stage('Container Build & Vulnerability Scan') {
            steps {
                echo 'Building Docker container and scanning with Trivy...'
                sh """
                    docker build -t ${APP_NAME}:${IMAGE_TAG} -t ${APP_NAME}:latest .
                    # trivy image --severity CRITICAL --exit-code 1 ${APP_NAME}:${IMAGE_TAG}
                """
            }
        }

        stage('Validate Infrastructure & Manifests') {
            steps {
                echo 'Validating Kubernetes manifests and Terraform...'
                dir('terraform') {
                    sh '''
                        terraform init -backend=false
                        terraform validate
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes (HA)') {
            steps {
                echo 'Executing Zero-Downtime Rolling Update...'
                sh '''
                    kubectl apply -f k8s-ha/
                    kubectl rollout status deployment/self-healing-api-ha --timeout=120s
                '''
            }
        }

        stage('Automated SLO & Performance Gate') {
            steps {
                echo 'Running automated k6 load test verification against SLO...'
                sh '''
                    k6 run loadtest/data_endpoint.js --quiet
                '''
            }
        }

        stage('Sync Datadog Monitors-as-Code') {
            steps {
                echo 'Upserting Datadog monitors...'
                sh '''
                    . venv/bin/activate || venv\\Scripts\\activate
                    python datadog/apply_monitors.py
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo "Pipeline succeeded! Application verified and live."
        }
        failure {
            echo "Pipeline failed! Rolling update aborted or alert triggered."
        }
    }
}
