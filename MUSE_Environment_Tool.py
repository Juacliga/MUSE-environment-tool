import customtkinter as ctk

# Import modules
from intro_tab import Intro_Tab
from module_1 import M1_Tab
from module_2 import M2_Tab
from module_3 import M3_Tab
from module_4 import M4_Tab
from module_5 import M5_Tab

# Global config
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MUSEEnvironmentTool(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MUSE Environment Tool - Master in Space Engineering")
        self.geometry("1100x950")
        
        # MATLAB engine global variable shared between tabs
        self.eng = None 

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        tab_intro = self.tabview.add("Ini")
        tab1 = self.tabview.add("1: Space Weather (LEO)")
        tab2 = self.tabview.add("2: Radiation (MEO/GEO)")
        tab3 = self.tabview.add("3: Plasma & Thermal (GEO)")
        tab4 = self.tabview.add("4: Space Debris (MMOD)")
        tab5 = self.tabview.add("5: ATOX Degradation (LEO)")


        # Initialize modules
        self.intro_logic = Intro_Tab(tab_intro, self)
        self.M1_logic = M1_Tab(tab1, self)
        self.M2_logic = M2_Tab(tab2, self)
        self.M3_logic = M3_Tab(tab3, self)
        self.M4_logic = M4_Tab(tab4, self)
        self.M5_logic = M5_Tab(tab5, self)

if __name__ == "__main__":
    app = MUSEEnvironmentTool()
    app.mainloop()