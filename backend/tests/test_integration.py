import json
import os
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4
from dotenv import load_dotenv


import psycopg
import jwt

import pytest


if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    pytest.skip(
        "Set RUN_INTEGRATION_TESTS=1 to run Docker integration tests.",
        allow_module_level=True,
    )


BASE_URL = os.getenv("AUTH_INTEGRATION_BASE_URL", "http://localhost:8080")


def make_opener():
    jar = CookieJar()
    return build_opener(HTTPCookieProcessor(jar)), jar


def send(opener, path, *, payload=None, headers=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Accept": "application/json", **(headers or {})},
        method="POST" if path != "/health" else "GET",
    )
    try:
        response = opener.open(request, timeout=10)
        raw_body = response.read()
        return response.status, json.loads(raw_body) if raw_body else None
    except HTTPError as error:
        raw_body = error.read()
        return error.code, json.loads(raw_body) if raw_body else None
    except URLError as error:
        pytest.fail(f"Integration gateway is unreachable at {BASE_URL}: {error}")


def web_headers(csrf_token=None):
    headers = {
        "Content-Type": "application/json",
        "X-Client-Platform": "web",
    }
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
    return headers


def age_session(session_id):
    load_dotenv()
    database_url = os.getenv("AUTH_INTEGRATION_DATABASE_URL")
    if not database_url:
        pytest.fail("AUTH_INTEGRATION_DATABASE_URL is required for AFK integration tests")
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            UPDATE sessions
            SET last_activity_at = NOW() - INTERVAL '31 minutes'
            WHERE id = %s
            """,
            (session_id,),
        )

def cookie_value(jar, name):
    return next((cookie.value for cookie in jar if cookie.name == name), None)


def credentials():
    return {
        "email": f"integration-{uuid4().hex}@example.com",
        "password": "Password123!",
    }

def false_email():
    return {
        "email": f"false-{uuid4().hex}@false.org",
        "password": "PasswordFalse123!",
    }

def false_pass(account):
    return {
        "email": account["email"],
        "password": "fakepassword123!",
    }

def native_headers():
    headers = {
        "Content-Type": "application/json",
        "X-Client-Platform": "native",
    }
    return headers

def test_gateway_health():
    opener, _ = make_opener()

    status, body = send(opener, "/health")

    assert status == 200
    assert body == {"status": "ok"}


def test_web_register_refresh_and_logout_uses_cookies_and_csrf():
    opener, jar = make_opener()
    account = credentials()

    register_status, register_body = send(
        opener,
        "/v1/auth/register",
        payload=account,
        headers=web_headers(),
    )
    assert register_status == 201
    assert register_body["user"]["email"] == account["email"]
    assert cookie_value(jar, "auth_access_token")
    assert cookie_value(jar, "auth_refresh_token")
    csrf_token = cookie_value(jar, "auth_csrf_token")
    assert csrf_token

    refresh_status, refresh_body = send(
        opener,
        "/v1/auth/refresh",
        headers=web_headers(csrf_token),
    )
    assert refresh_status == 200
    assert refresh_body["user"]["email"] == account["email"]
    rotated_csrf_token = cookie_value(jar, "auth_csrf_token")
    assert rotated_csrf_token and rotated_csrf_token != csrf_token

    logout_status, logout_body = send(
        opener,
        "/v1/auth/logout",
        headers=web_headers(rotated_csrf_token),
    )
    assert logout_status == 200
    assert logout_body == {"status": "ok"}

    fresh_opener, _ = make_opener()
    after_logout_status, _ = send(
        fresh_opener,
        "/v1/auth/refresh",
        headers=web_headers(),
    )
    assert after_logout_status == 401


def test_duplicate_registration_is_rejected():
    opener, _ = make_opener()
    account = credentials()

    first_status, _ = send(
        opener,
        "/v1/auth/register",
        payload=account,
        headers={"Content-Type": "application/json", "X-Client-Platform": "native"},
    )
    duplicate_status, duplicate_body = send(
        opener,
        "/v1/auth/register",
        payload=account,
        headers={"Content-Type": "application/json", "X-Client-Platform": "native"},
    )

    assert first_status == 201
    assert duplicate_status == 409
    assert duplicate_body["detail"]


def test_native_register_refresh_and_logout_uses_json_and_bearer_tokens():
    opener, _ = make_opener()
    account = credentials()

    register_status, register_body = send(
        opener,
        "/v1/auth/register",
        payload=account,
        headers=native_headers(),
    )
    assert register_status == 201
    assert register_body["access_token"]
    assert register_body["refresh_token"]

    refresh_status, refresh_body = send(
        opener,
        "/v1/auth/refresh",
        payload={"refresh_token": register_body["refresh_token"]},
        headers=native_headers(),
    )
    assert refresh_status == 200
    assert refresh_body["access_token"]
    assert refresh_body["refresh_token"]
    assert refresh_body["refresh_token"] != register_body["refresh_token"]

    logout_status, logout_body = send(
        opener,
        "/v1/auth/logout",
        headers={
            **native_headers(),
            "Authorization": f"Bearer {refresh_body['access_token']}",
        },
    )
    assert logout_status == 200
    assert logout_body == {"status": "ok"}

# def test_logout_or_afk_revokes_token_family():
#     opener, jar = make_opener()
#     account = credentials()

#     register_status, register_body = send(
#         opener,
#         "/v1/auth/register",
#         payload=account,
#         headers=web_headers(),
#     )
#     assert register_status == 201
#     assert register_body["access_token"]
#     assert register_body["refresh_token"]


#     assert cookie_value(jar, "auth_access_token")
#     assert cookie_value(jar, "auth_refresh_token")
#     csrf_token = cookie_value(jar, "auth_csrf_token")

#     logout_status, logout_body = send(
#         opener,
#         "v1/auth/logout",
#         headers={csrf_token}
#     )

#     assert logout_status == 200
#     assert logout_body == {"status": "ok"}


def test_incorrect_credentials_fail_login():
    opener, jar = make_opener()
    account = credentials()
    falseAccount = false_email()
    falsePass = false_pass(account)

    register_status, register_body = send(
        opener,
        "/v1/auth/register",
        payload=account,
        headers=web_headers(),
    )

    assert register_status == 201
    assert register_body["user"]["email"] == account["email"]
    assert cookie_value(jar, "auth_access_token")
    assert cookie_value(jar, "auth_refresh_token")
    csrf_token = cookie_value(jar, "auth_csrf_token")
    assert csrf_token


    login_status, login_body = send(
        opener,
        "/v1/auth/login",
        payload=falseAccount,
        headers=web_headers(),
    )

    assert login_status == 401
    assert login_body["detail"]

    login_status, login_body = send(
        opener,
        "/v1/auth/login",
        payload=falsePass,
        headers=web_headers(),
    )

    assert login_status == 401
    assert login_body["detail"]

    logout_status, logout_body = send(
        opener,
        "/v1/auth/logout",
        headers=web_headers(csrf_token)
    )

    assert logout_status == 200
    assert logout_body == {"status": "ok"}
    
def test_afk_timeout():
    opener, jar = make_opener()
    account = credentials()
    
    register_status, register_body = send(
        opener,
        "/v1/auth/register",
        payload=account,
        headers=web_headers()
    )
    assert register_status == 201
    assert register_body["user"]["email"] == account["email"]
    assert cookie_value(jar, "auth_access_token")
    assert cookie_value(jar, "auth_refresh_token")
    csrf_token = cookie_value(jar, "auth_csrf_token")
    assert csrf_token
    
    access_token = cookie_value(jar, "auth_access_token")
    assert access_token
    
    claims = jwt.decode(
        access_token,
        options={"verify_signature": False},
    )
    
    session_id = claims["sid"]
    
    age_session(session_id)
    
    refresh_status, refresh_body = send(
        opener,
        "/v1/auth/refresh",
        headers=web_headers(csrf_token)
    )
    
    assert refresh_status == 401
    assert refresh_body["detail"] == "Session expired"
    
    logout_status, logout_body = send(
        opener,
        "/v1/auth/logout",
        headers=web_headers(csrf_token)
    )
    
    assert logout_status == 401
    assert logout_body["detail"] == "Unauthorized"
    
    