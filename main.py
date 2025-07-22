# main.py (Versión con perfiles y autenticación)

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

# --- 1. CONFIGURACIÓN DE SEGURIDAD Y DE LA APP ---
app = FastAPI(title="Panel de Salud Personal con Autenticación")

SECRET_KEY = "un-secreto-muy-dificil-de-adivinar-y-super-largo"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- 2. MODELOS DE DATOS (PYDANTIC) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    photo_url: Optional[str] = None

class UserInDB(User):
    hashed_password: str
    health_data: List[Dict] = [] # Aquí se guardarán los datos de salud por usuario

# --- 3. BASE DE DATOS FALSA Y UTILIDADES ---

# GitHub Repo URL Base (Reemplaza 'tu-usuario' y 'tu-repo' por los tuyos)
# Usaremos esto para construir las URLs de las fotos de perfil
# GitHub sirve los archivos crudos a través de esta URL
GITHUB_RAW_URL = "https://raw.githubusercontent.com/tu-usuario/tu-repo/main/"

fake_users_db = {
    "paciente_a": {
        "username": "paciente_a",
        "full_name": "Ana García",
        "hashed_password": "$2b$12$EixZaY2Jz9pLws/5yLxl..NwkBSpj4Cwj5IEu3k01y5PbTcw6WbI.", # Contraseña: "pass_ana"
        "photo_url": GITHUB_RAW_URL + "user1_photo.png",
        "health_data": []
    },
    "paciente_b": {
        "username": "paciente_b",
        "full_name": "Luis Martínez",
        "hashed_password": "$2b$12$a4HnE5bC3h/9d.Q1q3dG5uVbXgP4rXbY.Z1p6eFqRkLh1sE0/3h0q", # Contraseña: "pass_luis"
        "photo_url": GITHUB_RAW_URL + "user2_photo.png",
        "health_data": []
    }
}

# (Las funciones verify_password, get_user, create_access_token son las mismas que antes)
# ...
def verify_password(plain_password, hashed_password): return pwd_context.verify(plain_password, hashed_password)
def get_user_data(username: str):
    if username in fake_users_db: return UserInDB(**fake_users_db[username])
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
async def get_current_user(token: str = Depends(oauth2_scheme)):
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

# --- 4. ENDPOINTS DE LA API ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_data(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# NUEVO Endpoint para obtener los datos del perfil del usuario
@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Endpoint PROTEGIDO para subir datos
@app.post("/upload-data")
async def upload_health_data(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # (El código para procesar el Excel es idéntico al que ya teníamos)
    # ...
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

# Endpoint PROTEGIDO para obtener los datos de salud
@app.get("/get-data")
async def get_health_data(current_user: User = Depends(get_current_user)):
    return fake_users_db[current_user.username]["health_data"]
    except Exception as e:
        # Este es un error inesperado. Ayuda a depurar.
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado al procesar el archivo: {e}")
