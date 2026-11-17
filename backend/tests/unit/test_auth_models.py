from sqlalchemy import inspect

from auth_service.models import ExternalIdentity, User


def test_external_identity_has_expected_columns():
    columns = inspect(ExternalIdentity).columns

    assert set(columns.keys()) >= {
        "id",
        "user_id",
        "provider",
        "provider_subject",
        "email_at_link_time",
        "created_at",
        "updated_at",
    }
    assert columns["user_id"].nullable is False
    assert columns["provider"].nullable is False
    assert columns["provider_subject"].nullable is False
    assert columns["email_at_link_time"].nullable is True


def test_external_identity_references_users_with_cascade_delete():
    user_foreign_key = next(iter(ExternalIdentity.__table__.foreign_keys))
    assert user_foreign_key.target_fullname == "users.id"
    assert user_foreign_key.ondelete == "CASCADE"


def test_external_identity_enforces_provider_uniqueness():
    constraints = {
        constraint.name: tuple(constraint.columns.keys())
        for constraint in ExternalIdentity.__table__.constraints
        if constraint.name
    }

    assert constraints["uq_external_identities_provider_subject"] == (
        "provider",
        "provider_subject",
    )
    assert constraints["uq_external_identities_user_provider"] == (
        "user_id",
        "provider",
    )


def test_external_identity_restricts_current_provider_values():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in ExternalIdentity.__table__.constraints
        if constraint.name == "ck_external_identities_provider"
    }

    assert checks["ck_external_identities_provider"] == "provider IN ('google')"


def test_google_only_users_can_have_no_password_hash():
    assert inspect(User).columns["password_hash"].nullable is True
