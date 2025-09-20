from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import asyncpg
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import hashlib
import json
from speech_detection import initialize_speech_detection, detect_speech_from_bytes


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PostgreSQL connection pool
pg_pool = None

async def init_db():
    global pg_pool
    pg_pool = await asyncpg.create_pool(
        host=os.environ.get('DB_HOST'),
        port=int(os.environ.get('DB_PORT')),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        min_size=1,
        max_size=10
    )
    
    # Create tables if they don't exist
    async with pg_pool.acquire() as connection:
        # Create questions table
        await connection.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_answer VARCHAR(1) NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D')),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')
        
        # Create exam_logs table
        await connection.execute('''
            CREATE TABLE IF NOT EXISTS exam_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                log_id VARCHAR(255) UNIQUE NOT NULL,
                reason TEXT NOT NULL,
                student_id VARCHAR(255) NOT NULL,
                exam_session_id VARCHAR(255) NOT NULL,
                video_url VARCHAR(255),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')
        
        # Create device_checks table
        await connection.execute('''
            CREATE TABLE IF NOT EXISTS device_checks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                has_multiple_keyboards BOOLEAN NOT NULL,
                has_external_monitors BOOLEAN NOT NULL,
                keyboard_count INTEGER NOT NULL,
                monitor_count INTEGER NOT NULL,
                detected_devices JSONB,
                check_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')
        
        # Create admin_users table
        await connection.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')
        
        # Insert default admin user if not exists
        admin_exists = await connection.fetchval(
            "SELECT COUNT(*) FROM admin_users WHERE username = 'admin'"
        )
        if admin_exists == 0:
            admin_password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            await connection.execute(
                "INSERT INTO admin_users (username, password_hash) VALUES ($1, $2)",
                "admin", admin_password_hash
            )

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

class ExamLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    log_id: str
    reason: str
    student_id: str
    exam_session_id: str
    video_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExamLogCreate(BaseModel):
    log_id: str
    reason: str
    student_id: str
    exam_session_id: str
    video_url: Optional[str] = None

class DeviceCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    has_multiple_keyboards: bool
    has_external_monitors: bool
    keyboard_count: int
    monitor_count: int
    detected_devices: List[str] = []
    check_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeviceCheckCreate(BaseModel):
    has_multiple_keyboards: bool
    has_external_monitors: bool
    keyboard_count: int
    monitor_count: int
    detected_devices: List[str] = []

class SpeechDetectionResult(BaseModel):
    speech_detected: bool
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# JWT token verification (simplified for demo)
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # In a real app, verify the JWT token
    # For now, just return True for any token
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Token required")
    return True

# Routes
@api_router.get("/")
async def root():
    return {"message": "Secure Exam Platform API"}

# Admin Authentication
@api_router.post("/admin/login")
async def admin_login(username: str = Form(...), password: str = Form(...)):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    async with pg_pool.acquire() as connection:
        admin = await connection.fetchrow(
            "SELECT * FROM admin_users WHERE username = $1 AND password_hash = $2",
            username, password_hash
        )
        
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate a simple token (in production, use proper JWT)
        token = hashlib.sha256(f"{username}:{password}:{datetime.now()}".encode()).hexdigest()
        
        return {"access_token": token, "token_type": "bearer"}

# Question Management
@api_router.post("/admin/questions", dependencies=[Depends(verify_token)])
async def create_question(question: QuestionCreate):
    async with pg_pool.acquire() as connection:
        question_id = await connection.fetchval(
            """INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_answer)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            question.question_text, question.option_a, question.option_b,
            question.option_c, question.option_d, question.correct_answer
        )
        
        return {"id": str(question_id), "message": "Question created successfully"}

@api_router.get("/admin/questions", dependencies=[Depends(verify_token)])
async def get_all_questions():
    async with pg_pool.acquire() as connection:
        rows = await connection.fetch("SELECT * FROM questions ORDER BY created_at DESC")
        
        questions = []
        for row in rows:
            questions.append({
                "id": str(row['id']),
                "question_text": row['question_text'],
                "option_a": row['option_a'],
                "option_b": row['option_b'],
                "option_c": row['option_c'],
                "option_d": row['option_d'],
                "correct_answer": row['correct_answer'],
                "created_at": row['created_at'].isoformat()
            })
        
        return questions

@api_router.get("/questions")
async def get_questions():
    async with pg_pool.acquire() as connection:
        rows = await connection.fetch("SELECT * FROM questions ORDER BY created_at DESC")
        
        questions = []
        for row in rows:
            # Don't include correct_answer for students
            questions.append({
                "id": str(row['id']),
                "question_text": row['question_text'],
                "option_a": row['option_a'],
                "option_b": row['option_b'],
                "option_c": row['option_c'],
                "option_d": row['option_d']
            })
        
        return questions

@api_router.delete("/admin/questions/{question_id}", dependencies=[Depends(verify_token)])
async def delete_question(question_id: str):
    async with pg_pool.acquire() as connection:
        result = await connection.execute(
            "DELETE FROM questions WHERE id = $1", uuid.UUID(question_id)
        )
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Question not found")
        
        return {"message": "Question deleted successfully"}

# Exam Logs
@api_router.post("/exam/logs")
async def create_exam_log(log: ExamLogCreate):
    async with pg_pool.acquire() as connection:
        log_id = await connection.fetchval(
            """INSERT INTO exam_logs (log_id, reason, student_id, exam_session_id, video_url)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            log.log_id, log.reason, log.student_id, log.exam_session_id, log.video_url
        )
        
        return {"id": str(log_id), "message": "Log created successfully"}

@api_router.get("/admin/logs", dependencies=[Depends(verify_token)])
async def get_exam_logs():
    async with pg_pool.acquire() as connection:
        rows = await connection.fetch("SELECT * FROM exam_logs ORDER BY timestamp DESC")
        
        logs = []
        for row in rows:
            logs.append({
                "id": str(row['id']),
                "log_id": row['log_id'],
                "reason": row['reason'],
                "student_id": row['student_id'],
                "exam_session_id": row['exam_session_id'],
                "video_url": row['video_url'],
                "timestamp": row['timestamp'].isoformat()
            })
        
        return logs

# Device Check
@api_router.post("/device/check")
async def device_check(check: DeviceCheckCreate):
    async with pg_pool.acquire() as connection:
        check_id = await connection.fetchval(
            """INSERT INTO device_checks (has_multiple_keyboards, has_external_monitors, keyboard_count, monitor_count, detected_devices)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            check.has_multiple_keyboards, check.has_external_monitors,
            check.keyboard_count, check.monitor_count, json.dumps(check.detected_devices)
        )
        
        return {"id": str(check_id), "message": "Device check recorded successfully"}

@api_router.get("/admin/device-checks", dependencies=[Depends(verify_token)])
async def get_device_checks():
    async with pg_pool.acquire() as connection:
        rows = await connection.fetch("SELECT * FROM device_checks ORDER BY check_timestamp DESC LIMIT 100")
        
        checks = []
        for row in rows:
            checks.append({
                "id": str(row['id']),
                "has_multiple_keyboards": row['has_multiple_keyboards'],
                "has_external_monitors": row['has_external_monitors'],
                "keyboard_count": row['keyboard_count'],
                "monitor_count": row['monitor_count'],
                "detected_devices": json.loads(row['detected_devices']),
                "check_timestamp": row['check_timestamp'].isoformat()
            })
        
        return checks

# Speech Detection Route
@api_router.post("/exam/detect-speech", response_model=SpeechDetectionResult)
async def detect_speech_in_audio(
    audio: UploadFile = File(...),
    student_id: str = Form(...),
    exam_session_id: str = Form(...),
    timestamp: str = Form(...)
):
    try:
        # Read audio data
        audio_bytes = await audio.read()
        logger.info(f"Received audio chunk: {len(audio_bytes)} bytes from student {student_id}")
        
        # Detect speech in the audio chunk
        speech_detected = detect_speech_from_bytes(audio_bytes, audio.content_type or "audio/webm")
        
        result = SpeechDetectionResult(
            speech_detected=speech_detected,
            message="Human speech detected" if speech_detected else "No human speech detected"
        )
        
        if speech_detected:
            # Log the speech detection as a violation
            violation_log = ExamLogCreate(
                log_id=f"speech_detected_{int(datetime.now().timestamp())}",
                reason="SPEECH_DETECTED: Human speech detected during exam",
                student_id=student_id,
                exam_session_id=exam_session_id
            )
            
            # Save violation to database
            try:
                async with pg_pool.acquire() as connection:
                    await connection.execute(
                        """INSERT INTO exam_logs (log_id, reason, student_id, exam_session_id)
                           VALUES ($1, $2, $3, $4)""",
                        violation_log.log_id, violation_log.reason,
                        violation_log.student_id, violation_log.exam_session_id
                    )
                logger.info(f"Speech violation logged for student {student_id}")
            except Exception as log_error:
                logger.error(f"Failed to log speech violation: {log_error}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in speech detection endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Speech detection failed: {str(e)}")

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

# Initialize speech detection on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Secure Exam Platform API...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized successfully")
    
    # Initialize speech detection
    try:
        initialize_speech_detection()
        logger.info("Speech detection model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize speech detection: {e}")
        logger.warning("Speech detection will not be available")

@app.on_event("shutdown")
async def shutdown_event():
    if pg_pool:
        await pg_pool.close()