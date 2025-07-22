od# main.py (Versión Corregida)

from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pandas as pd
import io

# 1. CONFIGURACIÓN
app = FastAPI(title="Panel de Salud Personal con Autenticación")
SECRET_KEY = "un-secreto-muy-dificil-de-adivinar-y-super-largo"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# 3. MODELOS DE DATOS
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    photo_url: Optional[str] = None

class UserInDB(User):
    hashed_password: str
    health_data: List[Dict] = []

# 4. BASE DE DATOS Y UTILIDADES DE SEGURIDAD
GITHUB_RAW_URL = "https://raw.githubusercontent.com/chemogod/panel-salud/main/" # <- ASEGÚRATE DE EDITAR ESTA LÍNEA

fake_users_db = {
    "paciente_a": {"username": "paciente_a", "full_name": "Ana García", "hashed_password": "$2b$12$EixZaY2Jz9pLws/5yLxl..NwkBSpj4Cwj5IEu3k01y5PbTcw6WbI.", "photo_url": GITHUB_RAW_URL + "user1_photo.png", "health_data": []},
    "paciente_b": {"username": "paciente_b", "full_name": "Luis Martínez", "hashed_password": "$2b$12$a4HnE5bC3h/9d.Q1q3dG5uVbXgP4rXbY.Z1p6eFqRkLh1sE0/3h0q", "photo_url": GITHUB_RAW_URL + "user2_photo.png", "health_data": []}
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_user_data(username: str) -> Optional[UserInDB]:
    if username in fake_users_db:
        return UserInDB(**fake_users_db[username])
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_data(username)
    if user is None: raise credentials_exception
    return user

# 5. ENDPOINTS
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_data(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/upload-data")
async def upload_health_data(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not file.filename.endswith('.xlsx'): raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx).")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
        df['Fecha'] = pd.to_datetime(df['Fecha']).dt.strftime('%Y-%m-%d')
        data_json = df.to_dict(orient='records')
        fake_users_db[current_user.username]["health_data"] = data_json
        return {"filename": file.filename, "message": f"Datos cargados para {current_user.username}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {e}")

@app.get("/get-data")
async def get_health_data(current_user: User = Depends(get_current_user)):
    return fake_users_db[current_user.username]["health_data"]
