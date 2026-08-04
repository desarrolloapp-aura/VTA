from fastapi import FastAPI, Request, Form, Depends, Cookie, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
import pandas as pd
import json
import os
import time
import threading
import io
import urllib.request
import asyncio
from supabase import create_client, Client

app = FastAPI(title="Dashboard VTA")

templates = Jinja2Templates(directory="templates")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

cached_json = None
last_cache_time = 0
is_fetching = False
data_lock = threading.Lock()

def process_excel_data():
    url = os.environ.get('EXCEL_URL')
    if not url:
        raise ValueError("La variable de entorno EXCEL_URL no está configurada en Render.")
    
    # Descargar el archivo a la memoria UNA SOLA VEZ para acelerar al doble
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        file_bytes = io.BytesIO(response.read())
        
    df_raw = pd.read_excel(file_bytes, sheet_name='Venta', header=None)
    
    # Buscar columnas de grupos (G1, G2) en la fila de encabezados (fila 2, index 1)
    col_aa_idx, col_ab_idx = 26, 27
    for i, val in enumerate(df_raw.iloc[1]):
        if str(val).strip() == 'G1': col_aa_idx = i
        elif str(val).strip() == 'G2': col_ab_idx = i
        
    df_raw[2] = df_raw[2].ffill()
    
    group_data = {}
    current_g_aa = 'G1'
    current_g_ab = 'G2'
    
    values = df_raw.values
    for row in values:
        val_aa = row[col_aa_idx]
        val_ab = row[col_ab_idx]
        
        if isinstance(val_aa, str) and str(val_aa).strip().startswith('G'):
            current_g_aa = str(val_aa).strip()
            current_g_ab = str(val_ab).strip() if pd.notna(val_ab) else None
            continue
            
        dia = row[2]
        turno = row[3]
        
        if pd.notna(dia) and str(dia) != 'Dia' and not str(dia).startswith('Unnamed'):
            if pd.notna(turno):
                key = f"{dia}_{turno}"
                if key not in group_data: group_data[key] = {}
                
                try:
                    group_data[key][current_g_aa] = float(val_aa) if pd.notna(val_aa) else 0
                except:
                    pass
                    
                if current_g_ab:
                    try:
                        group_data[key][current_g_ab] = float(val_ab) if pd.notna(val_ab) else 0
                    except:
                        pass

    # Procesamiento normal (leer de nuevo desde memoria)
    file_bytes.seek(0)
    df = pd.read_excel(file_bytes, sheet_name='Venta', header=1)
    
    # Llenar las fechas combinadas
    df['Raw_Dia'] = df['Dia']
    df['Dia'] = df['Dia'].ffill()
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
            if str(k) in ['G1', 'G2', 'Raw_Dia']:
                continue
            clean_r[str(k)] = v
            
        # Inyectar grupos dinámicos
        key = f"{r.get('Raw_Dia')}_{r.get('T°')}"
        if key in group_data:
            for g_col, g_val in group_data[key].items():
                clean_r[g_col] = g_val
                
        # Si no se inyectó un grupo particular, inicializarlo en 0 para evitar errores de renderizado
        for g in ['G1', 'G2', 'G3', 'G4']:
            if g not in clean_r:
                clean_r[g] = 0
                
        cleaned_records.append(clean_r)
        
    return json.dumps({"data": cleaned_records, "error": None}, default=str)

def fetch_data_background():
    global cached_json, last_cache_time, is_fetching
    if is_fetching: return
    is_fetching = True
    try:
        with data_lock:
            json_content = process_excel_data()
            cached_json = json_content
            last_cache_time = time.time()
    except Exception as e:
        print("Error en pre-carga de login:", e)
    finally:
        is_fetching = False

def verify_session(request: Request):
    if not supabase:
        return None
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        user = supabase.auth.get_user(token)
        return user
    except:
        return None

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(fetch_data_background)
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    if not supabase:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Supabase no está configurado en el servidor"})
        
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        token = response.session.access_token
        
        redirect = RedirectResponse(url="/", status_code=303)
        redirect.set_cookie(key="access_token", value=token, httponly=True, max_age=3600*24)
        return redirect
    except Exception as e:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Credenciales inválidas"})

@app.get("/logout")
async def logout():
    redirect = RedirectResponse(url="/login", status_code=303)
    redirect.delete_cookie("access_token")
    return redirect

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    if not supabase:
        return HTMLResponse("Falta configurar SUPABASE_URL y SUPABASE_KEY en Render")
        
    user = verify_session(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    return templates.TemplateResponse(request=request, name="dashboard.html")

# Cambiamos async def por def normal para que FastAPI lo ejecute en un Threadpool
# y no bloquee el hilo principal mientras Pandas procesa.
@app.get("/api/data")
def get_data(request: Request, background_tasks: BackgroundTasks):
    global cached_json, last_cache_time
    
    if supabase:
        user = verify_session(request)
        if not user:
            return Response(content=json.dumps({"error": "No autorizado"}), status_code=401)

    current_time = time.time()
    
    # ESTRATEGIA STALE-WHILE-REVALIDATE: 
    # Si hay caché, lo devolvemos INSTANTÁNEAMENTE (0 segundos de espera).
    # Si el caché tiene más de 5 minutos, lanzamos una tarea invisible para actualizarlo
    # en segundo plano, así la próxima vez tendrá los datos frescos sin hacer esperar a nadie.
    if cached_json:
        if (current_time - last_cache_time) > 300: # 5 minutos (300s)
            background_tasks.add_task(fetch_data_background)
        return Response(content=cached_json, media_type="application/json")
        
    # Si no hay caché absoluto (primer inicio del servidor), debemos procesarlo
    try:
        # Bloqueamos para asegurar que solo un proceso a la vez lea el Excel
        with data_lock:
            if cached_json and (time.time() - last_cache_time) < 300:
                return Response(content=cached_json, media_type="application/json")
            json_content = process_excel_data()
            cached_json = json_content
            last_cache_time = time.time()
        return Response(content=json_content, media_type="application/json")
    except Exception as e:
        json_content = json.dumps({"data": [], "error": str(e)}, default=str)
        return Response(content=json_content, media_type="application/json", status_code=500)
