# backend/main.py

import os
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
import logging
import hmac
import hashlib

# Assuming worker tasks are defined relative to the project root or PYTHONPATH is set
# This might need adjustment based on actual project structure/deployment
try:
    from worker.tasks import analyze_pull_request
except ImportError:
    # Fallback for different structure if needed
    # This indicates a potential issue with how modules are discovered
    logging.warning("Could not import worker.tasks directly, check PYTHONPATH or structure.")
    # As a temporary measure for development, might define a placeholder
    class PlaceholderTask:
        def delay(self, *args, **kwargs):
            logging.warning("analyze_pull_request task not imported, using placeholder delay.")
    analyze_pull_request = PlaceholderTask()


# Load environment variables from .env file for local development
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CodeGuardian AI Backend",
    description="Handles GitHub webhooks, authentication, and orchestrates AI code reviews.",
    version="0.1.0"
)

# --- GitHub Webhook Verification ---
def verify_github_signature(payload_body: bytes, signature_header: str):
    """Verify that the payload was sent from GitHub using the WEBHOOK_SECRET."""
    if not signature_header:
        logger.warning("X-Hub-Signature-256 header is missing!")
        return False
    
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        logger.error("GITHUB_WEBHOOK_SECRET is not configured. Cannot verify signature.")
        # In a real app, you might want to raise an error or deny the request
        # For now, we'll log and potentially allow if secret is missing (less secure)
        return True # Or False depending on security posture

    hash_object = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        logger.warning("Request signature does not match expected signature!")
        return False
    return True
# ----------------------------------

@app.get("/health", tags=["Status"])
async def health_check():
    """Basic health check endpoint."""
    logger.info("Health check endpoint called.")
    return {"status": "ok"}

@app.post("/webhook/github", tags=["GitHub"])
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handles incoming GitHub webhooks (e.g., pull_request events)."""
    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # --- Signature Verification ---
    # Uncomment in production after setting GITHUB_WEBHOOK_SECRET
    # if not verify_github_signature(payload_bytes, signature):
    #     logger.error("Webhook signature verification failed.")
    #     raise HTTPException(status_code=403, detail="Invalid signature")
    # logger.info("Webhook signature verified successfully.")
    # -----------------------------

    try:
        payload = await request.json() # Parse JSON after reading body for signature check
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    logger.info(f"Received GitHub webhook event: {event_type}, Delivery ID: {delivery_id}")

    if event_type == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        installation_id = payload.get("installation", {}).get("id")

        if action in ["opened", "synchronize", "reopened"]:
            pr_number = pr.get("number")
            repo_full_name = repo.get("full_name")
            pr_head_sha = pr.get("head", {}).get("sha")

            if not all([pr_number, repo_full_name, installation_id, pr_head_sha]):
                logger.warning("Missing required information in pull_request payload.")
                return {"status": "ignored", "reason": "Missing data"}

            logger.info(f"Processing pull_request event (action: {action}) for {repo_full_name}# {pr_number}")
            
            # Prepare data for the Celery task
            task_data = {
                "event_type": event_type,
                "action": action,
                "repo_full_name": repo_full_name,
                "pr_number": pr_number,
                "pr_head_sha": pr_head_sha,
                "installation_id": installation_id,
                "delivery_id": delivery_id # For tracing
            }

            # Enqueue job for AI analysis using Celery
            # Using background_tasks.add_task for FastAPI integration, 
            # but direct .delay() call is standard Celery practice.
            # Choose one method based on deployment strategy.
            try:
                analyze_pull_request.delay(task_data)
                logger.info(f"Enqueued analysis task for {repo_full_name}# {pr_number}")
            except Exception as e:
                logger.error(f"Failed to enqueue Celery task: {e}", exc_info=True)
                # Depending on the error, might need specific handling
                raise HTTPException(status_code=500, detail="Failed to enqueue analysis task")

        else:
            logger.info(f"Ignoring pull_request action: {action}")

    elif event_type == "installation":
        action = payload.get("action")
        logger.info(f"Processing installation event (action: {action})")
        # TODO: Handle app installation/uninstallation logic (e.g., update DB)
        pass
    elif event_type == "installation_repositories":
        action = payload.get("action")
        logger.info(f"Processing installation_repositories event (action: {action})")
        # TODO: Handle repositories being added/removed from installation
        pass
    elif event_type == "ping":
        logger.info("Received ping event from GitHub.")
        return {"status": "pong"}
    else:
        logger.info(f"Ignoring unhandled GitHub event type: {event_type}")

    return {"status": "received"}

# TODO: Add endpoint for GitHub App OAuth callback (/auth/github/callback)
# This will handle the user authorization flow after installing the app.

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for local development...")
    # Ensure .env is loaded if running directly
    load_dotenv()
    # Use environment variable for port or default to 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) # Added reload=True for dev

