import os
import json
import ctypes
import customtkinter as ctk

try:
    from supabase import create_client, Client
except ImportError:
    pass  # Asumimos que está instalado cuando se compila

# Archivo para guardar la configuración
CONFIG_FILE = "config.json"

# Configuración del tema (imitar diseño de Stitch)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green") # Cambiaremos colores manualmente para que sea "#2DD4BF"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Aura - Creador de Usuarios")
        self.geometry("450x650")
        self.configure(fg_color="#0F172A") # Fondo oscuro principal
        self.resizable(False, False)

        # Variables
        self.url_var = ctk.StringVar()
        self.key_var = ctk.StringVar()
        self.email_var = ctk.StringVar()
        self.password_var = ctk.StringVar()

        self.load_config()

        # Título Principal
        self.lbl_title = ctk.CTkLabel(
            self, text="Registro de Usuarios", 
            font=("Helvetica", 24, "bold"), text_color="#dde4e1"
        )
        self.lbl_title.pack(pady=(30, 5))
        
        self.lbl_subtitle = ctk.CTkLabel(
            self, text="Panel de Seguridad VTA Analytics", 
            font=("Helvetica", 14), text_color="#859490"
        )
        self.lbl_subtitle.pack(pady=(0, 20))

        # --- FRAME DE CONFIGURACIÓN ---
        self.config_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=15, border_width=1, border_color="#3c4a46")
        self.config_frame.pack(padx=30, pady=10, fill="x")

        self.lbl_config_title = ctk.CTkLabel(
            self.config_frame, text="Configuración (Supabase)", 
            font=("Helvetica", 12, "bold"), text_color="#57f1db"
        )
        self.lbl_config_title.pack(anchor="w", padx=20, pady=(15, 5))

        self.entry_url = ctk.CTkEntry(
            self.config_frame, textvariable=self.url_var, 
            placeholder_text="SUPABASE_URL", width=300, height=35,
            fg_color="#0F172A", border_color="#3c4a46", text_color="white", corner_radius=8
        )
        self.entry_url.pack(padx=20, pady=5)

        self.entry_key = ctk.CTkEntry(
            self.config_frame, textvariable=self.key_var, 
            placeholder_text="SUPABASE_KEY (anon)", width=300, height=35, show="*",
            fg_color="#0F172A", border_color="#3c4a46", text_color="white", corner_radius=8
        )
        self.entry_key.pack(padx=20, pady=(5, 20))

        # --- FRAME DE REGISTRO ---
        self.user_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=15, border_width=1, border_color="#3c4a46")
        self.user_frame.pack(padx=30, pady=10, fill="x")

        self.lbl_user_title = ctk.CTkLabel(
            self.user_frame, text="Nuevo Usuario", 
            font=("Helvetica", 12, "bold"), text_color="#57f1db"
        )
        self.lbl_user_title.pack(anchor="w", padx=20, pady=(15, 5))

        self.entry_email = ctk.CTkEntry(
            self.user_frame, textvariable=self.email_var, 
            placeholder_text="Correo Electrónico", width=300, height=35,
            fg_color="#0F172A", border_color="#3c4a46", text_color="white", corner_radius=8
        )
        self.entry_email.pack(padx=20, pady=5)

        self.entry_password = ctk.CTkEntry(
            self.user_frame, textvariable=self.password_var, 
            placeholder_text="Contraseña (mínimo 6 caracteres)", width=300, height=35, show="*",
            fg_color="#0F172A", border_color="#3c4a46", text_color="white", corner_radius=8
        )
        self.entry_password.pack(padx=20, pady=(5, 20))

        # --- BOTÓN DE REGISTRO ---
        self.btn_register = ctk.CTkButton(
            self, text="Crear Usuario", command=self.register_user,
            width=300, height=45, corner_radius=8,
            fg_color="#2DD4BF", hover_color="#3cddc7", text_color="#0F172A",
            font=("Helvetica", 14, "bold")
        )
        self.btn_register.pack(pady=20)

        # --- ETIQUETA DE ESTADO ---
        self.lbl_status = ctk.CTkLabel(
            self, text="", 
            font=("Helvetica", 14), text_color="white"
        )
        self.lbl_status.pack(pady=(0, 20))
        
        # Ocultar consola en Windows si es posible
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except Exception:
            pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.url_var.set(data.get("url", ""))
                    self.key_var.set(data.get("key", ""))
            except Exception:
                pass

    def save_config(self):
        data = {
            "url": self.url_var.get().strip(),
            "key": self.key_var.get().strip()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def show_message(self, message, is_error=False):
        color = "#ffb4ab" if is_error else "#57f1db"
        self.lbl_status.configure(text=message, text_color=color)

    def register_user(self):
        url = self.url_var.get().strip()
        key = self.key_var.get().strip()
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()

        if not url or not key:
            self.show_message("Error: Faltan las llaves de Supabase", is_error=True)
            return
        
        if not email or not password:
            self.show_message("Error: Ingresa correo y contraseña", is_error=True)
            return
        
        if len(password) < 6:
            self.show_message("Error: La contraseña debe tener al menos 6 caracteres", is_error=True)
            return

        # Guardar URL y Key para la próxima vez
        self.save_config()
        self.show_message("Conectando con la bóveda...", is_error=False)
        self.update() # Refrescar GUI

        try:
            supabase: Client = create_client(url, key)
            res = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            
            if hasattr(res, 'user') and res.user:
                self.show_message(f"¡Éxito! Usuario {email} creado.", is_error=False)
                # Limpiar campos de registro
                self.email_var.set("")
                self.password_var.set("")
            else:
                self.show_message("Error desconocido al crear el usuario.", is_error=True)
                
        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                self.show_message("Error: Este correo ya está registrado.", is_error=True)
            elif "invalid login credentials" in error_msg.lower():
                self.show_message("Error: Las llaves de Supabase son incorrectas.", is_error=True)
            else:
                self.show_message(f"Error: {error_msg[:40]}...", is_error=True)

if __name__ == "__main__":
    app = App()
    app.mainloop()
