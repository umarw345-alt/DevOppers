from uuid import uuid4

import pytest

from wallets.providers import (
    WalletPassProvider,
    WalletPassRequest,
    WalletPassResult,
    WalletPlatform,
)


class FakeGoogleWalletProvider:
    platform = WalletPlatform.GOOGLE

    def issue(self, request: WalletPassRequest) -> WalletPassResult:
        return WalletPassResult(
            platform=self.platform,
            provider_object_id=f"fake-google-{request.portfolio_id}",
            qr_value=request.public_url,
            add_to_wallet_url="https://example.test/add-to-google-wallet",
        )


class FakeAppleWalletProvider:
    platform = WalletPlatform.APPLE

    def issue(self, request: WalletPassRequest) -> WalletPassResult:
        return WalletPassResult(
            platform=self.platform,
            provider_object_id=f"fake-apple-{request.portfolio_id}",
            qr_value=request.public_url,
            content_type="application/vnd.apple.pkpass",
            filename="portfolio-card.pkpass",
            pass_bytes=b"fake-pkpass-bytes",
        )


def test_fake_google_provider_issues_wallet_result():
    request = WalletPassRequest(
        user_id=uuid4(),
        portfolio_id=uuid4(),
        artifact_version="v1",
        public_url="http://portfolio.example.test/jane",
        display_name="Jane's Portfolio",
    )

    provider: WalletPassProvider = FakeGoogleWalletProvider()
    result = provider.issue(request)

    assert result.platform is WalletPlatform.GOOGLE
    assert result.provider_object_id.startswith("fake-google-")
    assert result.qr_value == request.public_url
    assert result.add_to_wallet_url == "https://example.test/add-to-google-wallet"


def test_fake_apple_provider_issues_wallet_result():
    request = WalletPassRequest(
        user_id=uuid4(),
        portfolio_id=uuid4(),
        artifact_version="v1",
        public_url="http://portfolio.example.test/julian",
        display_name="Julian's Spot",
    )

    provider: WalletPassProvider = FakeAppleWalletProvider()
    result = provider.issue(request)

    assert result.platform is WalletPlatform.APPLE
    assert result.provider_object_id.startswith("fake-apple-")
    assert result.qr_value == request.public_url
    assert result.content_type == "application/vnd.apple.pkpass"
    assert result.filename == "portfolio-card.pkpass"
    assert result.pass_bytes == b"fake-pkpass-bytes"


def test_missing_public_url_is_rejected():
    with pytest.raises(ValueError, match="public_url cannot be empty"):
        WalletPassRequest(
            user_id=uuid4(),
            portfolio_id=uuid4(),
            artifact_version="v1",
            public_url="",
            display_name="Julian's Spot",
        )


def test_invalid_public_url_is_rejected():
    with pytest.raises(ValueError, match="absolute http:// or https:// URL"):
        WalletPassRequest(
            user_id=uuid4(),
            portfolio_id=uuid4(),
            artifact_version="v1",
            public_url="portfolio.example.test/julian",
            display_name="Julian's Spot",
        )
