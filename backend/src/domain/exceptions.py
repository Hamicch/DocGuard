from __future__ import annotations


class DocGuardError(Exception):
    """Base exception for all application errors."""


class WebhookVerificationError(DocGuardError):
    """HMAC signature on the incoming GitHub webhook did not match."""


class GitHubAPIError(DocGuardError):
    """GitHub API returned an unexpected error or rate-limit response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuditRunError(DocGuardError):
    """An unrecoverable error occurred during an audit run."""

    def __init__(self, message: str, run_id: str | None = None) -> None:
        super().__init__(message)
        self.run_id = run_id


class LLMJudgmentError(DocGuardError):
    """LLM returned an invalid or unparseable structured response."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response


class RepositoryError(DocGuardError):
    """A database operation failed."""


class ConfigurationError(DocGuardError):
    """A required configuration value is missing or invalid."""
