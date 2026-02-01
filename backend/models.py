from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Embedded Data Model: Profile lives inside User 
class UserProfile(BaseModel):
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    goals: Optional[str] = "Stay fit"

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    profile: UserProfile
    
    

from datetime import datetime
from typing import List

class Exercise(BaseModel):
    name: str
    sets: int
    reps: int
    weight: float  # in kg

class WorkoutCreate(BaseModel):
    title: str
    date: Optional[datetime] = Field(default_factory=datetime.utcnow)

class WorkoutResponse(WorkoutCreate):
    id: str
    user_id: str
    exercises: List[Exercise] = []
    total_duration: int = 0 # minutes