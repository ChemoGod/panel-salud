# main.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

# 1. Crear la aplicación FastAPI
app = FastAPI(title="API de Visualización de Datos de Salud")

# 2. Configurar CORS para permitir la comunicación entre el frontend y el backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Crear la ruta (endpoint) que manejará la subida del archivo
@app.post("/upload-data")
async def upload_health_data(file: UploadFile = File(...)):
    # Validar que sea un archivo .xlsx
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx).")

    try:
        # Leer el contenido del archivo
        contents = await file.read()
        
        # Usar la librería Pandas para leer el archivo Excel
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
        
        # Asegurarnos de que la columna de fecha tenga un formato estándar
        df['Fecha'] = pd.to_datetime(df['Fecha']).dt.strftime('%Y-%m-%d')
        
        # Convertir los datos a un formato JSON, que es fácil de usar en la web
        data_json = df.to_dict(orient='records')
        
        # Devolver los datos procesados a la página web
        return {"filename": file.filename, "data": data_json}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo Excel: {e}")