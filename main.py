# main.py (Versión Robusta)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

# 1. Crear la aplicación FastAPI
app = FastAPI(title="API de Visualización de Datos de Salud")

# 2. Configurar CORS (sin cambios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Crear el endpoint que manejará la subida del archivo
@app.post("/upload-data")
async def upload_health_data(file: UploadFile = File(...)):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx).")

    try:
        # Leer el contenido del archivo
        contents = await file.read()
        
        # --- MEJORAS DE ROBUSTEZ ---
        
        # Columnas que esperamos y sus tipos de datos
        expected_columns = {
            "Fecha": "datetime64[ns]",
            "PA Sistólica": "Int64", # Usamos Int64 para permitir valores nulos si los hubiera
            "PA Diastólica": "Int64",
            "Glucosa (mg/dL)": "Int64",
            "Peso (kg)": "float64"
        }
        
        # Leer el Excel especificando los tipos de datos.
        # Si una columna no existe o tiene un tipo incorrecto, esto fallará
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl", dtype=expected_columns)
        
        # Validar que todas las columnas esperadas están presentes
        if not all(col in df.columns for col in expected_columns.keys()):
            raise ValueError("El archivo Excel no contiene todas las columnas requeridas: Fecha, PA Sistólica, PA Diastólica, Glucosa (mg/dL), Peso (kg).")
            
        # Limpiar filas que puedan estar completamente vacías
        df.dropna(how='all', inplace=True)

        if df.empty:
            raise ValueError("El archivo Excel está vacío o no contiene datos válidos.")

        # Estandarizar el formato de la fecha
        df['Fecha'] = pd.to_datetime(df['Fecha']).dt.strftime('%Y-%m-%d')
        
        # --- FIN DE MEJORAS ---

        data_json = df.to_dict(orient='records')
        
        return {"filename": file.filename, "data": data_json}
        
    except ValueError as ve:
        # Este es un error "controlado", ej. falta una columna. Damos un mensaje claro.
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        # Este es un error inesperado. Ayuda a depurar.
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado al procesar el archivo: {e}")
