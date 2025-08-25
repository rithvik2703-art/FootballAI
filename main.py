from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models

# ------------------------------
# Load environment variables
# ------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

file_path = "./links.txt"

app = FastAPI(title="Soccer AI API", version="1.0.0")

links_content = ""
try:
    with open(file_path, 'r') as f:
        links_content = f.read()
except FileNotFoundError:
    links_content = "Links file not found."

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://footballai.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Security / JWT Setup
# ------------------------------
with open("private.pem", "r") as f:
    PRIVATE_KEY = f.read()
with open("public.pem", "r") as f:
    PUBLIC_KEY = f.read()

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ------------------------------
# Database setup
# ------------------------------
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
# Models
# ------------------------------
class UserProfile(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    expertise: Optional[str] = None
    time: Optional[int] = None

class CoachRequest(BaseModel):
    query: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str

# ------------------------------
# Helper Functions
# ------------------------------

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)



def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
# ------------------------------
# Auth Endpoints
# ------------------------------
@app.get("/")
def root():
    return {"message": "Soccer AI API is running 🚀"}

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username exists")

    hashed_pw = get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered"}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ------------------------------
# User Profile
# ------------------------------
@app.post("/v1/user/profile")
def create_or_update_profile(profile: UserProfile, db: Session = Depends(get_db), current_username: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.profile:  # update existing
        for key, value in profile.dict().items():
            setattr(user.profile, key, value)
    else:  # create new
        new_profile = models.Profile(**profile.dict(), owner=user)
        db.add(new_profile)

    db.commit()
    return {"message": "Profile updated successfully", "profile": profile.dict()}

@app.get("/v1/user/profile")
def get_profile(db: Session = Depends(get_db), current_username: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_username).first()
    if not user or not user.profile:
        return {}
    return {
        "name": user.profile.name,
        "age": user.profile.age,
        "weight": user.profile.weight,
        "height": user.profile.height,
        "strengths": user.profile.strengths,
        "weaknesses": user.profile.weaknesses,
        "expertise": user.profile.expertise,
        "time": user.profile.time
    }

# ------------------------------
# Coach AI with Chat History
# ------------------------------
@app.post("/v1/coach")
async def soccer_coach(req: CoachRequest, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build profile context
    profile = user.profile
    profile_context = "No profile provided."
    if profile:
        profile_parts = []
        if profile.name: profile_parts.append(f"Name: {profile.name}")
        if profile.age: profile_parts.append(f"Age: {profile.age}")
        if profile.weight: profile_parts.append(f"Weight (kg): {profile.weight}")
        if profile.height: profile_parts.append(f"Height (cm): {profile.height}")
        if profile.strengths: profile_parts.append(f"Strengths: {profile.strengths}")
        if profile.weaknesses: profile_parts.append(f"Weaknesses: {profile.weaknesses}")
        if profile.expertise: profile_parts.append(f"Expertise (in months): {profile.expertise}")
        if profile.time: profile_parts.append(f"Free time per day (minutes): {profile.time}")
        profile_context = "\n".join(profile_parts)

    # Load history
    history = [{"role": c.role, "content": c.content} for c in user.chats]
    history.append({"role": "user", "content": req.query})

    system_prompt = (
        "You are an AI Coach specializing in football, fitness, and health. "
        "Please provide personalized advice along with a daily plan(based on amount of time with brief instructions on what to do every session.) "
        f"Profile:\n{profile_context}\n"
        f"LINKS:\n{links_content}"
    )

    messages = [{"role": "system", "content": system_prompt}] + history

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    answer = response.choices[0].message.content

    # Save conversation
    db.add(models.ChatHistory(role="user", content=req.query, owner=user))
    db.add(models.ChatHistory(role="assistant", content=answer, owner=user))
    db.commit()

    return {"answer": answer}

# ------------------------------
# Get Chat History
# ------------------------------
@app.get("/v1/chat/history")
async def get_chat_history(db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return [{"role": c.role, "content": c.content} for c in user.chats]

@app.delete("/v1/chat/history")
async def clear_chat_history(db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user.id).delete()
    db.commit()
    return {"message": "Chat history cleared."}

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
