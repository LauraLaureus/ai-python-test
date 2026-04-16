from pydantic import BaseModel
from enum import Enum
from sqlmodel import SQLModel, Field
from uuid import uuid4

# region Enums
class RequestType(str, Enum):
    email = "email"
    sms = "sms"
    push = "push"

class RequestStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    sent = "sent"
    failed = "failed"

class ProviderPriority(str,Enum):
    low = "low"
    normal = "normal"
    high = "high"
# endregion


# region SQLModel

class NotificationBase(SQLModel):
    to: str
    message: str
    type: RequestType

class UserNotificationRequestBase(NotificationBase):
    user_input : str

# endregion

# region Table definition

class UserNotificationRequest(UserNotificationRequestBase, table=True):
    id : str =  Field(default_factory=lambda: str(uuid4()), primary_key=True)
    status : RequestStatus = "queued"
    # to : str #inherited from NotificationBase
    # message : str # inherited from NotificationBase
    # type : RequestType # inherited from NotificationBase
    # user_input : str # inherited from UserNotificationRequestBase

# endregion

# region DTOs

class CreateRequest(SQLModel):
    id: str

class RequestStatusResponse(SQLModel):
    id: str
    status: RequestStatus

# endregion