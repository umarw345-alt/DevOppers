import hashlib
import io
import json
import zipfile
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, pkcs7, pkcs12
from cryptography.x509.oid import NameOID

from portfolio import wallet


def test_pass_is_signed_and_its_qr_code_opens_the_portfolio(tmp_path, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.USER_ID, "pass.edu.sjsu.test"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "TEAM123456"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Pass Type ID: pass.edu.sjsu.test"),
    ])
    cert = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(1).not_valid_before(datetime(2020, 1, 1)).not_valid_after(datetime(2040, 1, 1))
        .sign(key, hashes.SHA256())
    )
    (tmp_path / "pass.p12").write_bytes(pkcs12.serialize_key_and_certificates(b"test", key, cert, None, NoEncryption()))
    (tmp_path / "wwdr.cer").write_bytes(cert.public_bytes(Encoding.DER))
    monkeypatch.setenv("PASS_P12_PATH", str(tmp_path / "pass.p12"))
    monkeypatch.setenv("WWDR_CERT_PATH", str(tmp_path / "wwdr.cer"))
    wallet.signer.cache_clear()

    data = wallet.build_pass(serial="ada", name="Ada", headline=None, url="https://abcd.com/ada", color="#1e3a8a")
    wallet.signer.cache_clear()

    archive = zipfile.ZipFile(io.BytesIO(data))
    pass_json = json.loads(archive.read("pass.json"))
    assert pass_json["barcodes"][0]["message"] == "https://abcd.com/ada"
    assert (pass_json["passTypeIdentifier"], pass_json["teamIdentifier"]) == ("pass.edu.sjsu.test", "TEAM123456")
    assert pass_json["foregroundColor"] == "rgb(255, 255, 255)"
    signed_files = [n for n in archive.namelist() if n not in ("manifest.json", "signature")]
    assert json.loads(archive.read("manifest.json")) == {n: hashlib.sha1(archive.read(n)).hexdigest() for n in signed_files}
    assert len(pkcs7.load_der_pkcs7_certificates(archive.read("signature"))) == 2
