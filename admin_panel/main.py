import os
import json
from fastapi import FastAPI, Request, Form, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Credenciales maestras (¡NUNCA COMPARTIR!)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
else:
    supabase = None
    print("ADVERTENCIA: Faltan credenciales de Supabase (URL o SERVICE_KEY).")

def verify_admin(request: Request):
    token = request.cookies.get("admin_token")
    if not token:
        return False
    try:
        # Validar el token real de Supabase
        user_res = supabase.auth.get_user(token)
        if user_res and user_res.user:
            role = user_res.user.user_metadata.get("role")
            if role == "admin":
                return True
    except Exception:
        pass
    return False

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if verify_admin(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def do_login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        # Intentar iniciar sesión real contra Supabase
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            role = res.user.user_metadata.get("role")
            if role == "admin":
                # Login exitoso y es administrador
                response = RedirectResponse(url="/dashboard", status_code=302)
                # Guardamos el token real que nos dio Supabase en la cookie
                response.set_cookie(key="admin_token", value=res.session.access_token, httponly=True, secure=True)
                return response
            else:
                return templates.TemplateResponse("login.html", {"request": request, "error": "Este usuario no tiene privilegios de administrador."})
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower():
            return templates.TemplateResponse("login.html", {"request": request, "error": "Correo o contraseña incorrectos."})
        return templates.TemplateResponse("login.html", {"request": request, "error": error_msg})

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("admin_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    if not verify_admin(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/api/users")
def get_users(request: Request):
    if not verify_admin(request):
        return Response(status_code=401)
    if not supabase:
        return JSONResponse(status_code=500, content={"error": "Supabase no está configurado con Service Key."})
    
    try:
        # El SDK de python expone admin.list_users()
        res = supabase.auth.admin.list_users()
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

@app.post("/api/users")
async def create_user(request: Request):
    if not verify_admin(request):
        return Response(status_code=401)
    
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    
    try:
        res = supabase.auth.admin.create_user({
            "email": email, 
            "password": password, 
            "email_confirm": True,
            "user_metadata": {"role": "viewer"}
        })
        return JSONResponse(content={"success": True, "user": res.user.email})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.delete("/api/users/{uid}")
def delete_user(request: Request, uid: str):
    if not verify_admin(request):
        return Response(status_code=401)
    
    try:
        supabase.auth.admin.delete_user(uid)
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
