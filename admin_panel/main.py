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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123") # Cambiar en Render

if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
else:
    supabase = None
    print("ADVERTENCIA: Faltan credenciales de Supabase (URL o SERVICE_KEY).")

def verify_admin(request: Request):
    token = request.cookies.get("admin_token")
    if token == ADMIN_PASSWORD:
        return True
    return False

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if verify_admin(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def do_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="admin_token", value=password, httponly=True, secure=True)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Contraseña incorrecta."})

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
        # Parse users
        users = [{"id": u.id, "email": u.email, "created_at": str(u.created_at)} for u in res]
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
        res = supabase.auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
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
