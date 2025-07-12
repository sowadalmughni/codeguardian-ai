# CodeGuardian AI - MVP Showcase

This repository contains the source code for the Minimum Viable Product (MVP) of CodeGuardian AI, an AI-powered code security review tool designed to integrate with GitHub Pull Requests, initially focusing on Python.

This MVP was built based on the technical blueprint and guidelines provided.

## Project Structure

```
/codeguardian
├── backend/         # FastAPI application (webhook handler, API)
│   ├── main.py
│   └── requirements.txt
├── worker/          # Celery worker (AI analysis task)
│   ├── celery_app.py
│   ├── tasks.py
│   └── requirements.txt
├── frontend/        # Next.js landing page
│   ├── pages/
│   │   └── index.js
│   ├── public/
│   ├── styles/
│   │   └── Home.module.css
│   └── package.json # (Needs to be created: npm init -y; npm install next react react-dom)
├── infra/           # Pulumi Infrastructure as Code (AWS)
│   ├── __main__.py
│   └── requirements.txt
├── .env.example     # Example environment variables
└── README.md        # This file
```

## Core Functionality (Implemented)

*   **Backend (FastAPI):** Receives GitHub `pull_request` webhooks, verifies signatures (optional, requires secret), parses payload, and enqueues analysis jobs to a queue (simulated via Celery/Redis locally, SQS in IaC).
*   **Worker (Celery):** Defines a task structure to:
    *   Simulate fetching GitHub installation tokens.
    *   Simulate fetching PR diff content.
    *   Prepare a prompt for security analysis.
    *   Call an LLM API (OpenAI GPT-4o) with the prompt (requires API key).
    *   Parse the LLM's JSON response for findings.
    *   Simulate posting findings as comments back to the GitHub PR.
*   **Frontend (Next.js):** A minimal landing page explaining the service and providing a link to install the (yet to be created) GitHub App.
*   **Infrastructure (Pulumi):** Python scripts to define the necessary AWS infrastructure (API Gateway, Lambda for backend/worker, SQS, Secrets Manager, basic RDS placeholder, S3 for frontend). Note: This defines the infrastructure; actual deployment requires AWS credentials and Pulumi CLI execution.

## Setup & Deployment Instructions

**1. Prerequisites:**

*   Python 3.11+
*   Node.js & npm (for frontend)
*   Docker (for local Redis/Postgres, optional)
*   Pulumi CLI (for deploying infrastructure)
*   AWS Account & Credentials (configured for Pulumi/AWS CLI)
*   GitHub Account

**2. Create GitHub App:**

*   Go to GitHub Settings -> Developer settings -> GitHub Apps -> New GitHub App.
*   Configure the app:
    *   **Homepage URL:** (Your deployed frontend URL)
    *   **Webhook URL:** (Your deployed API Gateway endpoint + `/webhook/github`)
    *   **Webhook Secret:** Generate a strong secret.
    *   **Permissions:**
        *   Repository: `Pull requests` (Read & Write), `Contents` (Read-only)
        *   Organization: `Members` (Read-only) - If needed for org installations
    *   **Subscribe to events:** `Pull request`, `Installation`, `Installation repositories`.
*   Generate a **Private Key** and download it.
*   Note down the **App ID**, **Client ID**, **Client Secret**, and the **Webhook Secret**.

**3. Configure Environment Variables:**

*   Copy `.env.example` to `.env` in the `/codeguardian` root directory.
*   Fill in the values obtained from your GitHub App (Step 2).
*   Add your `OPENAI_API_KEY`.
*   Update `DATABASE_URL` and `REDIS_URL` if running locally (e.g., using Docker Compose for Postgres/Redis) or leave placeholders if deploying directly to AWS.

**4. Local Development (Optional):**

*   **Backend:**
    *   `cd backend`
    *   `python -m venv venv`
    *   `source venv/bin/activate`
    *   `pip install -r requirements.txt`
    *   `uvicorn main:app --reload --port 8000` (Requires `.env` in `backend` or project root)
*   **Worker:**
    *   Requires Redis running (e.g., `docker run -d -p 6379:6379 redis`)
    *   `cd worker`
    *   `python -m venv venv`
    *   `source venv/bin/activate`
    *   `pip install -r requirements.txt`
    *   `celery -A worker.celery_app worker --loglevel=info` (Requires `.env` in `worker` or project root)
*   **Frontend:**
    *   `cd frontend`
    *   `npm init -y`
    *   `npm install next react react-dom`
    *   `npm run dev`

**5. Deploy Infrastructure (AWS via Pulumi):**

*   `cd infra`
*   `python -m venv venv`
*   `source venv/bin/activate`
*   `pip install -r requirements.txt`
*   `pulumi login`
*   `pulumi stack init <your-stack-name>` (e.g., `dev`)
*   `pulumi config set aws:region <your-aws-region>` (e.g., `us-east-1`)
*   **(IMPORTANT)** Update the placeholder secrets in `infra/__main__.py` (within the `aws.secretsmanager.Secret` resource) with your actual GitHub App credentials and OpenAI key, OR configure them using Pulumi secrets (`pulumi config set --secret <key> <value>`) and modify the script to use `config.require_secret()`.
*   `pulumi up` - Review the plan and confirm deployment.
*   Note the outputs, especially the `api_endpoint` and `frontend_bucket_website_endpoint`.

**6. Deploy Application Code:**

*   **Backend/Worker Lambda:** The Pulumi script assumes packaging the code into zip files (`../backend`, `../worker`). You need to create these zip archives or, preferably, modify the Pulumi script to use Docker image deployments for Lambda (requires Dockerfiles in backend/worker directories).
*   **Frontend:**
    *   `cd frontend`
    *   `npm run build` (This creates an `out` directory for static export if configured, or `.next` for standard build)
    *   Upload the contents of the build output directory (`out` or `.next/static`) to the S3 bucket created by Pulumi (`pulumi stack output frontend_bucket_name`). Use the AWS CLI: `aws s3 sync ./out s3://<bucket-name> --delete`

**7. Update GitHub App Settings:**

*   Update the **Webhook URL** in your GitHub App settings to the `api_endpoint` from the Pulumi output.
*   Update the **Homepage URL** to the S3 website endpoint or your CloudFront distribution URL (if you add CloudFront).

**8. Testing:**

*   Install the GitHub App on a test repository containing Python code.
*   Create a Pull Request with changes to Python files.
*   Check the backend Lambda logs (CloudWatch) for webhook processing.
*   Check the worker Lambda logs for analysis task execution.
*   Check the PR for comments posted by CodeGuardian AI.

## Limitations & Next Steps

*   **Placeholders:** The current code uses placeholders for actual GitHub API calls (fetching diffs, posting comments) and token generation. These need to be implemented using a GitHub SDK (like `PyGithub` or `requests` with manual JWT generation).
*   **Error Handling:** Robust error handling, retries, and dead-letter queue logic need refinement.
*   **Security:** Implement proper GitHub webhook signature verification (requires `GITHUB_WEBHOOK_SECRET`). Enhance IAM permissions following the principle of least privilege. Add input validation.
*   **Database Integration:** The database schema is basic. Need to implement logic to store installation details, scan results, user data, etc.
*   **Frontend:** The frontend is minimal. Needs development for user login, dashboard, repository management, viewing scan results, etc., as per the blueprint.
*   **AI Prompting & Parsing:** The LLM prompt is basic. Requires significant iteration and testing for accuracy, reliability, and handling different vulnerability types. Parsing logic needs to be robust against variations in LLM output.
*   **Testing:** Comprehensive unit, integration, and end-to-end tests are required.
*   **Scalability:** Review resource configurations (Lambda memory/timeout, DB instance class, SQS settings) for production scale.
*   **CI/CD:** Implement a CI/CD pipeline (e.g., GitHub Actions) for automated testing and deployment.

This MVP provides a solid foundation. The next steps involve replacing placeholders with real implementations, refining the AI components, building out the user-facing frontend, and thorough testing.
