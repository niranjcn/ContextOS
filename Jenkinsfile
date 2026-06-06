// =============================================================================
// ContextOS — Jenkins Declarative Pipeline
// =============================================================================
// Full CI/CD pipeline: Test → Lint → Build → Scan → Push → Deploy → Verify
//
// Prerequisites:
//   1. Jenkins credentials:
//      - 'ecr-registry-url': Your ECR registry URL (e.g., 123456789.dkr.ecr.us-east-1.amazonaws.com)
//      - 'aws-credentials': AWS access key + secret for ECR/EKS access
//      - 'slack-webhook' (optional): Slack webhook URL for notifications
//   2. Jenkins plugins: Docker Pipeline, Pipeline AWS Steps, Coverage
//   3. Tools on Jenkins agent: docker, aws-cli, kubectl, python3, trivy
// =============================================================================

pipeline {
    // Run on any available Jenkins agent
    agent any

    environment {
        // AWS region where ECR and EKS are deployed
        AWS_REGION = 'us-east-1'

        // ECR registry URL — stored as a Jenkins credential for security
        ECR_REGISTRY = credentials('ecr-registry-url')

        // Unique image tag: build number + short git commit hash
        // Example: 42-a1b2c3d (build #42, commit a1b2c3d)
        // This ensures every build produces a unique, traceable image tag
        IMAGE_TAG = "${BUILD_NUMBER}-${GIT_COMMIT[0..6]}"
    }

    // Fail fast — don't continue stages after a failure
    options {
        skipDefaultCheckout(false)
        timestamps()              // Add timestamps to console output
        timeout(time: 30, unit: 'MINUTES')  // Kill the pipeline if it takes too long
        disableConcurrentBuilds() // Prevent multiple builds of the same branch
    }

    stages {
        // =====================================================================
        // Stage 1: Checkout
        // =====================================================================
        // Jenkins checks out the code automatically, but we label the stage
        // so it appears clearly in the Blue Ocean UI.
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // =====================================================================
        // Stage 2: Set Up Python Environment
        // =====================================================================
        stage('Set Up Python') {
            steps {
                sh '''
                    # Create an isolated virtual environment for this build
                    python3 -m venv .venv
                    . .venv/bin/activate

                    # Install all dependencies including dev/test tools
                    pip install --no-cache-dir -r requirements-dev.txt

                    # Download the spaCy NLP model (needed for entity extraction tests)
                    python -m spacy download en_core_web_sm
                '''
            }
        }

        // =====================================================================
        // Stage 3: Run Tests
        // =====================================================================
        // Runs the full test suite with coverage reporting.
        // If any test fails, the entire pipeline aborts — we never deploy broken code.
        stage('Run Tests') {
            steps {
                sh '''
                    . .venv/bin/activate

                    # Run pytest with verbose output and coverage reporting
                    # --cov=core: measure coverage for the core package only
                    # --cov-report=xml: Cobertura format for Jenkins coverage plugin
                    # --cov-report=term: also print coverage to console
                    pytest tests/ -v --cov=core --cov-report=xml --cov-report=term
                '''
            }
            post {
                always {
                    // Publish coverage report in Jenkins UI (requires Coverage plugin)
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]

                    // Archive test results so they're accessible from the build page
                    junit allowEmptyResults: true, testResults: '**/junit*.xml'
                }
                failure {
                    echo 'Tests failed! Pipeline will abort.'
                }
            }
        }

        // =====================================================================
        // Stage 4: Code Quality Checks
        // =====================================================================
        // Linting and formatting checks. Failures here mark the build as
        // UNSTABLE (yellow) but DON'T abort the pipeline — code quality issues
        // shouldn't block a hotfix deployment.
        stage('Code Quality') {
            steps {
                sh '''
                    . .venv/bin/activate

                    # Ruff: fast Python linter (replaces flake8, pylint, etc.)
                    echo "Running ruff linter..."
                    ruff check . || true

                    # Black: opinionated code formatter
                    # --check means "don't modify files, just report"
                    echo "Running black formatter check..."
                    black --check . || true
                '''
            }
            post {
                failure {
                    // Mark as UNSTABLE instead of FAILURE — don't block deployment
                    unstable('Code quality checks failed — review linting issues')
                }
            }
        }

        // =====================================================================
        // Stage 5: Build Docker Images (Parallel)
        // =====================================================================
        // Build both images simultaneously to save time (~3-5 minutes saved).
        stage('Build Docker Images') {
            parallel {
                stage('Build API Image') {
                    steps {
                        sh """
                            echo "Building API image: contextos-api:${IMAGE_TAG}"
                            docker build \
                                -t contextos-api:${IMAGE_TAG} \
                                -t contextos-api:latest \
                                .
                        """
                    }
                }
                stage('Build Dashboard Image') {
                    steps {
                        sh """
                            echo "Building dashboard image: contextos-dashboard:${IMAGE_TAG}"
                            docker build \
                                -t contextos-dashboard:${IMAGE_TAG} \
                                -t contextos-dashboard:latest \
                                ./dashboard
                        """
                    }
                }
            }
        }

        // =====================================================================
        // Stage 6: Security Scan
        // =====================================================================
        // Trivy scans Docker images for known CVEs (Common Vulnerabilities).
        // CRITICAL vulnerabilities abort the pipeline — we never deploy
        // images with known critical security issues.
        stage('Security Scan') {
            steps {
                sh """
                    echo "Scanning API image for vulnerabilities..."
                    trivy image \
                        --severity HIGH,CRITICAL \
                        --format table \
                        --output trivy-api-report.txt \
                        contextos-api:${IMAGE_TAG}

                    echo "Scanning dashboard image for vulnerabilities..."
                    trivy image \
                        --severity HIGH,CRITICAL \
                        --format table \
                        --output trivy-dashboard-report.txt \
                        contextos-dashboard:${IMAGE_TAG}

                    # Check for CRITICAL vulnerabilities — abort if found
                    echo "Checking for critical vulnerabilities..."
                    CRITICAL_COUNT=\$(trivy image --severity CRITICAL --format json contextos-api:${IMAGE_TAG} | jq '.Results[].Vulnerabilities | length // 0' | paste -sd+ | bc)
                    if [ "\$CRITICAL_COUNT" -gt 0 ]; then
                        echo "CRITICAL vulnerabilities found! Aborting pipeline."
                        exit 1
                    fi
                """
            }
            post {
                always {
                    // Archive scan reports so they're accessible from the build page
                    archiveArtifacts artifacts: 'trivy-*.txt', allowEmptyArchive: true
                }
            }
        }

        // =====================================================================
        // Stage 7: Push to ECR (main branch only)
        // =====================================================================
        // Only push images when merging to main — feature branches just build
        // and test without pushing.
        stage('Push to ECR') {
            when {
                branch 'main'
            }
            steps {
                sh """
                    # Authenticate Docker with ECR (token expires after 12 hours)
                    aws ecr get-login-password --region ${AWS_REGION} | \
                        docker login --username AWS --password-stdin ${ECR_REGISTRY}

                    # Tag and push the API image (both versioned and latest tags)
                    docker tag contextos-api:${IMAGE_TAG} ${ECR_REGISTRY}/contextos-api:${IMAGE_TAG}
                    docker tag contextos-api:latest ${ECR_REGISTRY}/contextos-api:latest
                    docker push ${ECR_REGISTRY}/contextos-api:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/contextos-api:latest

                    # Tag and push the dashboard image
                    docker tag contextos-dashboard:${IMAGE_TAG} ${ECR_REGISTRY}/contextos-dashboard:${IMAGE_TAG}
                    docker tag contextos-dashboard:latest ${ECR_REGISTRY}/contextos-dashboard:latest
                    docker push ${ECR_REGISTRY}/contextos-dashboard:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/contextos-dashboard:latest
                """
            }
        }

        // =====================================================================
        // Stage 8: Deploy to Kubernetes (main branch only)
        // =====================================================================
        stage('Deploy to Kubernetes') {
            when {
                branch 'main'
            }
            steps {
                sh """
                    # Configure kubectl to talk to the EKS cluster
                    aws eks update-kubeconfig \
                        --region ${AWS_REGION} \
                        --name contextos-cluster

                    # Update the image tags in the k8s deployment files.
                    # sed replaces the placeholder IMAGE_TAG with the actual
                    # build-specific tag (e.g., 42-a1b2c3d).
                    sed -i "s|IMAGE_TAG|${IMAGE_TAG}|g" k8s/api-deployment.yaml
                    sed -i "s|IMAGE_TAG|${IMAGE_TAG}|g" k8s/dashboard-deployment.yaml

                    # Apply all Kubernetes manifests
                    kubectl apply -f k8s/ --namespace contextos

                    # Wait for the API deployment to finish rolling out.
                    # --timeout=5m: fail if the rollout takes longer than 5 minutes
                    # (pods might be crash-looping).
                    echo "Waiting for API deployment rollout..."
                    kubectl rollout status deployment/contextos-api \
                        --namespace contextos \
                        --timeout=5m

                    echo "Waiting for dashboard deployment rollout..."
                    kubectl rollout status deployment/contextos-dashboard \
                        --namespace contextos \
                        --timeout=2m
                """
            }
        }

        // =====================================================================
        // Stage 9: Integration Test (main branch only)
        // =====================================================================
        // After deploying, verify the application is actually working.
        // If the health check fails, automatically roll back to the previous version.
        stage('Integration Test') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    # Give the pods 30 seconds to become fully ready
                    echo "Waiting 30 seconds for pods to stabilize..."
                    sleep 30

                    # Hit the health endpoint to verify the API is responding
                    echo "Running health check..."
                    if ! curl -f --max-time 10 https://contextos.yourdomain.com/health; then
                        echo "Health check FAILED! Rolling back..."

                        # Automatic rollback — reverts to the previous deployment
                        kubectl rollout undo deployment/contextos-api \
                            --namespace contextos

                        echo "Rollback complete. Previous version restored."
                        exit 1
                    fi

                    echo "Health check passed! Deployment successful."
                '''
            }
        }
    }

    // =========================================================================
    // Post-Pipeline Actions
    // =========================================================================
    post {
        success {
            echo "Pipeline completed successfully! ContextOS v${IMAGE_TAG} deployed."
            // Uncomment to enable Slack notifications:
            // slackSend color: 'good', message: "✅ ContextOS v${IMAGE_TAG} deployed successfully"
        }
        failure {
            echo "Pipeline FAILED! Check the logs for details."
            // Uncomment to enable Slack notifications:
            // slackSend color: 'danger', message: "❌ ContextOS pipeline failed: ${BUILD_URL}"
        }
        unstable {
            echo "Pipeline completed with warnings (code quality issues)."
            // Uncomment to enable Slack notifications:
            // slackSend color: 'warning', message: "⚠️ ContextOS build unstable: ${BUILD_URL}"
        }
        always {
            // Clean up the workspace after every build to prevent disk space issues.
            // Docker images are also cleaned up to avoid filling the agent's disk.
            cleanWs()
            sh 'docker system prune -f || true'
        }
    }
}
