import os
import json
from fastapi import FastAPI, Request, Form, Response, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Credenciales maestras (¡NUNCA COMPARTIR!)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    # Creamos un cliente global solo para cosas que no muten el estado
    pass
else:
    print("ADVERTENCIA: Faltan credenciales de Supabase (URL o SERVICE_KEY).")

def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def verify_admin(request: Request):
    token = request.cookies.get("admin_token")
    if not token:
        return False
    try:
        db = get_client()
        # Validar el token real de Supabase
        user_res = db.auth.get_user(token)
        if user_res and user_res.user:
            role = user_res.user.user_metadata.get("role")
            if role == "admin":
                return True
    except Exception:
        pass
    return False

@app.get("/")
def index(request: Request):
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login")
def login_page(request: Request):
    if verify_admin(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def do_login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        db = get_client()
        # Intentar iniciar sesión real contra Supabase
        res = db.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            role = res.user.user_metadata.get("role")
            if role == "admin":
                # Login exitoso y es administrador
                response = RedirectResponse(url="/dashboard", status_code=302)
                # Guardamos el token real que nos dio Supabase en la cookie
                response.set_cookie(key="admin_token", value=res.session.access_token, httponly=True, secure=True)
                return response
            else:
                return templates.TemplateResponse(request=request, name="login.html", context={"error": "Este usuario no tiene privilegios de administrador."})
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower():
            return templates.TemplateResponse(request=request, name="login.html", context={"error": "Credenciales inválidas."})
        return templates.TemplateResponse(request=request, name="login.html", context={"error": error_msg})

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("admin_token")
    return response

@app.get("/dashboard")
def dashboard(request: Request):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/api/users")
def get_users(request: Request):
    if not verify_admin(request):
        return Response(status_code=401)
    if not SUPABASE_URL:
        return JSONResponse(status_code=500, content={"error": "Supabase no está configurado."})
    
    try:
        db = get_client()
        # El SDK de python expone admin.list_users()
        res = db.auth.admin.list_users()
        # Parse users y sacar rol
        users = []
        for u in res:
            role = u.user_metadata.get("role", "viewer")
            users.append({
                "id": u.id, 
                "email": u.email, 
                "created_at": str(u.created_at),
                "role": role
            })
        return JSONResponse(content={"users": users})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def send_webhook_email(webhook_url: str, email: str, password: str):
    try:
        with httpx.Client() as client:
            client.post(webhook_url, json={"email": email, "password": password}, timeout=20.0, follow_redirects=True)
    except Exception as hook_err:
        print(f"Error al enviar correo por webhook: {hook_err}")

@app.post("/api/users")
async def create_user(request: Request, background_tasks: BackgroundTasks):
    if not verify_admin(request):
        return Response(status_code=401)
    
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    
    try:
        db = get_client()
        res = db.auth.admin.create_user({
            "email": email, 
            "password": password, 
            "email_confirm": True,
            "user_metadata": {"role": "viewer"}
        })
        
        # Enviar correo usando el Webhook de Google (si está configurado) en segundo plano
        webhook_url = os.environ.get("GOOGLE_WEBHOOK_URL")
        if webhook_url:
            background_tasks.add_task(send_webhook_email, webhook_url, email, password)
                
        return JSONResponse(content={"success": True, "user": res.user.email})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.delete("/api/users/{uid}")
def delete_user(request: Request, uid: str):
    if not verify_admin(request):
        return Response(status_code=401)
    
    try:
        db = get_client()
        db.auth.admin.delete_user(uid)
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
