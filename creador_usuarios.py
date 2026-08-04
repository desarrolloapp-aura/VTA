import os
import sys
import json
import customtkinter as ctk
import tkinter.messagebox as messagebox

try:
    from supabase import create_client, Client
except ImportError:
    pass

CONFIG_FILE = "config.json"

# Configuración del tema (Imitando el fondo oscuro y detalles teal)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green") 

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("VTA Analytics - Creador de Usuarios")
        self.geometry("450x550")
        self.resizable(False, False)
        
        # Colores personalizados basados en el UI de Stitch
        self.bg_color = "#0e1513"
        self.surface_color = "#161d1b"
        self.primary_color = "#2dd4bf"
        self.text_color = "#dde4e1"
        self.text_muted = "#859490"
        
        self.configure(fg_color=self.bg_color)
        
        # Estado
        self.supabase_url = ""
        self.supabase_key = ""
        
        # Contenedor Principal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Inicializar Pantallas
        self.config_frame = self.create_config_frame()
        self.register_frame = self.create_register_frame()
        
        # Cargar configuración e iniciar en la pantalla correcta
        self.load_config()

    def create_config_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color=self.surface_color, corner_radius=15)
        
        # Titulo
        title = ctk.CTkLabel(frame, text="Configuración (Supabase)", font=("Helvetica", 20, "bold"), text_color=self.text_color)
        title.pack(pady=(40, 30))
        
        # URL
        lbl_url = ctk.CTkLabel(frame, text="URL del Proyecto", text_color=self.text_muted, font=("Helvetica", 12))
        lbl_url.pack(anchor="w", padx=30)
        self.entry_url = ctk.CTkEntry(frame, width=350, height=40, fg_color=self.bg_color, border_color="#3c4a46", text_color=self.text_color)
        self.entry_url.pack(padx=30, pady=(0, 20))
        
        # Key
        lbl_key = ctk.CTkLabel(frame, text="Llave Pública (anon key)", text_color=self.text_muted, font=("Helvetica", 12))
        lbl_key.pack(anchor="w", padx=30)
        self.entry_key = ctk.CTkEntry(frame, width=350, height=40, fg_color=self.bg_color, border_color="#3c4a46", text_color=self.text_color, show="*")
        self.entry_key.pack(padx=30, pady=(0, 40))
        
        # Boton Guardar
        btn_save = ctk.CTkButton(frame, text="Guardar y Continuar", height=45, fg_color=self.primary_color, text_color="#003731", hover_color="#57f1db", font=("Helvetica", 14, "bold"), command=self.save_config)
        btn_save.pack(padx=30, pady=(0, 30), fill="x")
        
        return frame

    def create_register_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color=self.surface_color, corner_radius=15)
        
        # Titulo
        title = ctk.CTkLabel(frame, text="Registro de Nuevo Usuario", font=("Helvetica", 20, "bold"), text_color=self.text_color)
        title.pack(pady=(40, 30))
        
        # Email
        lbl_email = ctk.CTkLabel(frame, text="Correo Electrónico", text_color=self.text_muted, font=("Helvetica", 12))
        lbl_email.pack(anchor="w", padx=30)
        self.entry_email = ctk.CTkEntry(frame, width=350, height=40, fg_color=self.bg_color, border_color="#3c4a46", text_color=self.text_color)
        self.entry_email.pack(padx=30, pady=(0, 20))
        
        # Password
        lbl_pwd = ctk.CTkLabel(frame, text="Contraseña (mínimo 6)", text_color=self.text_muted, font=("Helvetica", 12))
        lbl_pwd.pack(anchor="w", padx=30)
        self.entry_pwd = ctk.CTkEntry(frame, width=350, height=40, fg_color=self.bg_color, border_color="#3c4a46", text_color=self.text_color, show="*")
        self.entry_pwd.pack(padx=30, pady=(0, 30))
        
        # Boton Registro
        self.btn_register = ctk.CTkButton(frame, text="Crear Usuario", height=45, fg_color=self.primary_color, text_color="#003731", hover_color="#57f1db", font=("Helvetica", 14, "bold"), command=self.register_user)
        self.btn_register.pack(padx=30, fill="x")
        
        # Boton Volver
        btn_back = ctk.CTkButton(frame, text="Volver a Configuración", height=30, fg_color="transparent", text_color=self.text_muted, hover_color=self.bg_color, command=self.show_config)
        btn_back.pack(padx=30, pady=20)
        
        return frame

    def show_config(self):
        self.register_frame.pack_forget()
        self.config_frame.pack(fill="both", expand=True)
        
    def show_register(self):
        self.config_frame.pack_forget()
        self.register_frame.pack(fill="both", expand=True)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.supabase_url = data.get("url", "")
                    self.supabase_key = data.get("key", "")
                    
                if self.supabase_url and self.supabase_key:
                    self.entry_url.insert(0, self.supabase_url)
                    self.entry_key.insert(0, self.supabase_key)
                    self.show_register()
                    return
            except Exception:
                pass
        self.show_config()

    def save_config(self):
        url = self.entry_url.get().strip()
        key = self.entry_key.get().strip()
        
        if not url or not key:
            messagebox.showerror("Error", "Debes completar ambos campos.")
            return
            
        self.supabase_url = url
        self.supabase_key = key
        
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"url": url, "key": key}, f)
            self.show_register()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")

    def register_user(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_pwd.get().strip()
        
        if not email or not pwd:
            messagebox.showerror("Error", "Faltan datos. Ingresa correo y contraseña.")
            return
        if len(pwd) < 6:
            messagebox.showerror("Error", "La contraseña debe tener al menos 6 caracteres.")
            return
            
        self.btn_register.configure(state="disabled", text="Procesando...")
        self.update()
        
        try:
            supabase: Client = create_client(self.supabase_url, self.supabase_key)
            res = supabase.auth.sign_up({
                "email": email,
                "password": pwd,
            })
            
            if hasattr(res, 'user') and res.user:
                messagebox.showinfo("¡Éxito!", f"El usuario {email} ha sido creado correctamente.")
                self.entry_email.delete(0, 'end')
                self.entry_pwd.delete(0, 'end')
            else:
                messagebox.showerror("Error", "Error desconocido al crear el usuario.")
        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                messagebox.showerror("Error", "Este correo electrónico ya está registrado.")
            elif "invalid login credentials" in error_msg.lower():
                messagebox.showerror("Error", "Las llaves de Supabase son incorrectas. Vuelve a configuración y revísalas.")
            else:
                messagebox.showerror("Error", error_msg[:60])
                
        self.btn_register.configure(state="normal", text="Crear Usuario")

if __name__ == "__main__":
    app = App()
    app.mainloop()
