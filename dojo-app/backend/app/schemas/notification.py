from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentCredentials(BaseModel):
    registration_number: str
    pin: str


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(StudentCredentials):
    endpoint: str
    keys: PushSubscriptionKeys


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    notification_type: str
    message: str
    created_at: datetime
    read_at: datetime | None


class VapidPublicKeyResponse(BaseModel):
    public_key: str
