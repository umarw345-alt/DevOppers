"""Build an "Add to Google Wallet" link whose card's QR code opens the portfolio.

Google Wallet takes a JWT signed with a Google Cloud service account's key. The JWT
holds the card itself (a Generic pass), so the server never has to call Google:
the user opens https://pay.google.com/gp/v/save/<jwt> and Google saves the card.

Setup (see README, "Google Wallet setup"): an issuer ID from the Google Pay & Wallet
Console, and the JSON key of a service account that has access to that issuer.
"""

import json
import os
import time
from functools import lru_cache
from pathlib import Path

import jwt

SAVE_URL = "https://pay.google.com/gp/v/save/"
# Every card is an object of this one class (Google's word for a card template).
CLASS_SUFFIX = "portable_resume"


class GoogleWalletError(Exception):
    """The server has no usable Google Wallet configuration."""


@lru_cache
def credentials() -> tuple[str, str, str]:
    """(issuer ID, service account email, private key PEM)."""
    try:
        issuer_id = os.environ["GOOGLE_WALLET_ISSUER_ID"].strip()
        key = json.loads(Path(os.environ["GOOGLE_WALLET_KEY_PATH"]).read_text(encoding="utf-8"))
        email, private_key = key["client_email"], key["private_key"]
    except (KeyError, OSError, ValueError) as error:
        raise GoogleWalletError("Google Wallet isn't set up on this server.") from error
    if not issuer_id:
        raise GoogleWalletError("Google Wallet isn't set up on this server.")
    return issuer_id, email, private_key


def _text(value: str) -> dict:
    return {"defaultValue": {"language": "en-US", "value": value}}


def build_save_url(*, slug: str, name: str, headline: str | None, url: str, color: str, logo_url: str | None) -> str:
    """The link that adds this portfolio's card to Google Wallet.

    logo_url must be a public https:// image, because Google downloads it; pass None
    (e.g. on localhost) to leave the logo off.
    """
    issuer_id, email, private_key = credentials()
    class_id = f"{issuer_id}.{CLASS_SUFFIX}"
    card = {
        "id": f"{issuer_id}.{slug}",
        "classId": class_id,
        "state": "ACTIVE",
        "cardTitle": _text("Portable Resume"),
        "header": _text(name),
        "hexBackgroundColor": color,
        "barcode": {"type": "QR_CODE", "value": url, "alternateText": "Scan for my portfolio"},
        "linksModuleData": {"uris": [{"id": "portfolio", "uri": url, "description": "Portfolio"}]},
    }
    if headline:
        card["subheader"] = _text(headline)
    if logo_url:
        card["logo"] = {"sourceUri": {"uri": logo_url}, "contentDescription": _text("Portable Resume")}

    claims = {
        "iss": email,
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        # Google creates the class the first time a card of it is saved.
        "payload": {"genericClasses": [{"id": class_id}], "genericObjects": [card]},
    }
    return SAVE_URL + jwt.encode(claims, private_key, algorithm="RS256")
