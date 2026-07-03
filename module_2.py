import customtkinter as ctk
import matlab.engine
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import csv

class M2_Tab:
    def __init__(self, parent_tab, app_instance):
        self.tab = parent_tab
        self.app = app_instance
        
        self.depth_tid, self.dose_tid = [], []
        self.depth_eq, self.flu_eq = [], []
        
        self.res_dose = 0
        self.res_margin_tid = 0
        self.res_min_shield = 0
        self.res_flu = 0
        self.res_margin_flu = 0
        self.res_min_cover = 0
        self.status_tid = ""
        self.status_flu = ""
        self.current_deriv = []
        self.rdm_val = 2.0
        
        self.setup_ui()

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.main_container.pack(pady=5, padx=20, fill="x")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(2, weight=1)

        # --- FRAME 1: Data Import ---
        self.file_frame = ctk.CTkFrame(self.main_container)
        self.file_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.file_frame, text="1. Clean Data Import", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        instruction_text = "Use 2-column TXT/CSV files:\nCol 1: Depth [mm]\nCol 2: Radiation Value"
        ctk.CTkLabel(self.file_frame, text=instruction_text, text_color="#aaaaaa", justify="center").pack(pady=5)

        self.btn_load_tid = ctk.CTkButton(self.file_frame, text="Load TID Data (.txt)", command=lambda: self.load_file("TID"))
        self.btn_load_tid.pack(pady=5)
        self.lbl_tid = ctk.CTkLabel(self.file_frame, text="No TID data loaded.", text_color="gray")
        self.lbl_tid.pack(pady=2)

        self.btn_load_eq = ctk.CTkButton(self.file_frame, text="Load EQFLUX Data (.txt)", command=lambda: self.load_file("EQFLUX"))
        self.btn_load_eq.pack(pady=5)
        self.lbl_eq = ctk.CTkLabel(self.file_frame, text="No EQFLUX data loaded.", text_color="gray")
        self.lbl_eq.pack(pady=2)

        # --- FRAME 2: Avionics Parameters ---
        self.tid_frame = ctk.CTkFrame(self.main_container)
        self.tid_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.tid_frame, text="2. Avionics (TID)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_rdm = self.create_input_row(self.tid_frame, "Radiation Design Margin (RDM):", "2.0", 1)
        self.e_shield = self.create_input_row(self.tid_frame, "Target Al Shielding [mm]:", "2.0", 2)
        self.e_limit_tid = self.create_input_row(self.tid_frame, "Component Limit [krad]:", "50", 3)

        # --- FRAME 3: Solar Panels Parameters ---
        self.dd_frame = ctk.CTkFrame(self.main_container)
        self.dd_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.dd_frame, text="3. Solar Panels (DD)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.e_cover = self.create_input_row(self.dd_frame, "Coverglass Thickness [mm]:", "0.15", 1)
        self.e_limit_flu = self.create_input_row(self.dd_frame, "Cell 1-MeV Limit [e-/cm²]:", "1e15", 2)

        # --- Buttons & Status ---
        self.buttons_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.buttons_frame.pack(pady=10)

        self.btn_run = ctk.CTkButton(self.buttons_frame, text="Evaluate Integrated Radiation Risk", command=self.run_M2, font=ctk.CTkFont(weight="bold"))
        self.btn_run.grid(row=0, column=0, padx=10)

        self.btn_export = ctk.CTkButton(self.buttons_frame, text="Export Results CSV", command=self.export_csv, fg_color="#2e7d32", state="disabled")
        self.btn_export.grid(row=0, column=1, padx=10)

        # Dropdown menu to select specific plot or all plots
        self.view_var = ctk.StringVar(value="All plots")
        self.combo_expand = ctk.CTkOptionMenu(self.buttons_frame, variable=self.view_var, 
                                              values=["All plots", "1. Attenuation Physics", "2. Avionics Survivability", "3. Solar Panel Survivability"], 
                                              fg_color="#5c5c5c")
        self.combo_expand.grid(row=0, column=2, padx=10)

        self.btn_expand = ctk.CTkButton(self.buttons_frame, text="Full Screen Figure", 
                                        command=self.popout_plot, fg_color="#5c5c5c")
        self.btn_expand.grid(row=0, column=3, padx=10)

        self.lbl_status = ctk.CTkLabel(self.tab, text="Status: Ready", text_color="gray")
        self.lbl_status.pack(pady=0)
        self.lbl_results = ctk.CTkLabel(self.tab, text="", font=ctk.CTkFont(size=13, weight="bold"))
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

    def parse_clean_data(self, path):
        depths, values = [], []
        with open(path, 'r') as f:
            for line in f:
                parts = line.replace(',', ' ').split()
                if len(parts) >= 2:
                    try:
                        d = float(parts[0])
                        v = float(parts[1])
                        depths.append(d)
                        values.append(v)
                    except ValueError:
                        continue
        if not depths:
            raise Exception("No numerical data parsed.")
        return depths, values

    def load_file(self, data_type):
        path = filedialog.askopenfilename(filetypes=[("Text/CSV Files", "*.txt *.csv"), ("All Files", "*.*")])
        if not path: 
            return
            
        try:
            d_arr, v_arr = self.parse_clean_data(path)
            filename = path.split('/')[-1]
            
            if data_type == "TID":
                self.depth_tid, self.dose_tid = d_arr, v_arr
                self.lbl_tid.configure(text=filename, text_color="#00e5ff")
            else:
                self.depth_eq, self.flu_eq = d_arr, v_arr
                self.lbl_eq.configure(text=filename, text_color="#00e5ff")
                
        except Exception as e:
            if data_type == "TID":
                self.lbl_tid.configure(text=f"Error: {e}", text_color="red")
            else:
                self.lbl_eq.configure(text=f"Error: {e}", text_color="red")

    def run_M2(self):
        if not self.depth_tid and not self.depth_eq:
            self.lbl_status.configure(text="Error: Load at least one valid data file.", text_color="red")
            return
            
        try:
            target_sh = float(self.e_shield.get())
            lim_tid = float(self.e_limit_tid.get())
            target_cov = float(self.e_cover.get())
            lim_flu = float(self.e_limit_flu.get())
            self.rdm_val = float(self.e_rdm.get())
            
            d_tid = self.depth_tid if self.depth_tid else [-1.0]
            val_tid = self.dose_tid if self.dose_tid else [-1.0]
            d_eq = self.depth_eq if self.depth_eq else [-1.0]
            val_eq = self.flu_eq if self.flu_eq else [-1.0]

            self.lbl_status.configure(text="Status: Starting MATLAB Engine...", text_color="orange")
            self.tab.update()

            if self.app.eng is None: 
                self.app.eng = matlab.engine.start_matlab()
            
            self.lbl_status.configure(text="Status: Calculating Integrated Radiation Risks...", text_color="yellow")
            self.tab.update()

            dose, m_tid, stat_tid, min_sh, deriv, flu, m_flu, stat_flu, min_cov = self.app.eng.M2_radiation_analysis(
                matlab.double(d_tid), matlab.double(val_tid), target_sh, lim_tid,
                matlab.double(d_eq), matlab.double(val_eq), target_cov, lim_flu, self.rdm_val, nargout=9
            )

            res_str = ""
            if self.depth_tid:
                self.res_dose, self.res_margin_tid, self.res_min_shield = dose, m_tid, min_sh
                self.current_deriv = list(deriv[0]) if isinstance(deriv, matlab.double) else deriv
                self.status_tid = "PASS" if stat_tid == 1 else "FAIL"
                sh_txt = f"{min_sh:.2f} mm" if not np.isnan(min_sh) else "Out of bounds"
                res_str += f"[AVIONICS: {self.status_tid}] True TID: {dose:.2f} krad | Req. Shield: {sh_txt}\n"

            if self.depth_eq:
                self.res_flu, self.res_margin_flu, self.res_min_cover = flu, m_flu, min_cov
                self.status_flu = "PASS" if stat_flu == 1 else "FAIL"
                cov_txt = f"{min_cov:.3f} mm" if not np.isnan(min_cov) else "Out of bounds"
                res_str += f"[POWER: {self.status_flu}] True 1-MeV Fluence: {flu:.2e} e/cm² | Req. Coverglass: {cov_txt}"

            self.lbl_results.configure(text=res_str, text_color="white")
            self.lbl_status.configure(text="Analysis Complete!", text_color="gray")
            self.btn_export.configure(state="normal")
            
            self.draw_plot(target_sh, lim_tid, target_cov, lim_flu)
            
        except Exception as e:
            self.lbl_status.configure(text=f"Error: {e}", text_color="red")

    def draw_plot(self, target_sh, lim_tid, target_cov, lim_flu):
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
        # Vertically stacked layout (3 rows, 1 column)
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 7.5), dpi=100)
        fig.patch.set_facecolor('#2b2b2b')

        if self.depth_tid:
            deriv_safe = np.maximum(self.current_deriv, 1e-10)
            
            # --- Subplot 1: Phase 1 (Physics) ---
            ax1.set_facecolor('#2b2b2b')
            ax1.plot(self.depth_tid, self.dose_tid, color='#00e5ff', linewidth=2, label="Dose (krad)")
            ax1.set_yscale('log')
            ax1.set_ylabel('Total Ionizing Dose (krad)', color='#00e5ff')
            ax1.tick_params(axis='y', labelcolor='#00e5ff')
            ax1.set_title('Phase 1: Attenuation Physics (Bethe-Bloch vs Bremsstrahlung)')
            ax1.set_xlabel('Equivalent Aluminum Shielding Depth (mm)')
            ax1.grid(True, alpha=0.3, which="both")
            
            ax1a = ax1.twinx()
            ax1a.plot(self.depth_tid, deriv_safe, color='#ff4081', linewidth=1.5, linestyle='-', label="Attenuation Rate (-dD/dx)")
            ax1a.set_yscale('log')
            ax1a.set_ylabel('Effective Attenuation', color='#ff4081')
            ax1a.tick_params(axis='y', labelcolor='#ff4081')

            # --- Subplot 2: Phase 2 (Avionics Survivability) ---
            ax2.set_facecolor('#2b2b2b')
            ax2.plot(self.depth_tid, self.dose_tid, color='#00e5ff', linewidth=2, label="TID Curve")
            ax2.set_yscale('log')
            
            eff_lim_tid = lim_tid / self.rdm_val
            max_dose = max(self.dose_tid)
            if max_dose > eff_lim_tid:
                ax2.fill_between(self.depth_tid, eff_lim_tid, max_dose, color='#ff3d00', alpha=0.15, label="Danger Zone (Fail)")
                
            ax2.axhline(y=lim_tid, color='#ff9100', linestyle='--', linewidth=1.2, label="Absolute Component Limit")
            ax2.axhline(y=eff_lim_tid, color='#ff3d00', linestyle='-', linewidth=1.5, label=f"Effective Limit (RDM={self.rdm_val})")
            ax2.axvline(x=target_sh, color='yellow', linestyle=':', linewidth=1.5, label=f"Current Shielding ({target_sh} mm)")
            
            if not np.isnan(self.res_min_shield) and self.res_min_shield > 0:
                ax2.axvline(x=self.res_min_shield, color='#00e676', linestyle='-.', linewidth=1.2, label=f"Min Required ({self.res_min_shield:.2f} mm)")

            dot_color = '#00e676' if self.status_tid == "PASS" else '#ff3d00'
            ax2.plot(target_sh, self.res_dose, marker='o', color=dot_color, markersize=8, label="True Received Dose", zorder=5)
            
            ax2.set_title('Phase 2: Avionics Survivability and Mass Optimization')
            ax2.set_xlabel('Equivalent Aluminum Shielding Depth (mm)')
            ax2.set_ylabel('Dose (krad)')
            ax2.legend(loc="upper right", fontsize=8)
            ax2.grid(True, alpha=0.3, which="both")
        else:
            ax1.set_title('Phase 1: TID Data Not Loaded')
            ax2.set_title('Phase 2: TID Data Not Loaded')

        if self.depth_eq:
            # --- Subplot 3: Phase 3 (Solar Panel Survivability) ---
            ax3.set_facecolor('#2b2b2b')
            ax3.plot(self.depth_eq, self.flu_eq, color='#ff9100', linewidth=2, label="EQFLUX Curve")
            ax3.set_yscale('log')
            
            eff_lim_flu = lim_flu / self.rdm_val
            max_flu = max(self.flu_eq)
            if max_flu > eff_lim_flu:
                ax3.fill_between(self.depth_eq, eff_lim_flu, max_flu, color='#ff3d00', alpha=0.15, label="Danger Zone (Fail)")
                
            ax3.axhline(y=lim_flu, color='#ff9100', linestyle='--', linewidth=1.2, label="Absolute Component Limit")
            ax3.axhline(y=eff_lim_flu, color='#ff3d00', linestyle='-', linewidth=1.5, label=f"Effective Limit (RDM={self.rdm_val})")
            ax3.axvline(x=target_cov, color='yellow', linestyle=':', linewidth=1.5, label=f"Current Coverglass ({target_cov} mm)")
            
            if not np.isnan(self.res_min_cover) and self.res_min_cover > 0:
                ax3.axvline(x=self.res_min_cover, color='#00e676', linestyle='-.', linewidth=1.2, label=f"Min Required ({self.res_min_cover:.3f} mm)")

            dot_c = '#00e676' if self.status_flu == "PASS" else '#ff3d00'
            ax3.plot(target_cov, self.res_flu, marker='o', color=dot_c, markersize=8, label="True Received Fluence", zorder=5)
            
            ax3.set_title('Phase 3: Solar Panel Survivability (Displacement Damage)')
            ax3.set_xlabel('Coverglass Thickness (mm)')
            ax3.set_ylabel('1-MeV Equivalent Fluence (e-/cm²)')
            ax3.legend(loc="upper right", fontsize=8)
            ax3.grid(True, alpha=0.3, which="both")
        else:
            ax3.set_title('Phase 3: EQFLUX Data Not Loaded')

        fig.tight_layout(h_pad=4.0)
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

    def popout_plot(self):
        # Prevent execution if data is missing
        if not self.depth_tid and not self.depth_eq: 
            self.label_status.configure(text="Run simulation first.", text_color="orange")
            return

        selection = self.view_var.get()

        # New Tab
        popout_win = ctk.CTkToplevel(self.tab)
        popout_win.title(f"Full Screen: M2 - {selection}")
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
            
            if selection == "1. Attenuation Physics":
                if not self.depth_tid:
                    ax.set_title('Phase 1: TID Data Not Loaded')
                else:
                    deriv_safe = np.maximum(self.current_deriv, 1e-10)
                    ax.plot(self.depth_tid, self.dose_tid, color='#00e5ff', linewidth=2, label="Dose (krad)")
                    ax.set_yscale('log')
                    ax.set_ylabel('Total Ionizing Dose (krad)', color='#00e5ff')
                    ax.tick_params(axis='y', labelcolor='#00e5ff')
                    ax.set_title('Phase 1: Attenuation Physics (Bethe-Bloch vs Bremsstrahlung)')
                    ax.set_xlabel('Equivalent Aluminum Shielding Depth (mm)')
                    ax.grid(True, alpha=0.3, which="both")
                    
                    ax1a = ax.twinx()
                    ax1a.plot(self.depth_tid, deriv_safe, color='#ff4081', linewidth=1.5, linestyle='-', label="Attenuation Rate (-dD/dx)")
                    ax1a.set_yscale('log')
                    ax1a.set_ylabel('Effective Attenuation', color='#ff4081')
                    ax1a.tick_params(axis='y', labelcolor='#ff4081')
                    
            elif selection == "2. Avionics Survivability":
                if not self.depth_tid:
                    ax.set_title('Phase 2: TID Data Not Loaded')
                else:
                    target_sh = float(self.e_shield.get())
                    lim_tid = float(self.e_limit_tid.get())
                    
                    ax.plot(self.depth_tid, self.dose_tid, color='#00e5ff', linewidth=2, label="TID Curve")
                    ax.set_yscale('log')
                    
                    eff_lim_tid = lim_tid / self.rdm_val
                    max_dose = max(self.dose_tid)
                    if max_dose > eff_lim_tid:
                        ax.fill_between(self.depth_tid, eff_lim_tid, max_dose, color='#ff3d00', alpha=0.15, label="Danger Zone (Fail)")
                        
                    ax.axhline(y=lim_tid, color='#ff9100', linestyle='--', linewidth=1.2, label="Absolute Component Limit")
                    ax.axhline(y=eff_lim_tid, color='#ff3d00', linestyle='-', linewidth=1.5, label=f"Effective Limit (RDM={self.rdm_val})")
                    ax.axvline(x=target_sh, color='yellow', linestyle=':', linewidth=1.5, label=f"Current Shielding ({target_sh} mm)")
                    
                    if not np.isnan(self.res_min_shield) and self.res_min_shield > 0:
                        ax.axvline(x=self.res_min_shield, color='#00e676', linestyle='-.', linewidth=1.2, label=f"Min Required ({self.res_min_shield:.2f} mm)")

                    dot_color = '#00e676' if self.status_tid == "PASS" else '#ff3d00'
                    ax.plot(target_sh, self.res_dose, marker='o', color=dot_color, markersize=8, label="True Received Dose", zorder=5)
                    
                    ax.set_title('Phase 2: Avionics Survivability and Mass Optimization')
                    ax.set_xlabel('Equivalent Aluminum Shielding Depth (mm)')
                    ax.set_ylabel('Dose (krad)')
                    ax.legend(loc="upper right", fontsize=8)
                    ax.grid(True, alpha=0.3, which="both")
                    
            elif selection == "3. Solar Panel Survivability":
                if not self.depth_eq:
                    ax.set_title('Phase 3: EQFLUX Data Not Loaded')
                else:
                    target_cov = float(self.e_cover.get())
                    lim_flu = float(self.e_limit_flu.get())
                    
                    ax.plot(self.depth_eq, self.flu_eq, color='#ff9100', linewidth=2, label="EQFLUX Curve")
                    ax.set_yscale('log')
                    
                    eff_lim_flu = lim_flu / self.rdm_val
                    max_flu = max(self.flu_eq)
                    if max_flu > eff_lim_flu:
                        ax.fill_between(self.depth_eq, eff_lim_flu, max_flu, color='#ff3d00', alpha=0.15, label="Danger Zone (Fail)")
                        
                    ax.axhline(y=lim_flu, color='#ff9100', linestyle='--', linewidth=1.2, label="Absolute Component Limit")
                    ax.axhline(y=eff_lim_flu, color='#ff3d00', linestyle='-', linewidth=1.5, label=f"Effective Limit (RDM={self.rdm_val})")
                    ax.axvline(x=target_cov, color='yellow', linestyle=':', linewidth=1.5, label=f"Current Coverglass ({target_cov} mm)")
                    
                    if not np.isnan(self.res_min_cover) and self.res_min_cover > 0:
                        ax.axvline(x=self.res_min_cover, color='#00e676', linestyle='-.', linewidth=1.2, label=f"Min Required ({self.res_min_cover:.3f} mm)")

                    dot_c = '#00e676' if self.status_flu == "PASS" else '#ff3d00'
                    ax.plot(target_cov, self.res_flu, marker='o', color=dot_c, markersize=8, label="True Received Fluence", zorder=5)
                    
                    ax.set_title('Phase 3: Solar Panel Survivability (Displacement Damage)')
                    ax.set_xlabel('Coverglass Thickness (mm)')
                    ax.set_ylabel('1-MeV Equivalent Fluence (e-/cm²)')
                    ax.legend(loc="upper right", fontsize=8)
                    ax.grid(True, alpha=0.3, which="both")

            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # toolbar
            toolbar = NavigationToolbar2Tk(canvas, frame)
            toolbar.update()
            toolbar.pack(side="bottom", fill="x")

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filepath:
            try:
                with open(filepath, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["--- INTEGRATED RADIATION ANALYSIS (TID + DD) ---"])
                    writer.writerow(["Radiation Design Margin (RDM)", self.rdm_val])
                    writer.writerow([])
                    
                    if self.depth_tid:
                        # Fetch inputs directly to include plotting boundaries in CSV
                        target_sh = float(self.e_shield.get())
                        lim_tid = float(self.e_limit_tid.get())
                        eff_lim_tid = lim_tid / self.rdm_val

                        writer.writerow(["[AVIONICS TID RESULTS]"])
                        writer.writerow(["Status", self.status_tid])
                        writer.writerow(["Target Al Shielding [mm]", target_sh])
                        writer.writerow(["Absolute Component Limit [krad]", lim_tid])
                        writer.writerow(["Effective Limit (RDM applied) [krad]", eff_lim_tid])
                        writer.writerow(["True Received Dose [krad]", f"{self.res_dose:.4f}"])
                        writer.writerow(["Safety Margin [krad]", f"{self.res_margin_tid:.4f}"])
                        writer.writerow(["Min Required Al Shielding [mm]", f"{self.res_min_shield:.4f}"])
                        writer.writerow([])
                        writer.writerow(["Depth [mm]", "Dose [krad]", "Attenuation Rate (-dD/dx)"])
                        for d, dose, drv in zip(self.depth_tid, self.dose_tid, self.current_deriv):
                            writer.writerow([d, dose, drv])
                        writer.writerow([])
                        
                    if self.depth_eq:
                        # Fetch inputs directly to include plotting boundaries in CSV
                        target_cov = float(self.e_cover.get())
                        lim_flu = float(self.e_limit_flu.get())
                        eff_lim_flu = lim_flu / self.rdm_val

                        writer.writerow(["[SOLAR PANEL EQFLUX RESULTS]"])
                        writer.writerow(["Status", self.status_flu])
                        writer.writerow(["Target Coverglass [mm]", target_cov])
                        writer.writerow(["Absolute Component Limit [e-/cm2]", f"{lim_flu:.4e}"])
                        writer.writerow(["Effective Limit (RDM applied) [e-/cm2]", f"{eff_lim_flu:.4e}"])
                        writer.writerow(["True 1-MeV Fluence [e-/cm2]", f"{self.res_flu:.4e}"])
                        writer.writerow(["Safety Margin [e-/cm2]", f"{self.res_margin_flu:.4e}"])
                        writer.writerow(["Min Required Coverglass [mm]", f"{self.res_min_cover:.4f}"])
                        writer.writerow([])
                        writer.writerow(["Coverglass Depth [mm]", "1-MeV Fluence [e-/cm2]"])
                        for d, flu in zip(self.depth_eq, self.flu_eq):
                            writer.writerow([d, flu])

                self.lbl_status.configure(text="Status: Data successfully exported!", text_color="#00e676")
            except Exception as e:
                self.lbl_status.configure(text=f"Error exporting data: {str(e)}", text_color="red")