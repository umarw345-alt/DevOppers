from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from auth_service.db import Base


class WalletPass(Base):
    """A record of a wallet pass issued for a published portfolio artifact.

    Provider-specific signing material is deliberately not represented here.
    Apple certificates and Google service-account keys belong in deployment
    secret storage, while the client receives only the resulting pass or link.
    """

    __tablename__ = "wallet_passes"
    __table_args__ = (
        CheckConstraint("platform IN ('apple', 'google')", name="ck_wallet_passes_platform"),
        CheckConstraint(
            "status IN ('issued', 'revoked', 'failed')",
            name="ck_wallet_passes_status",
        ),
        UniqueConstraint(
            "platform",
            "provider_object_id",
            name="uq_wallet_passes_platform_provider_object",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # The portfolio table will be introduced by the publishing component. It
    # is intentionally not an FK yet so this feature can land independently.
    portfolio_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_object_id: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_version: Mapped[str] = mapped_column(String(128), nullable=False)
    public_url: Mapped[str] = mapped_column(Text, nullable=False)
    qr_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="issued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
