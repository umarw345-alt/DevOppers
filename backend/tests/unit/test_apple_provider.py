import hashlib
import json
from uuid import UUID

import pytest

from wallets.apple import (
    ApplePassSettings,
    AppleWalletProvider,
    build_unsigned_pass_files,
    generate_pass_json,
)
from wallets.providers import WalletPassRequest, WalletProviderNotConfigured


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
PORTFOLIO_ID = UUID("22222222-2222-2222-2222-222222222222")


def request() -> WalletPassRequest:
    return WalletPassRequest(
        user_id=USER_ID,
        portfolio_id=PORTFOLIO_ID,
        artifact_version="v1",
        public_url="https://portfolio.example.test/jane",
        display_name="Jane's Portfolio",
    )


def settings() -> ApplePassSettings:
    return ApplePassSettings(
        pass_type_identifier="pass.example.portfolio",
        team_identifier="TEAM123456",
        organization_name="Example Portfolio",
    )


def test_pass_json_has_required_fields_and_qr_url():
    raw = generate_pass_json(request(), settings())
    data = json.loads(raw)

    assert data["formatVersion"] == 1
    assert data["passTypeIdentifier"] == "pass.example.portfolio"
    assert data["serialNumber"] == str(PORTFOLIO_ID)
    assert data["teamIdentifier"] == "TEAM123456"
    assert data["organizationName"] == "Example Portfolio"
    assert data["barcodes"][0]["format"] == "PKBarcodeFormatQR"
    assert data["barcodes"][0]["message"] == request().public_url
    assert data["barcodes"][0]["messageEncoding"] == "utf-8"


def test_pass_json_is_valid_utf8():
    raw = generate_pass_json(request(), settings())

    encoded = raw.encode("utf-8")

    assert encoded.decode("utf-8") == raw
    assert json.loads(encoded.decode("utf-8"))["formatVersion"] == 1


def test_unsigned_source_files_include_manifest_with_correct_hash():
    files = build_unsigned_pass_files(
        request(),
        settings(),
        assets={"icon.png": b"fake-icon-bytes"},
    )

    manifest = json.loads(files["manifest.json"].decode("utf-8"))

    assert set(files) == {"pass.json", "manifest.json", "icon.png"}
    assert set(manifest) == {"pass.json", "icon.png"}
    assert manifest["pass.json"] == hashlib.sha1(
        files["pass.json"], usedforsecurity=False
    ).hexdigest()
    assert manifest["icon.png"] == hashlib.sha1(
        files["icon.png"], usedforsecurity=False
    ).hexdigest()


def test_pass_json_and_manifest_are_deterministic():
    first = build_unsigned_pass_files(request(), settings())
    second = build_unsigned_pass_files(request(), settings())

    assert first == second


def test_issue_requires_apple_signing_configuration():
    provider = AppleWalletProvider(settings())

    with pytest.raises(
        WalletProviderNotConfigured,
        match="Apple pass signing is not configured yet",
    ) as error:
        provider.issue(request())

    assert str(error.value) == "Apple pass signing is not configured yet"
