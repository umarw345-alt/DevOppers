"""Provider-neutral contracts for Apple Wallet and Google Wallet issuance.

Concrete providers will be added after the portfolio publishing URL contract
and provider credentials are available. Keeping this contract independent of
FastAPI makes it straightforward to test pass issuance with a fake provider.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlparse
from uuid import UUID


class WalletPlatform(StrEnum):
    APPLE = "apple"
    GOOGLE = "google"


@dataclass(frozen=True)
class WalletPassRequest:
    """Validated input shared by all wallet providers."""

    user_id: UUID
    portfolio_id: UUID
    artifact_version: str
    public_url: str
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.public_url, str) or not self.public_url.strip():
            raise ValueError("public_url cannot be empty")

        parsed = urlparse(self.public_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("public_url must be an absolute http:// or https:// URL")


@dataclass(frozen=True)
class WalletPassResult:
    """Provider output returned to the API layer, never directly to storage."""

    platform: WalletPlatform
    provider_object_id: str
    qr_value: str
    content_type: str | None = None
    filename: str | None = None
    pass_bytes: bytes | None = None
    add_to_wallet_url: str | None = None


class WalletPassProvider(Protocol):
    platform: WalletPlatform

    def issue(self, request: WalletPassRequest) -> WalletPassResult:
        """Create a provider artifact for a published portfolio URL."""


class WalletProviderNotConfigured(RuntimeError):
    """Raised when provider credentials or signing configuration are absent."""
