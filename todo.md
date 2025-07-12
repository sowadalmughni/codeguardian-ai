# CodeGuardian AI - Python Security MVP Todo List

This list outlines the steps to build the initial showcase-ready Minimum Viable Product (MVP) focused on Python code security reviews via a GitHub Action.

- [ ] **Phase 1: Setup & Core Backend**
    - [X] 1.1: Initialize project structure (backend, worker, infra, frontend directories).
    - [X] 1.2: Set up FastAPI application skeleton.
    - [X] 1.3: Configure basic logging and environment variable handling (using python-dotenv for local dev).
    - [ ] 1.4: Set up AWS Secrets Manager for storing sensitive keys (e.g., GitHub App credentials, LLM API key).
    - [ ] 1.5: Configure AWS SQS queue for asynchronous job processing.
    - [ ] 1.6: Set up basic PostgreSQL database schema (e.g., for tracking scan jobs, repo installations - using placeholder/local DB initially).

- [ ] **Phase 2: GitHub Integration**
    - [ ] 2.1: Register a new GitHub App for CodeGuardian.
    - [ ] 2.2: Implement GitHub App installation flow (OAuth callback handler in FastAPI).
    - [X] 2.3: Implement webhook handler in FastAPI to receive `pull_request` events (opened, synchronize).
    - [ ] 2.4: Securely store installation tokens/details (potentially linked to DB records).
    - [ ] 2.5: Implement logic to authenticate with GitHub API using installation tokens.

- [ ] **Phase 3: AI Worker & Analysis**
    - [X] 3.1: Develop AI Worker (e.g., Celery task or Lambda function) structure.
    - [ ] 3.2: Implement logic within the worker to fetch PR diff content using GitHub API.
    - [X] 3.3: Develop prompt engineering strategy for Python security vulnerability detection using an LLM (e.g., GPT-4o).
    - [X] 3.4: Implement LLM API call logic within the worker (handle API keys securely via Secrets Manager).
    - [X] 3.5: Implement logic to parse LLM response and identify actionable security findings (vulnerability type, location, suggestion).

- [ ] **Phase 4: Feedback & Frontend**
    - [X] 4.1: Implement logic within the worker (or a subsequent task) to post findings as comments on the GitHub PR.
    - [ ] 4.2: Ensure comments are posted on the correct lines of the diff.
    - [X] 4.3: Apply behavioral principles to comment formatting (concise, clear, link to potential future details).
    - [X] 4.4: Develop a minimal landing/status page using React/Next.js (showcase app purpose, link to GitHub App installation).

- [ ] **Phase 5: Deployment & Testing**
    - [X] 5.1: Set up Infrastructure as Code (IaC) using Pulumi (Python) for AWS resources (API Gateway, SQS, Lambda/ECS, RDS placeholder/minimal).
    - [ ] 5.2: Configure CI/CD pipeline (e.g., GitHub Actions) for automated testing and deployment.
    - [ ] 5.3: Deploy backend API, worker, and frontend to AWS.
    - [ ] 5.4: Configure API Gateway to route webhook traffic to the FastAPI application.
    - [ ] 5.5: Conduct end-to-end testing using a sample Python repository with known vulnerabilities.
    - [ ] 5.6: Refine prompts and parsing based on testing results.

- [ ] **Phase 6: Finalization**
    - [ ] 6.1: Review code quality, security, and adherence to guidelines.
    - [ ] 6.2: Prepare documentation for installation and usage.
    - [ ] 6.3: Verify all todo items are complete.
