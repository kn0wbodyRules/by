from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    email_sent: bool = True
    message: str = "Registration successful. Check your email for a verification code."


class ResendOTPRequest(BaseModel):
    email: EmailStr


class ResendOTPResponse(BaseModel):
    email_sent: bool
    # Wording is identical whether or not the address exists, so this endpoint
    # cannot be used to discover which emails are registered.
    message: str = "If that account exists and is unverified, a new code has been sent."


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    is_verified: bool
