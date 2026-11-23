"""Build a signed Apple Wallet pass (.pkpass) whose QR code opens the portfolio.

A .pkpass is a zip of pass.json + images, a manifest.json of their SHA-1 hashes,
and a detached PKCS#7 signature of the manifest made with your Pass Type ID certificate.
"""

import hashlib
import io
import json
import os
import zipfile
from functools import lru_cache
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, pkcs7, pkcs12
from cryptography.x509.oid import NameOID

from portfolio.themes import contrast_ratio

ICON = (Path(__file__).parent / "pass_icon.png").read_bytes()


class PassError(Exception):
    """The server has no usable Apple Wallet certificate."""


@lru_cache
def signer():
    """Your Pass Type ID certificate + key (a .p12 exported from Keychain) and Apple's WWDR certificate."""
    try:
        password = os.getenv("PASS_P12_PASSWORD", "").encode() or None
        key, cert, _ = pkcs12.load_key_and_certificates(Path(os.environ["PASS_P12_PATH"]).read_bytes(), password)
        wwdr = Path(os.environ["WWDR_CERT_PATH"]).read_bytes()
        wwdr = x509.load_pem_x509_certificate(wwdr) if wwdr.startswith(b"-----") else x509.load_der_x509_certificate(wwdr)
    except (KeyError, OSError, ValueError) as error:
        raise PassError("Apple Wallet isn't set up on this server.") from error
    return key, cert, wwdr


def rgb(hex_color: str) -> str:
    return "rgb({}, {}, {})".format(*(int(hex_color[i : i + 2], 16) for i in (1, 3, 5)))


def build_pass(*, serial: str, name: str, headline: str | None, url: str, color: str) -> bytes:
    key, cert, wwdr = signer()
    # The certificate itself says which pass type and team it signs for.
    pass_type_id = cert.subject.get_attributes_for_oid(NameOID.USER_ID)[0].value
    team_id = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
    text = "#ffffff" if contrast_ratio(color, "#ffffff") >= 4.5 else "#000000"
    pass_json = {
        "formatVersion": 1,
        "passTypeIdentifier": pass_type_id,
        "teamIdentifier": team_id,
        "serialNumber": serial,
        "organizationName": "Portable Resume",
        "logoText": "Portable Resume",
        "description": f"{name}'s portfolio",
        "backgroundColor": rgb(color),
        "foregroundColor": rgb(text),
        "labelColor": rgb(text),
        "generic": {
            "primaryFields": [{"key": "name", "label": "NAME", "value": name}],
            "secondaryFields": [{"key": "headline", "label": "TITLE", "value": headline}] if headline else [],
        },
        "barcodes": [{"format": "PKBarcodeFormatQR", "message": url, "messageEncoding": "iso-8859-1", "altText": "Scan for my portfolio"}],
    }
    files = {"pass.json": json.dumps(pass_json).encode(), "icon.png": ICON}
    manifest = json.dumps({n: hashlib.sha1(b).hexdigest() for n, b in files.items()}).encode()
    signature = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(manifest)
        .add_signer(cert, key, hashes.SHA256())
        .add_certificate(wwdr)
        .sign(Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary])
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for filename, data in {**files, "manifest.json": manifest, "signature": signature}.items():
            archive.writestr(filename, data)
    return out.getvalue()
