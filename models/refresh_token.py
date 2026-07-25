"""
Refresh Token model for server-side session management.

Stores a SHA-256 hash of the raw refresh token so the raw value
is never persisted.  Revoked on explicit logout; expired tokens
are pruned by the /auth/refresh endpoint.
"""

import hashlib
import uuid
from datetime import datetime

from models import db


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(
        db.String(50),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id = db.Column(
        db.String(50),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationship — handy for cascade deletes
    user = db.relationship("User", backref="refresh_tokens")

    # ------------------------------------------------------------------
    # Class-level helpers
    # ------------------------------------------------------------------

    @classmethod
    def hash_token(cls, raw_token: str) -> str:
        """Return the SHA-256 hex digest of a raw refresh token."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def find_valid(cls, raw_token: str) -> "RefreshToken | None":
        """
        Look up a refresh token by its raw value.
        Returns the row only when it is not revoked and has not expired.
        Returns None otherwise (caller should treat it as invalid).
        """
        token_hash = cls.hash_token(raw_token)
        return cls.query.filter_by(
            token_hash=token_hash,
            revoked=False,
        ).filter(cls.expires_at > datetime.utcnow()).first()

    def revoke(self) -> None:
        """Mark this token as revoked (used on logout or re-issue)."""
        self.revoked = True

    def is_expired(self) -> bool:
        """True when the token has passed its expiry date."""
        return datetime.utcnow() > self.expires_at

    def __repr__(self) -> str:
        return (
            f"<RefreshToken user_id={self.user_id} "
            f"revoked={self.revoked} expires_at={self.expires_at}>"
        )
