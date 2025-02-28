from pydantic import BaseModel, EmailStr, Field


class RefreshTokenRequest(BaseModel):
    client_id: str
    client_secret: str

    class Config:
        title = "Refresh the access token. If the token got expired"
        description = "Schema for the request to refresh the access token for a user."

        schema_extra = {
            "example": {"client_id": "your client id", "client_secret": "your secret"}
        }


class ProjectEngagementUserAuthTestSchema(BaseModel):
    project_name: str
    engagement_name: str
    email: str


class RegisterUserForProjectRequest(BaseModel):
    engagement_name: str
    project_name: str
    user_email: str
    role_name: str = "admin"

    class Config:
        schema_extra = {
            "example": {
                "engagement_name": "Development Sprint",
                "project_name": "AI Research",
                "user_email": "example@domain.com",
                "role_name": "admin",
            }
        }
        title = "Register a User for a Project"
        description = "Schema for the request to register a user to a project with a specific role for an engagement."


class ServiceAccountCreate(BaseModel):
    name: str = Field(..., description="A descriptive name for the service account")
    email: EmailStr = Field(..., description="A contact email for the service account")


class ServiceAccountResponse(BaseModel):
    client_id: str
    name: str
    email: EmailStr

    class Config:
        orm_mode = True
