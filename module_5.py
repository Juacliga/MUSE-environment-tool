import customtkinter as ctk
import matlab.engine
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import os
from tkinter import filedialog
import csv

class M5_Tab:
    def __init__(self, parent_tab, app_instance):
        self.tab = parent_tab
        self.app = app_instance
        
        # State variables for export
        self.current_t_yrs = []
        self.current_flu = []
        self.current_th_rem = []
        self.current_alpha = []
        self.current_temp = []
        self.current_status = ""
        
        self.setup_ui()

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.main_container.pack(pady=5, padx=20, fill="x")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(2, weight=1)

        # --- FRAME 1: LEO Environment ---
        self.env_frame = ctk.CTkFrame(self.main_container)
        self.env_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.env_frame, text="1. LEO ATOX Environment", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_alt = self.create_input_row(self.env_frame, "Orbital Altitude [km]:", "400", 1)
        self.e_f107 = self.create_input_row(self.env_frame, "Solar F10.7 Index:", "150", 2)
        self.e_years = self.create_input_row(self.env_frame, "Mission Duration [years]:", "10", 3)
        
        info_text = ("F10.7 ~70: Solar Min | F10.7 ~200: Solar Max")
        ctk.CTkLabel(self.env_frame, text=info_text, text_color="#aaaaaa", justify="left").grid(row=4, column=0, columnspan=2, pady=10)

        # --- FRAME 2: Material Properties ---
        self.mat_frame = ctk.CTkFrame(self.main_container)
        self.mat_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.mat_frame, text="2. Protective Surface Layer", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.mat_var = ctk.StringVar(value="Kapton (3.0e-24)")
        ctk.CTkLabel(self.mat_frame, text="Polymer Type:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        mat_menu = ctk.CTkOptionMenu(self.mat_frame, variable=self.mat_var, values=["Kapton (3.0e-24)", "Mylar (3.4e-24)", "Teflon/FEP (0.05e-24)"])
        mat_menu.grid(row=1, column=1, padx=10, pady=5)
        
        self.e_thick = self.create_input_row(self.mat_frame, "Initial Thickness [mm]:", "0.1", 2)

        # --- FRAME 3: Thermal Baseline ---
        self.sc_frame = ctk.CTkFrame(self.main_container)
        self.sc_frame.grid(row=0, column=2, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.sc_frame, text="3. Thermo-Optical Props", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_alpha = self.create_input_row(self.sc_frame, "Initial Absorptivity (α):", "0.35", 1)
        self.e_eps = self.create_input_row(self.sc_frame, "Emissivity (ε):", "0.80", 2)
        self.e_sub = self.create_input_row(self.sc_frame, "Substrate α (If eroded):", "0.90", 3)
        
        # --- Buttons & Status ---
        self.buttons_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.buttons_frame.pack(pady=10)

        self.btn_run = ctk.CTkButton(self.buttons_frame, text="Simulate Chemical Erosion", command=self.run_M5, font=ctk.CTkFont(weight="bold"))
        self.btn_run.grid(row=0, column=0, padx=10)

        self.btn_export = ctk.CTkButton(self.buttons_frame, text="Export Results CSV", command=self.export_csv, fg_color="#2e7d32", state="disabled")
        self.btn_export.grid(row=0, column=1, padx=10)

        # Dropdown menu to select specific plot or all plots
        self.view_var = ctk.StringVar(value="All plots")
        self.combo_expand = ctk.CTkOptionMenu(self.buttons_frame, variable=self.view_var, 
                                              values=["All plots", "1. Cumulative Atomic Oxygen Hit", "2. Structural Erosion (Mass Loss)", "3. Thermo-Optical Degradation"], 
                                              fg_color="#5c5c5c")
        self.combo_expand.grid(row=0, column=2, padx=10)

        self.btn_expand = ctk.CTkButton(self.buttons_frame, text="Full Screen Figure", 
                                        command=self.popout_plot, fg_color="#5c5c5c")
        self.btn_expand.grid(row=0, column=3, padx=10)

        self.lbl_status = ctk.CTkLabel(self.tab, text="Status: Ready", text_color="gray")
        self.lbl_status.pack(pady=0)

        self.plot_frame = ctk.CTkFrame(self.tab)
        self.plot_frame.pack(fill="both", expand=True, padx=20, pady=5)
        self.canvas = None
        self.toolbar = None

    def create_input_row(self, parent, label_text, default_val, row_idx):
        ctk.CTkLabel(parent, text=label_text).grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        entry = ctk.CTkEntry(parent, width=70)
        entry.insert(0, default_val)
        entry.grid(row=row_idx, column=1, padx=10, pady=5)
        return entry

    def run_M5(self):
        try:
            alt = float(self.e_alt.get())
            f107 = float(self.e_f107.get())
            years = float(self.e_years.get())
            mat_str = self.mat_var.get()
            ey_val = float(mat_str.split('(')[1].split('e')[0])
            thick = float(self.e_thick.get())
            alpha_init = float(self.e_alpha.get())
            eps_ir = float(self.e_eps.get())
            alpha_sub = float(self.e_sub.get())
            
            if self.app.eng is None: self.app.eng = matlab.engine.start_matlab()
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.app.eng.addpath(current_dir, nargout=0)
            
            self.lbl_status.configure(text="Status: Integrating Fluence & Erosion...", text_color="yellow")
            self.tab.update()

            t_yrs, flu, th_rem, alpha, temp, flag = self.app.eng.M5_atox_degradation(
                alt, f107, years, ey_val, thick, alpha_init, eps_ir, alpha_sub, nargout=6
            )

            self.current_t_yrs = list(t_yrs[0])
            self.current_flu = list(flu[0])
            self.current_th_rem = list(th_rem[0])
            self.current_alpha = list(alpha[0])
            self.current_temp = list(temp[0])

            color = "#00e676" if flag == 1 else "#ff3d00"
            status = "PASS (Layer Survived)" if flag == 1 else "FAIL (Layer Eroded Away!)"
            self.current_status = status
            
            self.lbl_status.configure(text=f"Status: [{status}]", text_color=color)
            self.btn_export.configure(state="normal")
            self.draw_plot(self.current_t_yrs, self.current_flu, self.current_th_rem, self.current_alpha, self.current_temp, thick)
            
        except Exception as e:
            self.lbl_status.configure(text=f"Error: {e}", text_color="red")

    def draw_plot(self, t_yrs, flu, th_rem, alpha, temp, th_init):
        if self.canvas: self.canvas.get_tk_widget().destroy()
        if hasattr(self, 'toolbar') and self.toolbar: self.toolbar.destroy()

        plt.close('all')

        plt.rcParams.update({
            'font.size': 14,           
            'axes.titlesize': 15,     
            'axes.labelsize': 12,      
            'legend.fontsize': 13,     
            'xtick.labelsize': 11,    
            'ytick.labelsize': 11      
        })

        plt.style.use('dark_background')
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 5), dpi=100)
        fig.patch.set_facecolor('#2b2b2b')

        ax1.set_facecolor('#2b2b2b')
        ax1.plot(t_yrs, flu, color='#b388ff', linewidth=2)
        ax1.set_xlabel('Mission Time (Years)')
        ax1.set_ylabel('ATOX Fluence (atoms/cm²)')
        ax1.set_title('1. Cumulative Atomic Oxygen Hit')
        ax1.grid(True, alpha=0.3)
        ax1.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
        
        ax2.set_facecolor('#2b2b2b')
        ax2.plot(t_yrs, th_rem, color='#00e5ff', linewidth=2)
        ax2.fill_between(t_yrs, 0, th_rem, color='#00e5ff', alpha=0.2)
        if min(th_rem) <= 0:
            ax2.axhline(y=0, color='#ff3d00', linestyle='--', linewidth=2, label="Breach / Failure")
            ax2.legend()
        ax2.set_xlabel('Mission Time (Years)')
        ax2.set_ylabel('Remaining Thickness (mm)')
        ax2.set_title('2. Structural Erosion (Mass Loss)')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim([-0.01, th_init * 1.1])

        ax3.set_facecolor('#2b2b2b')
        ax3.plot(t_yrs, alpha, color='#ff9100', linewidth=2, label=r'Absorptivity ($\alpha$)')
        ax3.set_xlabel('Mission Time (Years)')
        ax3.set_ylabel('Solar Absorptivity', color='#ff9100')
        ax3.tick_params(axis='y', labelcolor='#ff9100')
        ax3.set_ylim([0.0, 1.0])
        
        ax3b = ax3.twinx()
        ax3b.plot(t_yrs, temp, color='#ff3d00', linewidth=2, linestyle=':', label='Max Surf Temp')
        ax3b.set_ylabel('Temperature (°C)', color='#ff3d00')
        ax3b.tick_params(axis='y', labelcolor='#ff3d00')
        ax3.set_title('3. Thermo-Optical Degradation')
        ax3.grid(True, alpha=0.3)

        fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

    def popout_plot(self):
        # Prevent execution if data is missing
        if not self.current_t_yrs: 
            self.lbl_status.configure(text="Run simulation first.", text_color="orange")
            return

        selection = self.view_var.get()

        # New Tab
        popout_win = ctk.CTkToplevel(self.tab)
        popout_win.title(f"Full Screen: M5 - {selection}")
        popout_win.geometry("1920x1080")
        
        # New frame
        frame = ctk.CTkFrame(popout_win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        if selection == "All plots":
            if self.canvas:
                canvas = FigureCanvasTkAgg(self.canvas.figure, master=frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                
                # toolbar
                toolbar = NavigationToolbar2Tk(canvas, frame)
                toolbar.update()
                toolbar.pack(side="bottom", fill="x")
            else:
                ctk.CTkLabel(frame, text="Run first.").pack(pady=20)      
        else:
            # Generate specific single plot
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
            fig.patch.set_facecolor('#2b2b2b')
            ax.set_facecolor('#2b2b2b')
            
            # Retrieve specific user inputs needed for labels and limits
            th_init = float(self.e_thick.get())
            
            if selection == "1. Cumulative Atomic Oxygen Hit":
                ax.plot(self.current_t_yrs, self.current_flu, color='#b388ff', linewidth=2)
                ax.set_xlabel('Mission Time (Years)')
                ax.set_ylabel('ATOX Fluence (atoms/cm²)')
                ax.set_title('1. Cumulative Atomic Oxygen Hit')
                ax.grid(True, alpha=0.3)
                ax.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
                
            elif selection == "2. Structural Erosion (Mass Loss)":
                ax.plot(self.current_t_yrs, self.current_th_rem, color='#00e5ff', linewidth=2)
                ax.fill_between(self.current_t_yrs, 0, self.current_th_rem, color='#00e5ff', alpha=0.2)
                if min(self.current_th_rem) <= 0:
                    ax.axhline(y=0, color='#ff3d00', linestyle='--', linewidth=2, label="Breach / Failure")
                    ax.legend()
                ax.set_xlabel('Mission Time (Years)')
                ax.set_ylabel('Remaining Thickness (mm)')
                ax.set_title('2. Structural Erosion (Mass Loss)')
                ax.grid(True, alpha=0.3)
                ax.set_ylim([-0.01, th_init * 1.1])
                
            elif selection == "3. Thermo-Optical Degradation":
                ax.plot(self.current_t_yrs, self.current_alpha, color='#ff9100', linewidth=2, label=r'Absorptivity ($\alpha$)')
                ax.set_xlabel('Mission Time (Years)')
                ax.set_ylabel('Solar Absorptivity', color='#ff9100')
                ax.tick_params(axis='y', labelcolor='#ff9100')
                ax.set_ylim([0.0, 1.0])
                
                ax3b = ax.twinx()
                ax3b.plot(self.current_t_yrs, self.current_temp, color='#ff3d00', linewidth=2, linestyle=':', label='Max Surf Temp')
                ax3b.set_ylabel('Temperature (°C)', color='#ff3d00')
                ax3b.tick_params(axis='y', labelcolor='#ff3d00')
                ax.set_title('3. Thermo-Optical Degradation')
                ax.grid(True, alpha=0.3)

            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # toolbar
            toolbar = NavigationToolbar2Tk(canvas, frame)
            toolbar.update()
            toolbar.pack(side="bottom", fill="x")

    def export_csv(self):
        if not self.current_t_yrs: return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filepath:
            try:
                # Fetch inputs for the header
                alt = self.e_alt.get()
                f107 = self.e_f107.get()
                mat_str = self.mat_var.get()
                th_init = self.e_thick.get()
                alpha_init = self.e_alpha.get()
                eps = self.e_eps.get()
                
                with open(filepath, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["--- ATOX DEGRADATION & THERMAL RECESSION SIMULATION ---"])
                    writer.writerow(["Final Status", self.current_status])
                    writer.writerow([])
                    writer.writerow(["--- SIMULATION PARAMETERS ---"])
                    writer.writerow(["Altitude [km]", alt])
                    writer.writerow(["F10.7 Solar Index", f107])
                    writer.writerow(["Material Type", mat_str])
                    writer.writerow(["Initial Thickness [mm]", th_init])
                    writer.writerow(["Initial Absorptivity", alpha_init])
                    writer.writerow(["Emissivity", eps])
                    writer.writerow([])
                    writer.writerow(["--- TELEMETRY DATA ---"])
                    writer.writerow(["Timeline [Years]", "Accumulated Fluence [atoms/cm2]", "Remaining Thickness [mm]", "Degraded Absorptivity", "Equilibrium Temperature [C]"])
                    for yr, fl, th, al, tm in zip(self.current_t_yrs, self.current_flu, self.current_th_rem, self.current_alpha, self.current_temp):
                        writer.writerow([yr, fl, th, al, tm])
                self.lbl_status.configure(text="Status: Telemetry successfully exported!", text_color="#00e676")
            except Exception as e:
                self.lbl_status.configure(text=f"Error exporting data: {str(e)}", text_color="red")