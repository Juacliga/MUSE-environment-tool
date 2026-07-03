import customtkinter as ctk
import matlab.engine
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import os
from tkinter import filedialog
import csv

class M4_Tab:
    def __init__(self, parent_tab, app_instance):
        self.tab = parent_tab
        self.app = app_instance
        self.spenvis_data = None  # MEMORY: Store the entire parsed .txt file here
        
        # State variables for data export
        self.current_vel = []
        self.current_d_mono = []
        self.current_d_whip = []
        self.current_m_mono = 0
        self.current_m_whip = 0
        self.current_t_yrs = []
        self.current_pnp = []
        
        self.setup_ui()

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.main_container.pack(pady=5, padx=20, fill="x")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(2, weight=1)

        # --- FRAME 1: Space Debris Environment ---
        self.env_frame = ctk.CTkFrame(self.main_container)
        self.env_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.env_frame, text="1. Space Debris Environment", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_vimp = self.create_input_row(self.env_frame, "Impact Velocity [km/s]:", "10.0", 1)
        self.e_theta = self.create_input_row(self.env_frame, "Impact Angle [deg]:", "0.0", 2)
        self.e_rhop = self.create_input_row(self.env_frame, "Particle Density [g/cm^3]:", "2.8", 3)
        self.e_flux = self.create_input_row(self.env_frame, "Flux [impacts/m^2/yr]:", "0.005", 4)

        self.btn_load_txt = ctk.CTkButton(self.env_frame, text="Import SPENVIS Data (.txt)", command=self.load_spenvis_txt, fg_color="#5c5c5c", hover_color="#404040")
        self.btn_load_txt.grid(row=5, column=0, columnspan=2, pady=(15, 5), padx=10, sticky="ew")

        self.lbl_file_status = ctk.CTkLabel(self.env_frame, text="Mode: Manual Input", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_file_status.grid(row=6, column=0, columnspan=2, pady=(0, 10))

        # --- FRAME 2: Shield Material Properties ---
        self.mat_frame = ctk.CTkFrame(self.main_container)
        self.mat_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.mat_frame, text="2. Shield Material (e.g. Al-6061)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_rhot = self.create_input_row(self.mat_frame, "Shield Density [g/cm^3]:", "2.7", 1)
        self.e_sigma = self.create_input_row(self.mat_frame, "Yield Strength [MPa]:", "275", 2)
        self.e_ct = self.create_input_row(self.mat_frame, "Speed of Sound [km/s]:", "5.1", 3)

        # --- FRAME 3: Spacecraft Geometry ---
        self.sc_frame = ctk.CTkFrame(self.main_container)
        self.sc_frame.grid(row=0, column=2, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.sc_frame, text="3. S/C Configuration", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_dp = self.create_input_row(self.sc_frame, "Design Particle Dia [cm]:", "1.0", 1)
        self.e_area = self.create_input_row(self.sc_frame, "Exposed Area [m^2]:", "12.0", 2)
        self.e_years = self.create_input_row(self.sc_frame, "Mission Years:", "15.0", 3)
        self.e_standoff = self.create_input_row(self.sc_frame, "Standoff Distance [cm]:", "10.0", 4)

        # TRACKER: Auto-update flux when the user types in "Particle Dia"
        self.e_dp.bind("<KeyRelease>", self.update_flux_from_memory)

        # --- Buttons & Status ---
        self.buttons_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.buttons_frame.pack(pady=10)

        self.btn_run = ctk.CTkButton(self.buttons_frame, text="Evaluate MMOD Survivability & Shielding", command=self.run_M4, font=ctk.CTkFont(weight="bold"))
        self.btn_run.grid(row=0, column=0, padx=10)

        self.btn_export = ctk.CTkButton(self.buttons_frame, text="Export Results CSV", command=self.export_csv, fg_color="#2e7d32", state="disabled")
        self.btn_export.grid(row=0, column=1, padx=10)

        # Dropdown menu to select specific plot or all plots
        self.view_var = ctk.StringVar(value="All plots")
        self.combo_expand = ctk.CTkOptionMenu(self.buttons_frame, variable=self.view_var, 
                                              values=["All plots", "1. Mass Requirements", "2. Ballistic Limit", "3. Probability of No Penetration"], 
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

    def load_spenvis_txt(self):
        filepath = filedialog.askopenfilename(
            title="Select SPENVIS MASTER file (e.g., spenvis_master_c_dia.txt)",
            filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        if not filepath:
            return

        try:
            parsed_data = []
            with open(filepath, 'r') as file:
                lines = file.readlines()
                
            in_data_block = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("'Total_flux'"):
                    in_data_block = True
                    continue
                elif line.startswith("'End of File'"):
                    break
                    
                if in_data_block:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            # Store in memory as: (Diameter in meters, Total Flux)
                            parsed_data.append((float(parts[0]), float(parts[-1])))
                        except ValueError:
                            pass 

            if not parsed_data:
                 raise ValueError("Could not extract valid data from the file.")

            # Store the extracted table in the tool's memory
            self.spenvis_data = parsed_data
            
            # Set a conservative default velocity
            self.e_vimp.delete(0, 'end')
            self.e_vimp.insert(0, "15.0")

            filename = os.path.basename(filepath)
            self.lbl_file_status.configure(text=f"Loaded: {filename} (Live Sync Active)", text_color="#00e676")
            self.lbl_status.configure(text="SPENVIS DB memorized. Flux will auto-update if Particle Dia changes.", text_color="#00e5ff")

            # Force the first automatic update
            self.update_flux_from_memory()

        except Exception as e:
            self.lbl_file_status.configure(text="Parse Error", text_color="red")
            self.lbl_status.configure(text=f"File Error: {str(e)}", text_color="red")

    def update_flux_from_memory(self, event=None):
        # If no file is loaded in memory, do nothing
        if not self.spenvis_data:
            return
        
        try:
            # Read the diameter currently typed by the user
            target_dp_cm = float(self.e_dp.get())
            target_dp_m = target_dp_cm / 100.0

            extracted_flux = None
            # Search memory for the corresponding flux
            for dp_m, flux in self.spenvis_data:
                if dp_m >= target_dp_m:
                    extracted_flux = flux
                    break

            if extracted_flux is not None:
                # Update the flux entry cell in real-time
                self.e_flux.delete(0, 'end')
                self.e_flux.insert(0, f"{extracted_flux:.4e}")
                
        except ValueError:
            # User is clearing the cell or typing invalid characters. Ignore.
            pass

    def run_M4(self):
        try:
            v_imp = float(self.e_vimp.get())
            theta = float(self.e_theta.get())
            rho_p = float(self.e_rhop.get())
            flux = float(self.e_flux.get())
            
            rho_t = float(self.e_rhot.get())
            sigma_y = float(self.e_sigma.get())
            c_t = float(self.e_ct.get())
            
            dp = float(self.e_dp.get())
            area = float(self.e_area.get())
            years = float(self.e_years.get())
            standoff = float(self.e_standoff.get())
            
            self.lbl_status.configure(text="Status: Starting MATLAB Engine...", text_color="orange")
            self.tab.update()

            if self.app.eng is None: 
                self.app.eng = matlab.engine.start_matlab()
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.app.eng.addpath(current_dir, nargout=0)
            
            self.lbl_status.configure(text="Status: Calculating Ballistic Limits...", text_color="yellow")
            self.tab.update()

            vel, d_mono, d_whip, m_mono, m_whip, t_yrs, pnp = self.app.eng.M4_mmod_shield(
                area, years, flux, v_imp, rho_p, standoff, rho_t, sigma_y, c_t, dp, theta, nargout=7
            )

            # Store states for export
            self.current_vel = list(vel[0])
            self.current_d_mono = list(d_mono[0])
            self.current_d_whip = list(d_whip[0])
            self.current_m_mono = m_mono
            self.current_m_whip = m_whip
            self.current_t_yrs = list(t_yrs[0])
            self.current_pnp = list(pnp[0])

            self.lbl_status.configure(text="Simulation Complete!", text_color="#00e676")
            self.btn_export.configure(state="normal")
            
            self.draw_plot(self.current_vel, self.current_d_mono, self.current_d_whip, m_mono, m_whip, self.current_t_yrs, self.current_pnp, v_imp, dp)
            
        except Exception as e:
            self.lbl_status.configure(text=f"Error: {e}", text_color="red")

    def draw_plot(self, vel, d_mono, d_whip, m_mono, m_whip, t_yrs, pnp, target_v, target_dp):
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
        bars = ax1.bar(['Monolithic Wall', 'Whipple Shield'], [m_mono, m_whip], color=['#ff3d00', '#00e676'], alpha=0.8)
        ax1.set_ylabel('Areal Mass Required [kg/m²]')
        ax1.set_title(f'Mass Req. for {target_dp}cm Particle')
        for bar in bars:
            yval = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, yval + (yval*0.02), f'{yval:.1f} kg/m²', ha='center', va='bottom', color='white', fontweight='bold')
        
        ax2.set_facecolor('#2b2b2b')
        ax2.plot(vel, d_mono, color='#ff3d00', linewidth=2, linestyle='--', label='Limit: Monolithic')
        ax2.plot(vel, d_whip, color='#00e676', linewidth=2, label='Limit: Whipple')
        ax2.axvline(x=target_v, color='yellow', linestyle=':', label=f'Design V ({target_v} km/s)')
        ax2.set_xlabel('Impact Velocity (km/s)')
        ax2.set_ylabel('Critical Particle Diameter (cm)')
        ax2.set_title('Ballistic Limit Envelope')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim([0.0, target_dp * 2.0]) 

        ax3.set_facecolor('#2b2b2b')
        ax3.plot(t_yrs, pnp, color='#00e5ff', linewidth=2)
        ax3.fill_between(t_yrs, 0.90, pnp, where=(np.array(pnp) < 0.90), color='#ff3d00', alpha=0.3)
        ax3.axhline(y=0.90, color='#ff3d00', linestyle='--', label='90% Target')
        ax3.set_xlabel('Mission Elapsed Time (Years)')
        ax3.set_ylabel('Probability of No Penetration')
        ax3.set_title('PNP - % no penetration')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim([0.80, 1.01])

        fig.tight_layout()
        
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

    def popout_plot(self):
        # Prevent execution if data is missing
        if not self.current_vel: 
            self.lbl_status.configure(text="Run simulation first.", text_color="orange")
            return

        selection = self.view_var.get()

        # New Tab
        popout_win = ctk.CTkToplevel(self.tab)
        popout_win.title(f"Full Screen: M4 - {selection}")
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
            
            # Retrieve specific user inputs needed for labels and lines
            target_v = float(self.e_vimp.get())
            target_dp = float(self.e_dp.get())
            
            if selection == "1. Mass Requirements":
                bars = ax.bar(['Monolithic Wall', 'Whipple Shield'], [self.current_m_mono, self.current_m_whip], color=['#ff3d00', '#00e676'], alpha=0.8)
                ax.set_ylabel('Areal Mass Required [kg/m²]')
                ax.set_title(f'Mass Req. for {target_dp}cm Particle')
                for bar in bars:
                    yval = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2, yval + (yval*0.02), f'{yval:.1f} kg/m²', ha='center', va='bottom', color='white', fontweight='bold')
                
            elif selection == "2. Ballistic Limit":
                ax.plot(self.current_vel, self.current_d_mono, color='#ff3d00', linewidth=2, linestyle='--', label='Limit: Monolithic')
                ax.plot(self.current_vel, self.current_d_whip, color='#00e676', linewidth=2, label='Limit: Whipple')
                ax.axvline(x=target_v, color='yellow', linestyle=':', label=f'Design V ({target_v} km/s)')
                ax.set_xlabel('Impact Velocity (km/s)')
                ax.set_ylabel('Critical Particle Diameter (cm)')
                ax.set_title('Ballistic Limit Envelope')
                ax.legend()
                ax.grid(True, alpha=0.3)
                ax.set_ylim([0.0, target_dp * 2.0]) 
                
            elif selection == "3. Probability of No Penetration":
                ax.plot(self.current_t_yrs, self.current_pnp, color='#00e5ff', linewidth=2)
                ax.fill_between(self.current_t_yrs, 0.90, self.current_pnp, where=(np.array(self.current_pnp) < 0.90), color='#ff3d00', alpha=0.3)
                ax.axhline(y=0.90, color='#ff3d00', linestyle='--', label='90% Target')
                ax.set_xlabel('Mission Elapsed Time (Years)')
                ax.set_ylabel('Probability of No Penetration')
                ax.set_title('PNP - % no penetration')
                ax.legend()
                ax.grid(True, alpha=0.3)
                ax.set_ylim([0.80, 1.01])

            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # toolbar
            toolbar = NavigationToolbar2Tk(canvas, frame)
            toolbar.update()
            toolbar.pack(side="bottom", fill="x")

    def export_csv(self):
        if not self.current_vel: return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filepath:
            try:
                v_imp = float(self.e_vimp.get())
                dp = float(self.e_dp.get())
                
                with open(filepath, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["--- MMOD SHIELDING SIMULATION RESULTS ---"])
                    writer.writerow(["Design Particle Diameter [cm]", dp])
                    writer.writerow(["Design Impact Velocity [km/s]", v_imp])
                    writer.writerow(["Optimized Monolithic Mass [kg/m2]", self.current_m_mono])
                    writer.writerow(["Optimized Whipple Shield Mass [kg/m2]", self.current_m_whip])
                    writer.writerow([])
                    writer.writerow(["Velocity [km/s]", "Mono Critical Dia [cm]", "Whipple Critical Dia [cm]", "Time [Years]", "Poisson PNP"])
                    for v, dm, dw, yr, p in zip(self.current_vel, self.current_d_mono, self.current_d_whip, self.current_t_yrs, self.current_pnp):
                        writer.writerow([v, dm, dw, yr, p])
                self.lbl_status.configure(text="Status: Results successfully exported!", text_color="#00e676")
            except Exception as e:
                self.lbl_status.configure(text=f"Error exporting data: {str(e)}", text_color="red")