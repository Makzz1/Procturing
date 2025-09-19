from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import hashlib


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str  # A, B, C, or D
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class QuestionCreate(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str

class Admin(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AdminLogin(BaseModel):
    username: str
    password: str

class ExamLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    log_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    video_url: Optional[str] = None
    reason: str
    student_id: Optional[str] = None
    exam_session_id: Optional[str] = None

class ExamLogCreate(BaseModel):
    log_id: str
    video_url: Optional[str] = None
    reason: str
    student_id: Optional[str] = None
    exam_session_id: Optional[str] = None

class DeviceCheckResult(BaseModel):
    has_multiple_keyboards: bool
    has_external_monitors: bool
    keyboard_count: int
    monitor_count: int
    detected_devices: List[str]
    check_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# Initialize default admin if not exists
async def init_default_admin():
    admin_exists = await db.admins.find_one({"username": "admin"})
    if not admin_exists:
        default_admin = Admin(
            username="admin",
            password_hash=hash_password("admin123")
        )
        await db.admins.insert_one(default_admin.dict())
        logger.info("Default admin created: username=admin, password=admin123")

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Secure Exam Platform API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Admin Authentication Routes
@api_router.post("/admin/login")
async def admin_login(credentials: AdminLogin):
    admin = await db.admins.find_one({"username": credentials.username})
    if not admin or not verify_password(credentials.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Simple token (in production, use JWT)
    token = str(uuid.uuid4())
    await db.admin_sessions.insert_one({
        "token": token,
        "admin_id": admin["id"],
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"token": token, "message": "Login successful"}

# Question Management Routes
@api_router.post("/admin/questions", response_model=Question)
async def create_question(question: QuestionCreate):
    question_obj = Question(**question.dict())
    await db.questions.insert_one(question_obj.dict())
    return question_obj

@api_router.get("/admin/questions", response_model=List[Question])
async def get_all_questions():
    questions = await db.questions.find().to_list(1000)
    return [Question(**question) for question in questions]

@api_router.get("/questions", response_model=List[Question])
async def get_exam_questions():
    # Get 50 random questions for exam
    pipeline = [{"$sample": {"size": 50}}]
    questions = await db.questions.aggregate(pipeline).to_list(50)
    # Don't return correct answers to students
    for q in questions:
        q.pop('correct_answer', None)
    return [Question(**question) for question in questions]

@api_router.delete("/admin/questions/{question_id}")
async def delete_question(question_id: str):
    result = await db.questions.delete_one({"id": question_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question deleted successfully"}

# Exam Logging Routes
@api_router.post("/exam/logs", response_model=ExamLog)
async def create_exam_log(log: ExamLogCreate):
    log_obj = ExamLog(**log.dict())
    await db.exam_logs.insert_one(log_obj.dict())
    return log_obj

@api_router.get("/admin/logs", response_model=List[ExamLog])
async def get_exam_logs():
    logs = await db.exam_logs.find().sort("timestamp", -1).to_list(1000)
    return [ExamLog(**log) for log in logs]

# Device Check Routes
@api_router.post("/device/check", response_model=DeviceCheckResult)
async def device_check(check_data: DeviceCheckResult):
    # Store device check result
    await db.device_checks.insert_one(check_data.dict())
    return check_data

@api_router.get("/admin/device-checks")
async def get_device_checks():
    checks = await db.device_checks.find().sort("check_timestamp", -1).to_list(100)
    return checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await init_default_admin()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()