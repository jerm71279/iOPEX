from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # PDFShift (optional — falls back to local PDF generation if not set)
    pdfshift_api_key: str = ""

    # DocuSeal
    docuseal_base_url: str = "http://localhost:3000"
    docuseal_api_key: str = ""
    docuseal_webhook_secret: str = ""
    docuseal_template_id: str = ""   # Pre-created template ID (free tier — create once in UI)
    docuseal_use_polling: bool = False
    docuseal_poll_interval: int = 30  # seconds

    # Demo signing mode: when True, /sign/{id} page is used instead of DocuSeal
    # Auto-enabled when docuseal_template_id is not set
    demo_signing_mode: bool = False

    # Gmail (optional for demo — intake via /trigger/upload, emails logged if not set)
    gmail_user: str = ""
    gmail_app_password: str = ""
    gmail_imap_host: str = "imap.gmail.com"
    gmail_smtp_host: str = "smtp.gmail.com"
    gmail_smtp_port: int = 587

    # Recipients
    customer_email: str = ""
    revops_email: str

    # Provider identity (shown in contract template)
    provider_name: str = "Service Provider"
    provider_email: str = ""
    provider_signatory: str = "Authorised Signatory"

    # App
    app_base_url: str = "http://localhost:8000"
    output_dir: Path = Path("output")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def state_dir(self) -> Path:
        return self.output_dir / "state"

    @property
    def archive_dir(self) -> Path:
        return self.output_dir / "archive"

    @property
    def audit_file(self) -> Path:
        return self.output_dir / "audit" / "audit.jsonl"

    def ensure_dirs(self):
        for d in [self.state_dir, self.archive_dir, self.output_dir / "audit",
                  self.output_dir / "state" / "raw"]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
