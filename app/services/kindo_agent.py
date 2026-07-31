import os
import json
import time
import logging
import requests

logger = logging.getLogger(__name__)

KINDO_API_URL = "https://api.kindo.ai/v1/agents/runs"
POLL_INTERVAL = 2
MAX_POLL_TIME = int(os.environ.get("APP_AGENT_POLL_TIMEOUT_SEC", "120"))


def _get_config():
    token = os.environ.get("KINDO_API_TOKEN", "")
    agent_id = os.environ.get("KINDO_AGENT_ID", "")
    return token, agent_id


def is_configured():
    token, agent_id = _get_config()
    return bool(token) and bool(agent_id)


def build_request_payload(operation, entity_id, input_data, organization="",
                          detail_level="detailed", include_recommendations=True):
    return {
        "operation": operation,
        "entity_id": str(entity_id),
        "input_data": {
            "description": input_data.get("description", ""),
            "records": input_data.get("records", []),
            "context": {
                "organization": organization,
                "policy": input_data.get("policy", ""),
                "time_range": input_data.get("time_range", ""),
            },
        },
        "options": {
            "detail_level": detail_level,
            "include_recommendations": include_recommendations,
            "return_confidence": True,
        },
    }


def run_agent(payload):
    """Submit a request to the Kindo agent, poll until done, return parsed result."""
    token, agent_id = _get_config()
    if not token or not agent_id:
        return {"status": "error", "summary": "Kindo agent not configured. Set KINDO_API_TOKEN and KINDO_AGENT_ID."}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "agent_id": agent_id,
        "inputs": [{"name": "request", "value": json.dumps(payload)}],
    }

    try:
        resp = requests.post(KINDO_API_URL, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        run_data = resp.json()
    except requests.RequestException as exc:
        logger.exception("Kindo agent submission failed: %s", exc)
        return {"status": "error", "summary": f"Failed to submit agent request: {exc}"}

    run_id = run_data.get("id") or run_data.get("run_id")
    if not run_id:
        return {"status": "error", "summary": "No run ID returned from Kindo API."}

    # Poll for completion
    poll_url = f"{KINDO_API_URL}/{run_id}"
    start = time.time()
    while time.time() - start < MAX_POLL_TIME:
        try:
            poll_resp = requests.get(poll_url, headers=headers, timeout=15)
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()
        except requests.RequestException as exc:
            logger.warning("Poll error: %s", exc)
            time.sleep(POLL_INTERVAL)
            continue

        status = poll_data.get("status", "")
        if status in ("completed", "success", "done"):
            return _parse_result(poll_data)
        if status in ("failed", "error", "cancelled"):
            return {"status": "error", "summary": f"Agent run ended with status: {status}"}

        time.sleep(POLL_INTERVAL)

    return {"status": "error", "summary": "Agent run timed out."}


def _parse_result(poll_data):
    """Extract the agent's JSON result from the run response."""
    output = poll_data.get("output") or poll_data.get("result") or poll_data.get("response", "")
    if isinstance(output, dict):
        return output

    if isinstance(output, str):
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass
        # Try to extract JSON from markdown fenced block
        if "```" in output:
            parts = output.split("```")
            for part in parts:
                clean = part.strip()
                if clean.startswith("json"):
                    clean = clean[4:].strip()
                try:
                    return json.loads(clean)
                except (json.JSONDecodeError, ValueError):
                    continue

        return {
            "status": "ok",
            "summary": output[:1000],
            "score": 0.0,
            "risk_level": "informational",
            "findings": [],
            "recommendations": [],
            "confidence": 0.0,
        }

    return {"status": "error", "summary": "Unexpected response format from agent."}
