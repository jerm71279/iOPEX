import hashlib
import hmac
import httpx
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEMO_SUBMISSION_PREFIX = "demo-"


class DocuSealClient:
    def __init__(self, base_url: str, api_key: str, webhook_secret: str = "",
                 template_id: str = "", demo_mode: bool = False):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.template_id = template_id
        # Demo mode: use built-in /sign/{contract_id} page instead of DocuSeal
        self.demo_mode = demo_mode or not template_id
        self._headers = {"X-Auth-Token": api_key, "Content-Type": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api{path}"

    def create_submission(self, contract_id: str, client_email: str, client_name: str,
                          app_base_url: str = "http://localhost:8000") -> dict:
        """
        Create a signing submission.
        - Real mode: POST /api/submissions against a pre-configured template_id
        - Demo mode: return a synthetic submission with a local signing URL
        """
        if self.demo_mode or not self.api_key:
            return self._demo_submission(contract_id, client_name, client_email, app_base_url)

        payload = {
            "template_id": int(self.template_id),
            "submitters": [
                {"email": client_email, "name": client_name, "role": "Client"}
            ],
            "message": {
                "subject": "Please sign your Service Agreement",
                "body": "Your contract is ready for signature. Click the link below to review and sign."
            }
        }
        resp = httpx.post(self._url("/submissions"), json=payload,
                          headers=self._headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # DocuSeal returns {"id": ..., "submitters": [{"slug": ..., "embed_src": ...}]}
        submitters = data.get("submitters") or []
        embed_src = submitters[0].get("embed_src", "") if submitters else ""
        return {
            "id": data.get("id"),
            "signing_url": embed_src,
            "mode": "docuseal",
        }

    def _demo_submission(self, contract_id: str, client_name: str,
                         client_email: str, app_base_url: str) -> dict:
        """Synthetic submission for demo mode — uses built-in signing page."""
        submission_id = f"{DEMO_SUBMISSION_PREFIX}{contract_id}"
        signing_url = f"{app_base_url}/sign/{contract_id}"
        logger.info(
            "[%s] Demo mode: signing URL → %s (no DocuSeal template configured)",
            contract_id, signing_url
        )
        return {
            "id": submission_id,
            "signing_url": signing_url,
            "mode": "demo",
        }

    def is_demo_submission(self, submission_id) -> bool:
        return str(submission_id).startswith(DEMO_SUBMISSION_PREFIX)

    def get_submission(self, submission_id) -> dict:
        if self.is_demo_submission(submission_id):
            return {"id": submission_id, "status": "pending", "mode": "demo"}
        resp = httpx.get(self._url(f"/submissions/{submission_id}"),
                         headers=self._headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def poll_until_complete(self, submission_id, poll_interval: int = 30,
                            timeout: int = 172800) -> dict:
        """Poll submission status until completed or timeout (default 48h)."""
        if self.is_demo_submission(submission_id):
            # Demo: never auto-completes via polling — caller must use notify_complete
            raise RuntimeError("Demo submission cannot be polled — use /sign/{id} page")

        start = time.time()
        while time.time() - start < timeout:
            data = self.get_submission(submission_id)
            status = data.get("status")
            if status == "completed":
                return data
            if status in ("expired", "declined"):
                raise RuntimeError(f"Submission {submission_id} ended with status: {status}")
            logger.info("Submission %s status: %s — polling in %ds",
                        submission_id, status, poll_interval)
            time.sleep(poll_interval)
        raise TimeoutError(f"Submission {submission_id} did not complete within {timeout}s")

    def download_document(self, submission_id) -> Optional[bytes]:
        """Download the completed signed document as PDF bytes."""
        if self.is_demo_submission(submission_id):
            return None  # Demo: caller copies the generated PDF
        submission = self.get_submission(submission_id)
        doc_url = submission.get("documents", [{}])[0].get("url")
        if not doc_url:
            raise ValueError(f"No document URL in submission {submission_id}")
        resp = httpx.get(doc_url, timeout=30)
        resp.raise_for_status()
        return resp.content

    def update_webhook_url(self, webhook_url: str):
        """Update the global webhook URL in DocuSeal settings."""
        payload = {"webhook_url": webhook_url}
        resp = httpx.put(self._url("/account"), json=payload,
                         headers=self._headers, timeout=15)
        if resp.status_code in (200, 201, 204):
            logger.info("DocuSeal webhook URL set to: %s", webhook_url)
        else:
            logger.warning("Could not set webhook URL: %s %s", resp.status_code, resp.text)

    def validate_webhook(self, payload_bytes: bytes, signature_header: str) -> bool:
        """HMAC-SHA256 validation of incoming DocuSeal webhook."""
        if not self.webhook_secret:
            return True  # No secret configured — skip validation in dev
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)
