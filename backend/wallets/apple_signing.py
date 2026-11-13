"""Load and validate Apple Wallet signing material.

This module deliberately stops before signing. It only prepares validated
certificate and private-key objects for the PKCS#7 stage.
"""

from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from auth_service.config import Settings
from wallets.providers import WalletProviderNotConfigured


@dataclass(frozen=True)
class AppleSigningMaterial:
    """Validated Apple certificate chain and matching private key."""

    pass_certificate: x509.Certificate
    private_key: object
    wwdr_certificate: x509.Certificate


def _load_certificate(path: Path) -> x509.Certificate:
    data = path.read_bytes()
    try:
        return x509.load_der_x509_certificate(data)
    except ValueError:
        return x509.load_pem_x509_certificate(data)


def _load_private_key(path: Path) -> object:
    data = path.read_bytes()
    try:
        return serialization.load_pem_private_key(data, password=None)
    except ValueError:
        return serialization.load_der_private_key(data, password=None)


def _public_key_bytes(key: object) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_apple_signing_material(settings: Settings) -> AppleSigningMaterial:
    """Load configured Apple signing files without exposing their contents."""

    paths = (
        settings.apple_pass_certificate_path,
        settings.apple_pass_private_key_path,
        settings.apple_wwdr_certificate_path,
    )
    if any(path is None for path in paths):
        raise WalletProviderNotConfigured(
            "Apple Wallet signing paths are not configured"
        )

    pass_path, private_key_path, wwdr_path = paths
    assert pass_path is not None
    assert private_key_path is not None
    assert wwdr_path is not None

    if not all(path.is_file() for path in paths):
        raise WalletProviderNotConfigured(
            "One or more Apple Wallet signing files are unavailable"
        )

    try:
        pass_certificate = _load_certificate(pass_path)
        private_key = _load_private_key(private_key_path)
        wwdr_certificate = _load_certificate(wwdr_path)
    except (OSError, ValueError, TypeError) as error:
        raise WalletProviderNotConfigured(
            "Apple Wallet signing files could not be parsed"
        ) from error

    if _public_key_bytes(pass_certificate) != _public_key_bytes(private_key):
        raise WalletProviderNotConfigured(
            "Apple pass certificate and private key do not match"
        )

    return AppleSigningMaterial(
        pass_certificate=pass_certificate,
        private_key=private_key,
        wwdr_certificate=wwdr_certificate,
    )
