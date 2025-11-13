from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re

# User Schemas
class UserLoginById(BaseModel):
    user_id: str  # UUID as string

class UserLogin(BaseModel):
    email: str
    password: str

class UserSignup(BaseModel):
    username: str
    email: str
    phone_number: str = Field(..., description="Phone number with country code 250 followed by 9 digits")
    password: str = None  # Optional, will use default if not provided
    confirm_password: str = None  # Optional, will use default if not provided
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        # Remove any spaces or dashes
        phone = v.replace(" ", "").replace("-", "")
        
        # Check if it matches the pattern: 250 followed by 9 digits
        if not re.match(r'^250\d{9}$', phone):
            raise ValueError('Phone number must be country code 250 followed by 9 digits (e.g., 250123456789)')
        return phone

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenWithUserInfo(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

# Saving Schemas
class SavingCreate(BaseModel):
    user_id: str  # UUID as string
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")

class SavingResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    username: str | None = None
    phone_number: str | None = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class SavingSummary(BaseModel):
    total_amount: float
    total_saving: int
    savings: list[SavingResponse]

# Saving update schema
class SavingUpdate(BaseModel):
    amount: float | None = None

# Loan Schemas
class LoanCreate(BaseModel):
    user_id: str  # UUID as string
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    issued_date: datetime
    deadline: datetime

class LoanResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    issued_date: datetime
    deadline: datetime
    created_at: datetime
    updated_at: datetime
    username: str | None = None
    phone_number: str | None = None
    
    class Config:
        from_attributes = True

class LoanSummary(BaseModel):
    total_amount: float
    total_loan: int
    loans: list[LoanResponse]

# Loan Payment Schemas
class LoanPaymentCreate(BaseModel):
    user_id: str  # UUID as string
    loan_id: str  # UUID as string
    amount: float = Field(..., gt=0, description="Payment amount must be greater than 0")

class LoanPaymentResponse(BaseModel):
    id: str
    user_id: str
    loan_id: str
    amount: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LoanPaymentSummary(BaseModel):
    total_amount: float
    total_payments: int
    payments: list[LoanPaymentResponse]

# Profile Photo Schemas
class ProfilePhotoResponse(BaseModel):
    id: str
    user_id: str
    photo: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProfilePhotoURLResponse(BaseModel):
    image_preview_link: str | None = None

    class Config:
        from_attributes = True

# Penalty Schemas
class PenaltyCreate(BaseModel):
    user_id: str  # UUID as string
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for the penalty")
    amount: float = Field(..., gt=0, description="Penalty amount must be greater than 0")
    status: str = Field(default="unpaid", pattern="^(paid|unpaid|cancelled)$", description="Status must be: paid, unpaid, or cancelled")

class PenaltyResponse(BaseModel):
    id: str
    user_id: str
    reason: str
    amount: float
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PenaltySummary(BaseModel):
    total_paid: float
    total_unpaid: float
    penalties: list[PenaltyResponse]

# Home Dashboard Schemas
class LatestSavingInfo(BaseModel):
    month: int
    year: int
    amount: float

class HomeResponse(BaseModel):
    user_id: str
    image_preview_link: str | None
    total_saving: float
    total_loan: float  # Current loan balance (total loans - total payments)
    latest_saving_info: LatestSavingInfo | None

class DashboardResponse(BaseModel):
    user_id: str
    total_saving: float
    total_loan: float  # Current loan balance (total loans - total payments)
    total_penalties: float

# User response/update schemas
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    phone_number: str
    total_saving: float = 0.0

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    phone_number: str | None = None
    password: str | None = None

# Loan update schema
class LoanUpdate(BaseModel):
    amount: float | None = None
    issued_date: datetime | None = None
    deadline: datetime | None = None

# Penalty update schema
class PenaltyUpdate(BaseModel):
    reason: str | None = None
    amount: float | None = None
    status: str | None = None


# Member listing schema (for admin or public members list)
class MemberResponse(BaseModel):
    id: str
    username: str
    email: str
    phone_number: str | None = None
    image_preview_link: str | None = None
    shares: int = 0

    class Config:
        from_attributes = True