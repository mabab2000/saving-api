from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "saving_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    fcm_token = Column(String, nullable=True)  # FCM token for push notifications
    oauth_provider = Column(String, nullable=True)  # e.g., 'google', 'facebook'
    oauth_id = Column(String, nullable=True)  # OAuth provider's user ID
    profile_picture = Column(String, nullable=True)  # Profile picture URL from OAuth

class Saving(Base):
    __tablename__ = "savings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("saving_users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Loan(Base):
    __tablename__ = "loans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("saving_users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    issued_date = Column(DateTime, nullable=False)
    deadline = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="active")  # active, paid, cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ProfilePhoto(Base):
    __tablename__ = "profile_photos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("saving_users.id"), nullable=False, unique=True, index=True)
    photo_url = Column(String, nullable=False)  # Supabase image URL
    content_type = Column(String, nullable=False, default="image/jpeg")  # MIME type
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Penalty(Base):
    __tablename__ = "penalties"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("saving_users.id"), nullable=False, index=True)
    reason = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="unpaid")  # paid, unpaid, cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class LoanPayment(Base):
    __tablename__ = "loan_payments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("saving_users.id"), nullable=False, index=True)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Distribution(Base):
    __tablename__ = "distributions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Removed ForeignKey to avoid DB creation error when referenced table lacks a UNIQUE/PK on `id`.
    # Will rely on application-level validation; add FK back after DB cleanup if desired.
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PayLoanUsingSaving(Base):
    __tablename__ = "pay_loan_using_savings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Avoiding DB-level ForeignKey to prevent create_all FK errors; validate user existence in app logic
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)