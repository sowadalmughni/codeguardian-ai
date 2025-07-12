# worker/tasks.py

import os
import time
import logging
from .celery_app import app
from openai import OpenAI, RateLimitError, APIError
import requests # Placeholder for GitHub API calls
from dotenv import load_dotenv

# Load .env for local dev if needed (Celery might load it differently)
load_dotenv()

logger = logging.getLogger(__name__)

# --- Configuration ---
# In production, use dependency injection or a config object
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o") # Or your preferred model
GITHUB_API_BASE_URL = "https://api.github.com"

# Initialize OpenAI client (consider initializing once per worker process)
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY not found in environment. LLM calls will fail.")
    openai_client = None

# --- Helper Functions (Placeholders/Simplified) ---

def get_github_installation_token(installation_id):
    """Placeholder: Fetches a short-lived installation token."""
    # In reality, this involves creating a JWT signed with the app's private key
    # and exchanging it for an installation token.
    logger.info(f"Simulating fetching token for installation {installation_id}")
    # Use a placeholder token for simulation if needed, but real calls require a valid one.
    # return os.getenv("PLACEHOLDER_GITHUB_TOKEN")
    return "ghs_placeholder_token" # Extremely temporary placeholder

def fetch_pr_diff(token, repo_full_name, pr_number):
    """Placeholder: Fetches the diff content of a Pull Request."""
    # url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/pulls/{pr_number}"
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Accept": "application/vnd.github.v3.diff"
    # }
    # response = requests.get(url, headers=headers)
    # response.raise_for_status() # Raise exception for bad status codes
    # return response.text
    logger.info(f"Simulating fetching diff for {repo_full_name}# {pr_number}")
    return """diff --git a/vulnerable.py b/vulnerable.py
index e69de29..d1f2e7a 100644
--- a/vulnerable.py
+++ b/vulnerable.py
@@ -0,0 +1,5 @@
+import os
+
+def execute_command(user_input):
+    # Potential command injection vulnerability
+    os.system(f"echo User input: {user_input}")
""" # Sample Python diff

def create_security_analysis_prompt(diff_content):
    """Creates the prompt for the LLM to analyze the diff for security issues."""
    # This prompt needs significant refinement and testing
    prompt = f"""
Analyze the following code diff for potential security vulnerabilities in Python. Focus specifically on identifying issues like command injection, SQL injection, cross-site scripting (XSS), insecure deserialization, improper access control, and use of weak cryptographic algorithms. For each vulnerability found, provide:
1. The file path (if available in the diff).
2. The line number where the vulnerability occurs (relative to the diff hunk).
3. A brief description of the vulnerability type.
4. A clear explanation of the potential security risk.
5. A specific suggestion for how to fix the vulnerability.

Format the output as a JSON list of findings. Each finding should be an object with keys: "file_path", "line", "type", "risk", "suggestion". If no vulnerabilities are found, return an empty list.

Code Diff:
```diff
{diff_content}
```

JSON Findings:
"""
    return prompt

def call_llm_api(prompt):
    """Calls the configured LLM API (OpenAI)."""
    if not openai_client:
        raise ValueError("OpenAI client not initialized. Check API key.")
    
    logger.info(f"Sending prompt to LLM model: {LLM_MODEL_NAME}")
    try:
        response = openai_client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert security code reviewer specializing in Python."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Lower temperature for more deterministic results
            max_tokens=1024, # Adjust as needed
            response_format={"type": "json_object"} # Request JSON output if model supports it
        )
        logger.info("Received LLM response.")
        # Ensure response content is accessed correctly
        content = response.choices[0].message.content
        return content
    except RateLimitError as e:
        logger.warning(f"LLM rate limit exceeded: {e}. Retrying task.")
        raise # Re-raise to trigger Celery retry
    except APIError as e:
        logger.error(f"LLM API error: {e}")
        raise # Re-raise to trigger Celery retry
    except Exception as e:
        logger.error(f"Unexpected error calling LLM: {e}", exc_info=True)
        raise # Re-raise to trigger Celery retry

def parse_llm_response(response_content):
    """Parses the JSON response from the LLM."""
    import json
    try:
        # Assuming the LLM returns a JSON string within the content
        findings_data = json.loads(response_content)
        # Basic validation
        if isinstance(findings_data, dict) and "findings" in findings_data and isinstance(findings_data["findings"], list):
             return findings_data["findings"]
        elif isinstance(findings_data, list):
             # If the response is directly the list
             return findings_data
        else:
             logger.warning(f"LLM response JSON structure unexpected: {response_content}")
             return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}\nResponse content:\n{response_content}")
        return [] # Return empty list on parsing error
    except Exception as e:
        logger.error(f"Error processing LLM response: {e}", exc_info=True)
        return []

def post_pr_comment(token, repo_full_name, pr_number, comment_body, commit_id, path, line):
    """Placeholder: Posts a single review comment to a PR."""
    # url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/pulls/{pr_number}/comments"
    # headers = {
    #     "Authorization": f"Bearer {token}",
    #     "Accept": "application/vnd.github.v3+json"
    # }
    # data = {
    #     "body": comment_body,
    #     "commit_id": commit_id,
    #     "path": path,
    #     "line": line # Line number within the diff hunk
    # }
    # response = requests.post(url, headers=headers, json=data)
    # response.raise_for_status()
    logger.info(f"Simulating posting comment to {repo_full_name}# {pr_number} on path {path}, line {line}")
    pass

# --- Celery Task ---

@app.task(bind=True, max_retries=3, default_retry_delay=60) # Added retry logic
def analyze_pull_request(self, pr_data):
    """Celery task to analyze a pull request for security vulnerabilities."""
    repo_full_name = pr_data.get("repo_full_name")
    pr_number = pr_data.get("pr_number")
    installation_id = pr_data.get("installation_id")
    commit_id = pr_data.get("pr_head_sha") # Use head SHA for comments

    log_prefix = f"PR Analysis - {repo_full_name}# {pr_number}:"

    try:
        logger.info(f"{log_prefix} Starting analysis.")

        if not installation_id:
            raise ValueError("Missing installation_id")
        if not openai_client:
             raise ValueError("OpenAI client not configured.")

        # 1. Get GitHub Token (Placeholder)
        github_token = get_github_installation_token(installation_id)
        if not github_token:
             raise ValueError("Failed to get GitHub token")

        # 2. Fetch PR Diff (Placeholder)
        diff_content = fetch_pr_diff(github_token, repo_full_name, pr_number)
        if not diff_content:
            logger.info(f"{log_prefix} No diff content found or fetched.")
            return {"status": "success", "findings_count": 0}
        logger.info(f"{log_prefix} Fetched PR diff.")

        # 3. Prepare & Call LLM
        prompt = create_security_analysis_prompt(diff_content)
        llm_response_content = call_llm_api(prompt)
        if not llm_response_content:
            raise ValueError("Received empty response from LLM")
        logger.info(f"{log_prefix} Received LLM response.")

        # 4. Parse LLM Response
        findings = parse_llm_response(llm_response_content)
        logger.info(f"{log_prefix} Parsed {len(findings)} findings from LLM response.")

        # 5. Post Findings as PR Comments (Placeholder)
        if findings:
            logger.info(f"{log_prefix} Posting {len(findings)} findings to PR...")
            for finding in findings:
                # Construct comment body (apply behavioral principles here - concise, actionable)
                comment_body = (
                    f"**CodeGuardian AI Security Finding:**\n\n" 
                    f"**Type:** {finding.get('type', 'N/A')}\n" 
                    f"**Risk:** {finding.get('risk', 'N/A')}\n\n" 
                    f"**Suggestion:** {finding.get('suggestion', 'N/A')}"
                )
                # Post comment (ensure path and line are correctly extracted/mapped)
                post_pr_comment(
                    github_token,
                    repo_full_name,
                    pr_number,
                    comment_body,
                    commit_id,
                    finding.get("file_path", "unknown_file"), # Requires robust path extraction
                    finding.get("line", 1) # Requires robust line mapping
                )
                time.sleep(0.5) # Avoid hitting rate limits when posting multiple comments
            logger.info(f"{log_prefix} Finished posting findings.")
        else:
            logger.info(f"{log_prefix} No findings to report.")
            # Optionally post a "no issues found" comment or status check

        logger.info(f"{log_prefix} Successfully completed analysis.")
        return {"status": "success", "findings_count": len(findings)}

    except Exception as e:
        logger.error(f"{log_prefix} Error during analysis: {e}", exc_info=True)
        try:
            # Retry the task if it's a potentially transient error (e.g., network, rate limit)
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"{log_prefix} Max retries exceeded. Task failed permanently.")
            # Optionally notify someone or update status in DB
            return {"status": "failed", "message": f"Max retries exceeded: {e}"}
        return {"status": "retrying", "message": str(e)}


