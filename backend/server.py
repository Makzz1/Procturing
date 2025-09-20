from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from supabase import create_client, Client
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

# Supabase connection
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_ANON_KEY')

if not supabase_url or not supabase_key:
    # For development, use placeholder values
    supabase_url = "https://placeholder.supabase.co"
    supabase_key = "placeholder_key"
    logging.warning("Supabase credentials not found. Using placeholder values.")

supabase: Client = create_client(supabase_url, supabase_key)

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

class AudioUpload(BaseModel):
    student_id: str
    exam_session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_size: int
    file_name: str

class FaceCapture(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_size: int
    file_name: str
    student_id: str
    exam_session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_final: bool = False
    file_size: int
    file_name: str

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# Initialize default admin if not exists
async def init_default_admin():
    try:
        # Check if admin exists
        result = supabase.table('admins').select('*').eq('username', 'admin').execute()
        
        if not result.data:
            default_admin = {
                'id': str(uuid.uuid4()),
                'username': 'admin',
                'password_hash': hash_password('admin123'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            supabase.table('admins').insert(default_admin).execute()
            logger.info("Default admin created: username=admin, password=admin123")
    except Exception as e:
        logger.error(f"Error initializing default admin: {e}")

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Secure Exam Platform API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.dict())
    status_data = status_obj.dict()
    status_data['timestamp'] = status_data['timestamp'].isoformat()
    
    try:
        supabase.table('status_checks').insert(status_data).execute()
        return status_obj
    except Exception as e:
        logger.error(f"Error creating status check: {e}")
        raise HTTPException(status_code=500, detail="Failed to create status check")

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    try:
        result = supabase.table('status_checks').select('*').execute()
        status_checks = []
        for item in result.data:
            item['timestamp'] = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
            status_checks.append(StatusCheck(**item))
        return status_checks
    except Exception as e:
        logger.error(f"Error getting status checks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status checks")

# Admin Authentication Routes
@api_router.post("/admin/login")
async def admin_login(credentials: AdminLogin):
    try:
        result = supabase.table('admins').select('*').eq('username', credentials.username).execute()
        
        if not result.data or not verify_password(credentials.password, result.data[0]['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        admin = result.data[0]
        
        # Simple token (in production, use JWT)
        token = str(uuid.uuid4())
        session_data = {
            'token': token,
            'admin_id': admin['id'],
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table('admin_sessions').insert(session_data).execute()
        
        return {"token": token, "message": "Login successful"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during admin login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# Question Management Routes
@api_router.post("/admin/questions", response_model=Question)
async def create_question(question: QuestionCreate):
    try:
        question_obj = Question(**question.dict())
        question_data = question_obj.dict()
        question_data['created_at'] = question_data['created_at'].isoformat()
        
        supabase.table('questions').insert(question_data).execute()
        return question_obj
    except Exception as e:
        logger.error(f"Error creating question: {e}")
        raise HTTPException(status_code=500, detail="Failed to create question")

@api_router.get("/admin/questions", response_model=List[Question])
async def get_all_questions():
    try:
        result = supabase.table('questions').select('*').execute()
        questions = []
        for item in result.data:
            item['created_at'] = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
            questions.append(Question(**item))
        return questions
    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get questions")

@api_router.get("/questions")
async def get_exam_questions():
    try:
        # Get random questions for exam (Supabase doesn't have $sample, so we'll get all and sample in Python)
        result = supabase.table('questions').select('*').execute()
        questions = result.data
        
        # Randomly sample 50 questions (or all if less than 50)
        import random
        sampled_questions = random.sample(questions, min(50, len(questions)))
        
        # Don't return correct answers to students
        for q in sampled_questions:
            q.pop('correct_answer', None)
        
        return sampled_questions
    except Exception as e:
        logger.error(f"Error getting exam questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get exam questions")

@api_router.delete("/admin/questions/{question_id}")
async def delete_question(question_id: str):
    try:
        result = supabase.table('questions').delete().eq('id', question_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        return {"message": "Question deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting question: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete question")

# Exam Logging Routes
@api_router.post("/exam/logs", response_model=ExamLog)
async def create_exam_log(log: ExamLogCreate):
    try:
        log_obj = ExamLog(**log.dict())
        log_data = log_obj.dict()
        log_data['timestamp'] = log_data['timestamp'].isoformat()
        
        supabase.table('exam_logs').insert(log_data).execute()
        return log_obj
    except Exception as e:
        logger.error(f"Error creating exam log: {e}")
        raise HTTPException(status_code=500, detail="Failed to create exam log")

@api_router.get("/admin/logs", response_model=List[ExamLog])
async def get_exam_logs():
    try:
        result = supabase.table('exam_logs').select('*').order('timestamp', desc=True).execute()
        logs = []
        for item in result.data:
            item['timestamp'] = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
            logs.append(ExamLog(**item))
        return logs
    except Exception as e:
        logger.error(f"Error getting exam logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get exam logs")

# Device Check Routes
@api_router.post("/device/check", response_model=DeviceCheckResult)
async def device_check(check_data: DeviceCheckResult):
    try:
        check_dict = check_data.dict()
        check_dict['check_timestamp'] = check_dict['check_timestamp'].isoformat()
        
        supabase.table('device_checks').insert(check_dict).execute()
        return check_data
    except Exception as e:
        logger.error(f"Error storing device check: {e}")
        raise HTTPException(status_code=500, detail="Failed to store device check")

@api_router.get("/admin/device-checks")
async def get_device_checks():
    try:
        result = supabase.table('device_checks').select('*').order('check_timestamp', desc=True).limit(100).execute()
        
        # Convert timestamp strings back to datetime objects for consistency
        for check in result.data:
            check['check_timestamp'] = datetime.fromisoformat(check['check_timestamp'].replace('Z', '+00:00'))
        
        return result.data
    except Exception as e:
        logger.error(f"Error getting device checks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device checks")

# Face capture endpoint (commented out - ready for implementation)
"""
@api_router.post("/exam/upload-face")
async def upload_face_image(
    face_image: UploadFile = File(...),
    student_id: str = Form(...),
    timestamp: str = Form(...)
):
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/faces")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_name = f"face_{student_id}_{int(datetime.now().timestamp())}.jpg"
        file_path = upload_dir / file_name
        
        # Save face image
        with open(file_path, "wb") as buffer:
            content = await face_image.read()
            buffer.write(content)
        
        # Log face capture
        face_log = {
            'id': str(uuid.uuid4()),
            'student_id': student_id,
            'timestamp': datetime.fromisoformat(timestamp.replace('Z', '+00:00')).isoformat(),
            'file_size': len(content),
            'file_name': file_name
        }
        
        supabase.table('face_captures').insert(face_log).execute()
        
        return {
            "message": "Face image uploaded successfully",
            "file_name": file_name,
            "file_size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Failed to upload face image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload face image")
"""

# Audio upload endpoint (commented out - ready for implementation)
"""
@api_router.post("/exam/upload-audio")
async def upload_audio_chunk(
    audio: UploadFile = File(...),
    student_id: str = Form(...),
    exam_session_id: str = Form(...),
    timestamp: str = Form(...)
):
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/audio")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_name = f"{student_id}_{exam_session_id}_{int(datetime.now().timestamp())}.webm"
        file_path = upload_dir / file_name
        
        # Save audio file
        with open(file_path, "wb") as buffer:
            content = await audio.read()
            buffer.write(content)
        
        # Log audio upload
        audio_log = {
            'student_id': student_id,
            'exam_session_id': exam_session_id,
            'timestamp': datetime.fromisoformat(timestamp.replace('Z', '+00:00')).isoformat(),
            'file_size': len(content),
            'file_name': file_name
        }
        
        supabase.table('audio_uploads').insert(audio_log).execute()
        
        return {
            "message": "Audio chunk uploaded successfully",
            "file_name": file_name,
            "file_size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Failed to upload audio: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload audio")
"""
"""
@api_router.post("/exam/upload-video")
async def upload_video_chunk(
    video: UploadFile = File(...),
    student_id: str = Form(...),
    exam_session_id: str = Form(...),
    timestamp: str = Form(...),
    is_final: str = Form(...)
):
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/videos")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_name = f"{student_id}_{exam_session_id}_{int(datetime.now().timestamp())}.webm"
        file_path = upload_dir / file_name
        
        # Save video file
        with open(file_path, "wb") as buffer:
            content = await video.read()
            buffer.write(content)
        
        # Log video upload
        video_log = VideoUpload(
            student_id=student_id,
            exam_session_id=exam_session_id,
            timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
            is_final=is_final.lower() == 'true',
            file_size=len(content),
            file_name=file_name
        )
        
        video_data = video_log.dict()
        video_data['timestamp'] = video_data['timestamp'].isoformat()
        supabase.table('video_uploads').insert(video_data).execute()
        
        return {
            "message": "Video chunk uploaded successfully",
            "file_name": file_name,
            "file_size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Failed to upload video: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload video")
"""

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

# Note: No shutdown event needed for Supabase as it handles connections automatically