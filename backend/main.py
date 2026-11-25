import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
load_dotenv()

import jwt

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends
)
from fastapi.responses import FileResponse
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from pwdlib import PasswordHash

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker


# ==========================================
# AASHI CLOUD APPLICATION
# ==========================================

app = FastAPI(
    title="Aashi Cloud",
    description="Global Cloud Deployment Platform",
    version="1.1.0"
)


# ==========================================
# CORS CONFIGURATION
# ==========================================

allowed_origins = os.getenv(
    "AASHI_ALLOWED_ORIGINS",
    "http://127.0.0.1:5500,http://localhost:5500"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"]
)


# ==========================================
# DATABASE
# ==========================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./aashi_cloud.db"
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

engine_args = {}

if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {
        "check_same_thread": False
    }

engine = create_engine(
    DATABASE_URL,
    **engine_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# ==========================================
# SECURITY CONFIGURATION
# ==========================================

password_hash = PasswordHash.recommended()

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing in .env file")

ALGORITHM = "HS256"

security = HTTPBearer()


def hash_password(password):
    return password_hash.hash(password)


def verify_password(password, hashed_password):
    return password_hash.verify(
        password,
        hashed_password
    )


def create_access_token(user_id):
    expire = datetime.now(timezone.utc) + timedelta(hours=24)

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ==========================================
# DATABASE MODELS
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    hashed_password = Column(
        String,
        nullable=False
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    framework = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        default="Draft"
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )


class CloudFile(Base):
    __tablename__ = "cloud_files"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    filename = Column(
        String,
        nullable=False
    )

    stored_filename = Column(
        String,
        nullable=False,
        unique=True
    )

    content_type = Column(
        String,
        nullable=True
    )

    size = Column(
        Integer,
        nullable=False
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )


Base.metadata.create_all(bind=engine)


# ==========================================
# FILE STORAGE CONFIGURATION
# ==========================================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024


# ==========================================
# REQUEST SCHEMAS
# ==========================================

class ProjectCreate(BaseModel):
    name: str
    framework: str


class ProjectUpdate(BaseModel):
    name: str
    framework: str
    status: str


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


# ==========================================
# AUTHENTICATION HELPER
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        user_id = int(user_id)

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    finally:
        db.close()


# ==========================================
# HOME API
# ==========================================

@app.get("/")
def home():
    return {
        "product": "Aashi Cloud",
        "company": "Aashi Tech",
        "status": "Running",
        "market": "Global"
    }


# ==========================================
# HEALTH API
# ==========================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ==========================================
# AUTH REGISTER
# ==========================================

@app.post("/auth/register")
def register(data: UserRegister):

    if not data.username.strip():
        raise HTTPException(
            status_code=400,
            detail="Username is required"
        )

    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters"
        )

    db = SessionLocal()

    try:
        existing_user = db.query(User).filter(
            User.username == data.username.strip()
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        user = User(
            username=data.username.strip(),
            hashed_password=hash_password(data.password)
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "message": "Registration successful",
            "user_id": user.id,
            "username": user.username
        }

    finally:
        db.close()


# ==========================================
# AUTH LOGIN
# ==========================================

@app.post("/auth/login")
def login(data: UserLogin):

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.username == data.username
        ).first()

        if not user or not verify_password(
            data.password,
            user.hashed_password
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        token = create_access_token(user.id)

        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer"
        }

    finally:
        db.close()


# ==========================================
# CREATE PROJECT
# ==========================================

@app.post("/projects")
def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        project = Project(
            name=data.name,
            framework=data.framework,
            user_id=current_user.id
        )

        db.add(project)
        db.commit()
        db.refresh(project)

        return {
            "message": "Project created",
            "id": project.id,
            "name": project.name,
            "framework": project.framework,
            "status": project.status
        }

    finally:
        db.close()


# ==========================================
# GET ALL PROJECTS
# ==========================================

@app.get("/projects")
def get_projects(
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        projects = db.query(Project).filter(
            Project.user_id == current_user.id
        ).all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "framework": p.framework,
                "status": p.status
            }
            for p in projects
        ]

    finally:
        db.close()


# ==========================================
# GET SINGLE PROJECT
# ==========================================

@app.get("/projects/{project_id}")
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()

        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        return {
            "id": project.id,
            "name": project.name,
            "framework": project.framework,
            "status": project.status
        }

    finally:
        db.close()


# ==========================================
# UPDATE PROJECT
# ==========================================

@app.put("/projects/{project_id}")
def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()

        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        project.name = data.name
        project.framework = data.framework
        project.status = data.status

        db.commit()
        db.refresh(project)

        return {
            "message": "Project updated",
            "id": project.id,
            "name": project.name,
            "framework": project.framework,
            "status": project.status
        }

    finally:
        db.close()


# ==========================================
# DELETE PROJECT
# ==========================================

@app.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()

        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        db.delete(project)
        db.commit()

        return {
            "message": "Project deleted successfully",
            "id": project_id
        }

    finally:
        db.close()


# ==========================================
# FILE MANAGER - UPLOAD
# ==========================================

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    original_name = file.filename.replace("\\", "/").split("/")[-1]

    if not original_name:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

    stored_name = str(uuid.uuid4())
    file_path = UPLOAD_DIR / stored_name

    size = 0

    try:
        with open(file_path, "wb") as output:

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Maximum file size is 50 MB"
                    )

                output.write(chunk)

        db = SessionLocal()

        try:
            new_file = CloudFile(
                filename=original_name,
                stored_filename=stored_name,
                content_type=file.content_type,
                size=size,
                user_id=current_user.id
            )

            db.add(new_file)
            db.commit()
            db.refresh(new_file)

            return {
                "message": "File uploaded successfully",
                "id": new_file.id,
                "filename": new_file.filename,
                "size": new_file.size,
                "uploaded_at": new_file.uploaded_at.isoformat()
            }

        finally:
            db.close()

    except Exception:
        if file_path.exists():
            os.remove(file_path)
        raise

    finally:
        await file.close()


# ==========================================
# FILE MANAGER - GET ALL FILES
# ==========================================

@app.get("/files")
def get_files(
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        files = db.query(CloudFile).filter(
            CloudFile.user_id == current_user.id
        ).order_by(
            CloudFile.id.desc()
        ).all()

        return [
            {
                "id": f.id,
                "filename": f.filename,
                "content_type": f.content_type,
                "size": f.size,
                "uploaded_at": f.uploaded_at.isoformat()
            }
            for f in files
        ]

    finally:
        db.close()


# ==========================================
# FILE MANAGER - DOWNLOAD
# ==========================================

@app.get("/files/{file_id}/download")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        cloud_file = db.query(CloudFile).filter(
            CloudFile.id == file_id,
            CloudFile.user_id == current_user.id
        ).first()

        if not cloud_file:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

        file_path = UPLOAD_DIR / cloud_file.stored_filename

        if not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Physical file not found"
            )

        return FileResponse(
            path=str(file_path),
            filename=cloud_file.filename,
            media_type=cloud_file.content_type or "application/octet-stream"
        )

    finally:
        db.close()


# ==========================================
# FILE MANAGER - DELETE
# ==========================================

@app.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user)
):

    db = SessionLocal()

    try:
        cloud_file = db.query(CloudFile).filter(
            CloudFile.id == file_id,
            CloudFile.user_id == current_user.id
        ).first()

        if not cloud_file:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

        file_path = UPLOAD_DIR / cloud_file.stored_filename

        if file_path.exists():
            os.remove(file_path)

        db.delete(cloud_file)
        db.commit()

        return {
            "message": "File deleted successfully",
            "id": file_id
        }

    finally:
        db.close()