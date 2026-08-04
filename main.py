from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import pandas as pd
import json
import os

app = FastAPI(title="Dashboard VTA")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    # Obtener URL desde variable de entorno, con fallback a la original por defecto
    default_url = 'https://docs.google.com/uc?export=download&id=1t9cp6K-dcbiVbZTx_VQ76fpTrmx6VUL8'
    url = os.environ.get('EXCEL_URL', default_url)
    
    try:
        # Descargamos directamente la hoja 'Venta' del excel de drive
        df = pd.read_excel(url, sheet_name='Venta', header=1)
        
        # Llenar las fechas combinadas (Turno A y B comparten la misma fecha)
        df['Dia'] = df['Dia'].ffill()
        # Limpiar datos: remover filas donde 'Dia' es nulo o es encabezado
        df = df.dropna(subset=['Dia'])
        df = df[df['Dia'] != 'Dia']
        # Formatear la fecha
        df['Dia'] = pd.to_datetime(df['Dia']).dt.strftime('%d-%b')
        
        records = df.to_dict('records')
        cleaned_records = []
        for r in records:
            clean_r = {}
            for k, v in r.items():
                if pd.isna(v) or str(k).startswith('Unnamed:'):
                    continue
                clean_r[str(k)] = v
            cleaned_records.append(clean_r)
            
        context = {
            "request": request,
            'datos_excel': json.dumps(cleaned_records, default=str),
            'error': None
        }
    except Exception as e:
        context = {
            "request": request,
            'datos_excel': '[]',
            'error': str(e)
        }
        
    return templates.TemplateResponse("dashboard.html", context)
