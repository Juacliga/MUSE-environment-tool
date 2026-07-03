import customtkinter as ctk
from PIL import Image
import os

class Intro_Tab:
    def __init__(self, parent_tab, app_instance):
        self.tab = parent_tab
        self.app = app_instance
        self.setup_ui()

    def setup_ui(self):
        # main
        self.frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Tittle
        ctk.CTkLabel(self.frame, text="MUSE Environment Tool", font=("Arial", 32, "bold")).pack(pady=20)
        ctk.CTkLabel(self.frame, text="Grado en Ingeniería Aeroespacial - UPV", font=("Arial", 18)).pack(pady=5)
        
        # 
        ctk.CTkLabel(self.frame, text="Alumno: Juan Climent García", font=("Arial", 16, "bold")).pack(pady=30)
        
        # 
        ctk.CTkLabel(self.frame, text="Tutores:", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(self.frame, text="Miguel Ardid Ramirez\nJuan Angel Sans Tresserras", font=("Arial", 16)).pack(pady=5)

        # logos 
        if os.path.exists("logo_upv.png") and os.path.exists("logo_etsiadi.png") and os.path.exists("logo_etsiadi2.png"):
            img_upv = ctk.CTkImage(light_image=Image.open("logo_upv.png"), size=(300, 100))
            img_etsiadi = ctk.CTkImage(light_image=Image.open("logo_etsiadi.png"), size=(100, 100))
            img_etsiadi2 = ctk.CTkImage(light_image=Image.open("logo_etsiadi2.png"), size=(240, 80))
            
            logo_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
            logo_frame.pack(pady=50)
            
            ctk.CTkLabel(logo_frame, image=img_upv, text="").pack(side="left", padx=20)
            ctk.CTkLabel(logo_frame, image=img_etsiadi, text="").pack(side="left", padx=20)
            ctk.CTkLabel(logo_frame, image=img_etsiadi2, text="").pack(side="left", padx=20)