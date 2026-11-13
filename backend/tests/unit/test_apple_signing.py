from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from auth_service.config import Settings
from wallets.apple_signing import load_apple_signing_material
from wallets.providers import WalletProviderNotConfigured


def _certificate(private_key, common_name: str) -> bytes:
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.DER)


def _settings(tmp_path, pass_path, private_key_path, wwdr_path) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://test",
        jwt_private_key_path=tmp_path / "jwt-private.pem",
        jwt_public_key_path=tmp_path / "jwt-public.pem",
        jwt_issuer="test",
        jwt_audience="test",
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=1,
        afk_timeout_minutes=30,
        login_rate_limit=5,
        login_rate_window_seconds=300,
        argon2_memory_cost=65536,
        argon2_time_cost=3,
        argon2_parallelism=4,
        argon2_hash_length=32,
        argon2_salt_length=16,
        apple_pass_certificate_path=pass_path,
        apple_pass_private_key_path=private_key_path,
        apple_wwdr_certificate_path=wwdr_path,
    )


def test_loads_matching_apple_signing_material(tmp_path):
    pass_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wwdr_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pass_path = tmp_path / "apple-pass.cer"
    private_key_path = tmp_path / "apple-pass.key"
    wwdr_path = tmp_path / "apple-wwdr.cer"
    pass_path.write_bytes(_certificate(pass_key, "Apple Pass"))
    private_key_path.write_bytes(
        pass_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    wwdr_path.write_bytes(_certificate(wwdr_key, "Apple WWDR"))

    material = load_apple_signing_material(
        _settings(tmp_path, pass_path, private_key_path, wwdr_path)
    )

    assert material.pass_certificate.subject.rdns
    assert material.private_key is not None
    assert material.wwdr_certificate.subject.rdns


def test_missing_paths_are_rejected(tmp_path):
    with pytest.raises(
        WalletProviderNotConfigured,
        match="paths are not configured",
    ):
        load_apple_signing_material(_settings(tmp_path, None, None, None))


def test_mismatched_certificate_and_private_key_are_rejected(tmp_path):
    pass_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    different_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wwdr_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pass_path = tmp_path / "apple-pass.cer"
    private_key_path = tmp_path / "apple-pass.key"
    wwdr_path = tmp_path / "apple-wwdr.cer"
    pass_path.write_bytes(_certificate(pass_key, "Apple Pass"))
    private_key_path.write_bytes(
        different_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    wwdr_path.write_bytes(_certificate(wwdr_key, "Apple WWDR"))

    with pytest.raises(
        WalletProviderNotConfigured,
        match="do not match",
    ):
        load_apple_signing_material(
            _settings(tmp_path, pass_path, private_key_path, wwdr_path)
        )
