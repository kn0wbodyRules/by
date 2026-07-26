from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_str


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        # One account per provider identity. The subject is the provider's own
        # immutable user id — never the email, which users can change.
        UniqueConstraint("oauth_provider", "oauth_subject", name="uq_users_oauth_identity"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    # Nullable because OAuth accounts have no password to hash. A user with
    # hashed_password IS NULL can only sign in through their provider.
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    oauth_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    oauth_subject: Mapped[str | None] = mapped_column(String, nullable=True)

    otp_code_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    jobs: Mapped[list["Job"]] = relationship(back_populates="user", cascade="all, delete-orphan")
