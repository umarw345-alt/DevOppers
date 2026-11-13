"""Apple Wallet pass document and package-building primitives.

This module currently builds the unsigned source files. A real Wallet pass
still needs a PKCS#7 signature and ZIP packaging before it can be installed.
"""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json

from wallets.providers import (
    WalletPassProvider,
    WalletPassRequest,
    WalletPassResult,
    WalletPlatform,
    WalletProviderNotConfigured,
)


@dataclass(frozen=True)
class ApplePassSettings:
    pass_type_identifier: str
    team_identifier: str
    organization_name: str


def generate_pass_json(
    request: WalletPassRequest,
    settings: ApplePassSettings,
) -> str:
    """Return the deterministic JSON document for ``pass.json``."""

    data = {
        "formatVersion": 1,
        "passTypeIdentifier": settings.pass_type_identifier,
        "serialNumber": str(request.portfolio_id),
        "teamIdentifier": settings.team_identifier,
        "organizationName": settings.organization_name,
        "description": "Portfolio Website Pass",
        "foregroundColor": "rgb(255,255,255)",
        "backgroundColor": "rgb(0,0,0)",
        "generic": {
            "primaryFields": [
                {
                    "key": "portfolio",
                    "label": "Portfolio",
                    "value": request.display_name,
                }
            ],
        },
        "barcodes": [
            {
                "format": "PKBarcodeFormatQR",
                "message": request.public_url,
                "messageEncoding": "utf-8",
            }
        ],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def manifest_json_file(files: Mapping[str, bytes]) -> str:
    """Return Apple's filename-to-SHA-1 manifest JSON.

    ``files`` excludes ``manifest.json`` and ``signature`` because those are
    generated after this manifest is calculated.
    """

    manifest = {
        filename: hashlib.sha1(content, usedforsecurity=False).hexdigest()
        for filename, content in sorted(files.items())
    }
    return json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))


def build_unsigned_pass_files(
    request: WalletPassRequest,
    settings: ApplePassSettings,
    *,
    assets: Mapping[str, bytes] | None = None,
) -> dict[str, bytes]:
    """Build source files before Apple signing and ZIP packaging."""

    files: dict[str, bytes] = {
        "pass.json": generate_pass_json(request, settings).encode("utf-8"),
    }
    if assets:
        files.update(assets)

    files["manifest.json"] = manifest_json_file(files).encode("utf-8")
    return files


class AppleWalletProvider(WalletPassProvider):
    platform = WalletPlatform.APPLE

    def __init__(self, settings: ApplePassSettings):
        self.settings = settings

    def issue(self, request: WalletPassRequest) -> WalletPassResult:
        # Build and hash source files now. PKCS#7 signing and ZIP packaging are
        # blocked until Apple certificate configuration exists.
        build_unsigned_pass_files(request, self.settings)
        raise WalletProviderNotConfigured(
            "Apple pass signing is not configured yet"
        )
