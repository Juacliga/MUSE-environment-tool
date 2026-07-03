import customtkinter as ctk
import matlab.engine
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
from tkinter import filedialog
import csv

class M3_Tab:
    def __init__(self, parent_tab, app_instance):
        self.tab = parent_tab
        self.app = app_instance
        
        # State variables for data export
        self.current_t_hrs = []
        self.current_temp = []
        self.current_v_surf = []
        self.current_e_int = []
        self.current_breakdown = 1.0e7
        self.current_status = ""
        
        self.setup_ui()

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.main_container.pack(pady=5, padx=20, fill="x")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)

        # --- FRAME 1: Orbital Events (Eclipse & Substorm) ---
        self.env_frame = ctk.CTkFrame(self.main_container)
        self.env_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.env_frame, text="1. Orbital Events (Eclipse & Substorm)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_ecl_start = self.create_input_row(self.env_frame, "Eclipse Start Time [hr]:", "11.0", 1)
        self.e_ecl_dur = self.create_input_row(self.env_frame, "Eclipse Duration [min]:", "120", 2)
        
        ctk.CTkLabel(self.env_frame, text="--- Substorm Injection ---", text_color="gray").grid(row=3, column=0, columnspan=2, pady=5)
        self.e_sub_start = self.create_input_row(self.env_frame, "Substorm Start Time [hr]:", "11.5", 4)
        self.e_sub_dur = self.create_input_row(self.env_frame, "Substorm Duration [min]:", "240", 5)
        self.e_ne = self.create_input_row(self.env_frame, "Peak Plasma Density [cm^-3]:", "1.5", 6)
        self.e_te = self.create_input_row(self.env_frame, "Peak Plasma Temp [keV]:", "12.0", 7)
        self.e_jr = self.create_input_row(self.env_frame, "Deep Internal Flux [pA/cm^2]:", "3.5", 8)

        # --- FRAME 2: S/C & Material Properties ---
        self.sc_frame = ctk.CTkFrame(self.main_container)
        self.sc_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.sc_frame, text="2. S/C & Material Properties", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_mass = self.create_input_row(self.sc_frame, "Thermal Mass [kg]:", "15.0", 1)
        self.e_cp = self.create_input_row(self.sc_frame, "Specific Heat (cp) [J/kgK]:", "900", 2)
        self.e_area = self.create_input_row(self.sc_frame, "Radiating Area [m^2]:", "4.0", 3)
        self.e_photo = self.create_input_row(self.sc_frame, "Photoemission Flux [uA/m^2]:", "20.0", 4)
        self.e_sey = self.create_input_row(self.sc_frame, "Secondary Yield (SEY) [0-1]:", "0.4", 5)
        
        ctk.CTkLabel(self.sc_frame, text="--- Dielectric (Kapton/FR4) ---", text_color="gray").grid(row=6, column=0, columnspan=2, pady=5)
        self.e_sigma = self.create_input_row(self.sc_frame, "Base Conductivity @25°C [S/m]:", "1e-14", 7)
        self.e_act = self.create_input_row(self.sc_frame, "Activation Energy [eV]:", "0.55", 8)
        self.e_eps = self.create_input_row(self.sc_frame, "Relative Permittivity (Eps_r):", "3.0", 9)
        self.e_break = self.create_input_row(self.sc_frame, "Breakdown Field [V/m]:", "1.0e7", 10)

        # --- Buttons & Status ---
        self.buttons_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.buttons_frame.pack(pady=10)

        self.btn_run = ctk.CTkButton(self.buttons_frame, text="Run Numerical Integrations (NASA-HDBK-4002B)", command=self.run_M3, font=ctk.CTkFont(weight="bold"))
        self.btn_run.grid(row=0, column=0, padx=10)

        self.btn_export = ctk.CTkButton(self.buttons_frame, text="Export Results CSV", command=self.export_csv, fg_color="#2e7d32", state="disabled")
        self.btn_export.grid(row=0, column=1, padx=10)

        # Dropdown menu to select specific plot or all plots
        self.view_var = ctk.StringVar(value="All plots")
        self.combo_expand = ctk.CTkOptionMenu(self.buttons_frame, variable=self.view_var, 
                                              values=["All plots", "1. Thermal Analysis", "2. Surface Voltage", "3. Electric Field"], 
                                              fg_color="#5c5c5c")
        self.combo_expand.grid(row=0, column=2, padx=10)

        self.btn_expand = ctk.CTkButton(self.buttons_frame, text="Full Screen Figure", 
                                        command=self.popout_plot, fg_color="#5c5c5c")
        self.btn_expand.grid(row=0, column=3, padx=10)

        self.lbl_status = ctk.CTkLabel(self.tab, text="Status: Ready", text_color="gray")
        self.lbl_status.pack(pady=0)
        self.lbl_results = ctk.CTkLabel(self.tab, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_results.pack(pady=5)

        self.plot_frame = ctk.CTkFrame(self.tab)
        self.plot_frame.pack(fill="both", expand=True, padx=20, pady=5)
        self.canvas = None
        self.toolbar = None

    def create_input_row(self, parent, label_text, default_val, row_idx):
        ctk.CTkLabel(parent, text=label_text).grid(row=row_idx, column=0, padx=15, pady=2, sticky="w")
        entry = ctk.CTkEntry(parent, height=22)
        entry.insert(0, default_val)
        entry.grid(row=row_idx, column=1, padx=15, pady=2)
        return entry

    def run_M3(self):
        try:
            params = [
                float(self.e_ecl_start.get()), float(self.e_ecl_dur.get()),
                float(self.e_sub_start.get()), float(self.e_sub_dur.get()),
                float(self.e_ne.get()), float(self.e_te.get()), float(self.e_jr.get()),
                float(self.e_mass.get()), float(self.e_cp.get()), float(self.e_area.get()), 
                float(self.e_photo.get()), float(self.e_sey.get()),
                float(self.e_sigma.get()), float(self.e_act.get()), 
                float(self.e_eps.get()), float(self.e_break.get())
            ]
            
            self.lbl_status.configure(text="Status: Starting MATLAB Engine...", text_color="orange")
            self.tab.update()

            if self.app.eng is None: 
                self.app.eng = matlab.engine.start_matlab()
            
            self.lbl_status.configure(text="Status: Solving Coupled ODEs...", text_color="yellow")
            self.tab.update()

            t_hrs, temp, v_surf, e_int, flag = self.app.eng.M3_plasma_charging(*params, nargout=5)
            t_hrs, temp, v_surf, e_int = list(t_hrs[0]), list(temp[0]), list(v_surf[0]), list(e_int[0])

            max_e = max(e_int)
            min_temp = min(temp)
            min_v = min(v_surf)
            
            color = "#00e676" if flag == 0 else "#ff3d00"
            status = "PASS" if flag == 0 else "FAIL (Dielectric Rupture!)"
            
            res_str = (f"Status: [{status}]  |  Min Temp: {min_temp:.1f} °C  |  "
                       f"Max Surface Voltage: {min_v:.0f} V  |  Max Internal E-Field: {max_e:.2e} V/m")
                       
            self.lbl_results.configure(text=res_str, text_color=color)
            self.lbl_status.configure(text="Simulation Complete!", text_color="gray")
            
            # Save State variables
            self.current_t_hrs = t_hrs
            self.current_temp = temp
            self.current_v_surf = v_surf
            self.current_e_int = e_int
            self.current_breakdown = params[-1]
            self.current_status = status
            
            self.btn_export.configure(state="normal")
            self.draw_plot(t_hrs, temp, v_surf, e_int, params[-1], params[0], params[1], params[2], params[3])
            
        except Exception as e:
            self.lbl_status.configure(text=f"Error: {e}", text_color="red")

    def draw_plot(self, t_hrs, temp, v_surf, e_int, breakdown, ecl_start, ecl_dur, sub_start, sub_dur):
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
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 9), dpi=100, sharex=True)
        fig.patch.set_facecolor('#2b2b2b')

        ecl_end = ecl_start + (ecl_dur / 60.0)
        sub_end = sub_start + (sub_dur / 60.0)

        ax1.set_facecolor('#2b2b2b')
        ax1.axvspan(ecl_start, ecl_end, color='#ffffff', alpha=0.15, label="Eclipse")
        ax1.plot(t_hrs, temp, color='#ff9100', linewidth=2, label="S/C Bulk Temperature")
        ax1.set_ylabel('Temperature (°C)', color='#ff9100')
        ax1.tick_params(axis='y', labelcolor='#ff9100')
        ax1.set_title('1. Thermal Analysis (Eclipse Cooling)')
        ax1.set_xlabel('Mission Time (hours)')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="upper right", fontsize=9)

        ax2.set_facecolor('#2b2b2b')
        ax2.axvspan(ecl_start, ecl_end, color='#ffffff', alpha=0.15)
        ax2.axvspan(sub_start, sub_end, color='#ff3d00', alpha=0.15, label="Substorm Plasma Injection")
        ax2.plot(t_hrs, v_surf, color='#00e5ff', linewidth=2, label="Absolute Surface Potential")
        ax2.set_ylabel('Surface Voltage (V)', color='#00e5ff')
        ax2.tick_params(axis='y', labelcolor='#00e5ff')
        ax2.set_title('2. Surface Charging (Non-Linear Current Balance)')
        ax2.set_xlabel('Mission Time (hours)')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc="lower right", fontsize=9)

        ax3.set_facecolor('#2b2b2b')
        ax3.axvspan(ecl_start, ecl_end, color='#ffffff', alpha=0.15)
        ax3.axvspan(sub_start, sub_end, color='#ff3d00', alpha=0.15)
        ax3.plot(t_hrs, e_int, color='#b388ff', linewidth=2, label="Internal Electric Field")
        ax3.axhline(y=breakdown, color='#ff3d00', linestyle='--', linewidth=2.5, label="Dielectric Breakdown Limit")
        ax3.fill_between(t_hrs, breakdown, e_int, where=(np.array(e_int) > breakdown), color='#ff3d00', alpha=0.3)
        ax3.set_ylabel('Electric Field (V/m)', color='#b388ff')
        ax3.tick_params(axis='y', labelcolor='#b388ff')
        ax3.set_title('3. Deep Dielectric Charging (Temperature-Coupled Conductivity)')
        ax3.set_xlabel('Mission Time (Hours)')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc="upper left", fontsize=9)
        
        ax1.set_xlim([0, 24])
        fig.tight_layout(h_pad=4.0)
        
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

    def popout_plot(self):
        # Prevent execution if data is missing
        if not self.current_t_hrs: 
            self.lbl_status.configure(text="Run simulation first.", text_color="orange")
            return

        selection = self.view_var.get()

        # New Tab
        popout_win = ctk.CTkToplevel(self.tab)
        popout_win.title(f"Full Screen: M3 - {selection}")
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
            
            # Retrieve orbital event parameters
            ecl_start = float(self.e_ecl_start.get())
            ecl_dur = float(self.e_ecl_dur.get())
            sub_start = float(self.e_sub_start.get())
            sub_dur = float(self.e_sub_dur.get())
            ecl_end = ecl_start + (ecl_dur / 60.0)
            sub_end = sub_start + (sub_dur / 60.0)
            
            if selection == "1. Thermal Analysis":
                ax.axvspan(ecl_start, ecl_end, color='#ffffff', alpha=0.15, label="Eclipse")
                ax.plot(self.current_t_hrs, self.current_temp, color='#ff9100', linewidth=2.5, label="S/C Bulk Temperature")
                ax.set_ylabel('Temperature (°C)', color='#ff9100')
                ax.set_title('1. Thermal Analysis (Eclipse Cooling)')
                
            elif selection == "2. Surface Voltage":
                ax.axvspan(ecl_start, ecl_end, color='#ffffff', alpha=0.15)
                ax.axvspan(sub_start, sub_end, color='#ff3d00', alpha=0.15, label="Substorm Plasma Injection")
                ax.plot(self.current_t_hrs, self.current_v_surf, color='#00e5ff', linewidth=2.5, label="Absolute Surface Potential")
                ax.set_ylabel('Surface Voltage (V)', color='#00e5ff')
                ax.set_title('2. Surface Charging (Non-Linear Current Balance)')
                
            elif selection == "3. Electric Field":
                breakdown = self.current_breakdown
                ax.axvspan(ecl_start, ecl_end, color='#ffffff', alpha=0.15)
                ax.axvspan(sub_start, sub_end, color='#ff3d00', alpha=0.15)
                ax.plot(self.current_t_hrs, self.current_e_int, color='#b388ff', linewidth=2.5, label="Internal Electric Field")
                ax.axhline(y=breakdown, color='#ff3d00', linestyle='--', linewidth=3, label="Dielectric Breakdown Limit")
                ax.fill_between(self.current_t_hrs, breakdown, self.current_e_int, where=(np.array(self.current_e_int) > breakdown), color='#ff3d00', alpha=0.3)
                ax.set_ylabel('Electric Field (V/m)', color='#b388ff')
                ax.set_title('3. Deep Dielectric Charging (Temperature-Coupled Conductivity)')

            ax.set_xlabel('Mission Time (hours)')
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best", fontsize=12)
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # toolbar
            toolbar = NavigationToolbar2Tk(canvas, frame)
            toolbar.update()
            toolbar.pack(side="bottom", fill="x")

    def export_csv(self):
        if not self.current_t_hrs: return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filepath:
            try:
                # extract inputs
                ecl_start = float(self.e_ecl_start.get())
                ecl_dur = float(self.e_ecl_dur.get())
                sub_start = float(self.e_sub_start.get())
                sub_dur = float(self.e_sub_dur.get())
                
                with open(filepath, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["--- ESD PLASMIC SIMULATION RESULTS ---"])
                    writer.writerow(["Global Status", self.current_status])
                    writer.writerow(["Dielectric Breakdown Field [V/m]", self.current_breakdown])
                    writer.writerow(["Eclipse Start Time [Hours]", ecl_start])
                    writer.writerow(["Eclipse Duration [Minutes]", ecl_dur])
                    writer.writerow(["Substorm Start Time [Hours]", sub_start])
                    writer.writerow(["Substorm Duration [Minutes]", sub_dur])
                    writer.writerow([])
                    writer.writerow(["Time [Hours]", "Spacecraft Temperature [C]", "Surface Voltage [V]", "Internal Electric Field [V/m]"])
                    for th, tmp, vs, ei in zip(self.current_t_hrs, self.current_temp, self.current_v_surf, self.current_e_int):
                        writer.writerow([th, tmp, vs, ei])
                self.lbl_status.configure(text="Status: Results successfully exported!", text_color="#00e676")
            except Exception as e:
                self.lbl_status.configure(text=f"Error exporting data: {str(e)}", text_color="red")