from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date

class UserAdminResponse(BaseModel):
    id: int
    email: str
    name: str
    lastname: str
    birthday: date
    is_active: bool
    is_deleted: bool

class PaginatedUsersResponse(BaseModel):
    data: List[UserAdminResponse]
    total: int
    page: int
    size: int

class ApproveUserRequest(BaseModel):
    user_id_to_approve: int
    admin_id: int

class BulkApproveUserRequest(BaseModel):
    user_ids_to_approve: List[int]
    admin_id: int

class ToggleUserRequest(BaseModel):
    user_id_to_toggle: int
    admin_id: int

class UserDetailsResponse(BaseModel):
    user: UserAdminResponse
    role: str
    details: dict
