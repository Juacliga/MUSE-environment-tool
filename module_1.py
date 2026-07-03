import customtkinter as ctk
import matlab.engine
import requests
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import filedialog
import numpy as np

class M1_Tab:
    def __init__(self, parent_tab, app_instance):
        self.tab = parent_tab
        self.app = app_instance
        self.current_timestamps = []
        self.current_alt = []
        self.current_rho = []
        self.current_bz = []
        self.current_vsw = []
        self.current_dst = []
        self.current_kp = []
        self.setup_ui()

    def setup_ui(self):
        # --- Main Container (2 Columns) ---
        self.main_container = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.main_container.pack(pady=5, padx=20, fill="x")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)

        # --- FRAME 1: Environment Definition ---
        self.env_frame = ctk.CTkFrame(self.main_container)
        self.env_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.env_frame, text="1. Event Timeframe (OMNIWeb)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        ctk.CTkLabel(self.env_frame, text="Start Date (YYYY-MM-DD):").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.entry_start = ctk.CTkEntry(self.env_frame)
        self.entry_start.insert(0, "2003-10-28") 
        self.entry_start.grid(row=1, column=1, padx=15, pady=10)

        ctk.CTkLabel(self.env_frame, text="End Date (YYYY-MM-DD):").grid(row=2, column=0, padx=15, pady=10, sticky="w")
        self.entry_end = ctk.CTkEntry(self.env_frame)
        self.entry_end.insert(0, "2003-11-01")
        self.entry_end.grid(row=2, column=1, padx=15, pady=10)

        # --- FRAME 2: Spacecraft Parameters ---
        self.sc_frame = ctk.CTkFrame(self.main_container)
        self.sc_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.sc_frame, text="2. Spacecraft Parameters", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        ctk.CTkLabel(self.sc_frame, text="Mass [kg]:").grid(row=1, column=0, padx=15, pady=2, sticky="w")
        self.entry_mass = ctk.CTkEntry(self.sc_frame, height=22)
        self.entry_mass.insert(0, "500")
        self.entry_mass.grid(row=1, column=1, padx=15, pady=2)

        ctk.CTkLabel(self.sc_frame, text="Frontal Area [m^2]:").grid(row=2, column=0, padx=15, pady=2, sticky="w")
        self.entry_area = ctk.CTkEntry(self.sc_frame, height=22)
        self.entry_area.insert(0, "2.5")
        self.entry_area.grid(row=2, column=1, padx=15, pady=2)

        ctk.CTkLabel(self.sc_frame, text="Drag Coeff (Cd):").grid(row=3, column=0, padx=15, pady=2, sticky="w")
        self.entry_cd = ctk.CTkEntry(self.sc_frame, height=22)
        self.entry_cd.insert(0, "2.2")
        self.entry_cd.grid(row=3, column=1, padx=15, pady=2)

        ctk.CTkLabel(self.sc_frame, text="Initial Alt [km]:").grid(row=4, column=0, padx=15, pady=2, sticky="w")
        self.entry_alt = ctk.CTkEntry(self.sc_frame, height=22)
        self.entry_alt.insert(0, "400")
        self.entry_alt.grid(row=4, column=1, padx=15, pady=2)

        ctk.CTkLabel(self.sc_frame, text="Propulsion Isp [s]:").grid(row=5, column=0, padx=15, pady=2, sticky="w")
        self.entry_isp = ctk.CTkEntry(self.sc_frame, height=22)
        self.entry_isp.insert(0, "220")
        self.entry_isp.grid(row=5, column=1, padx=15, pady=2)

        # --- Buttons and Status ---
        self.buttons_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.buttons_frame.pack(pady=10)
        
        self.button_run = ctk.CTkButton(self.buttons_frame, text="Download NASA Data & Run", command=self.run_simulation, font=ctk.CTkFont(weight="bold"))
        self.button_run.grid(row=0, column=0, padx=10)

        self.button_load = ctk.CTkButton(self.buttons_frame, text="Import Local CSV", command=self.load_local_data, fg_color="#1976d2", hover_color="#115293")
        self.button_load.grid(row=0, column=1, padx=10)

        self.button_export = ctk.CTkButton(self.buttons_frame, text="Export Results CSV", command=self.export_csv, fg_color="#2e7d32", state="disabled")
        self.button_export.grid(row=0, column=2, padx=10)

        # Dropdown menu to select specific plot or all plots
        self.view_var = ctk.StringVar(value="All plots")
        self.combo_expand = ctk.CTkOptionMenu(self.buttons_frame, variable=self.view_var, 
                                              values=["All plots", "1. Solar Wind Conditions", "2. Earth Geomagnetic Response", "3. Orbital Decay"], 
                                              fg_color="#5c5c5c")
        self.combo_expand.grid(row=0, column=3, padx=10)

        self.button_expand = ctk.CTkButton(self.buttons_frame, text="Full Screen Figure", 
                                        command=self.popout_plot, fg_color="#5c5c5c")
        self.button_expand.grid(row=0, column=4, padx=10)

        self.label_status = ctk.CTkLabel(self.tab, text="Status: Ready", text_color="gray")
        self.label_status.pack()
        self.label_results_data = ctk.CTkLabel(self.tab, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.label_results_data.pack(pady=5)

        self.plot_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.plot_frame.pack(fill="both", expand=True, padx=20, pady=5)
        self.canvas = None
        self.toolbar = None

    def fetch_nasa_data(self, start_date_str, end_date_str):
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            raise Exception("Date format must be exactly YYYY-MM-DD")

        start_hapi = start_dt.strftime("%Y-%m-%dT00:00:00Z")
        end_hapi = end_dt.strftime("%Y-%m-%dT23:59:59Z")

        info_url = "https://cdaweb.gsfc.nasa.gov/hapi/info?id=OMNI2_H0_MRG1HR"
        info_res = requests.get(info_url)
        if info_res.status_code != 200:
            raise Exception("Could not fetch metadata from NASA HAPI.")
            
        info_data = info_res.json()
        params_found = []
        found_flags = {'kp': False, 'f107': False, 'bz': False, 'vsw': False, 'dst': False}
        
        for index, param in enumerate(info_data.get('parameters', [])):
            orig_name = param['name']          
            p_name = orig_name.upper()         
            
            if not found_flags['kp'] and p_name in ['KP', 'KP1800', 'KP_INDEX']:
                params_found.append((index, orig_name, 'kp'))
                found_flags['kp'] = True
            elif not found_flags['f107'] and p_name in ['F10_INDEX', 'F10_INDEX1800', 'F10', 'F10.7']:
                params_found.append((index, orig_name, 'f107'))
                found_flags['f107'] = True
            elif not found_flags['bz'] and ('BZ' in p_name):
                params_found.append((index, orig_name, 'bz'))
                found_flags['bz'] = True
            elif not found_flags['vsw'] and p_name in ['V', 'V1800', 'V_SW', 'SPEED', 'FLOW_SPEED', 'BULK_SPEED', 'PLASMA_SPEED']:
                params_found.append((index, orig_name, 'vsw'))
                found_flags['vsw'] = True
            elif not found_flags['dst'] and p_name in ['DST', 'DST1800', 'DST_INDEX']:
                params_found.append((index, orig_name, 'dst'))
                found_flags['dst'] = True

        params_found.sort(key=lambda x: x[0])
        params_str = ",".join([p[1] for p in params_found])

        data_url = f"https://cdaweb.gsfc.nasa.gov/hapi/data?id=OMNI2_H0_MRG1HR&parameters={params_str}&time.min={start_hapi}&time.max={end_hapi}"
        response = requests.get(data_url)
        
        if response.status_code != 200:
            raise Exception(f"NASA HAPI Error {response.status_code}: {response.text}")

        lines = response.text.strip().split('\n')
        if not lines or lines[0].startswith("<!DOCTYPE") or lines[0].startswith("<html"):
            raise Exception("NASA API returned an HTML webpage instead of data.")

        year, doy, hour, timestamps = [], [], [], []
        f107_clean, kp_clean, bz_clean, vsw_clean, dst_clean = [], [], [], [], []

        for line in lines:
            parts = line.split(',')
            if len(parts) < 3:
                continue
                
            dt_raw = datetime.strptime(parts[0][:19], "%Y-%m-%dT%H:%M:%S")
            year.append(float(dt_raw.year))
            doy.append(float(dt_raw.timetuple().tm_yday))
            hour.append(float(dt_raw.hour))
            timestamps.append(dt_raw)
            
            row_vals = {}
            for i, p in enumerate(params_found):
                try:
                    row_vals[p[2]] = float(parts[i+1])
                except (ValueError, IndexError):
                    row_vals[p[2]] = float('nan')
            
            kp_raw = row_vals.get('kp', float('nan'))
            f10_raw = row_vals.get('f107', float('nan'))
            bz_raw = row_vals.get('bz', float('nan'))
            vsw_raw = row_vals.get('vsw', float('nan'))
            dst_raw = row_vals.get('dst', float('nan'))
            
            if kp_raw > 90 or kp_raw < 0: kp_clean.append(float('nan'))
            else: kp_clean.append(kp_raw / 10.0) 
            if f10_raw > 900 or f10_raw < 0: f107_clean.append(float('nan'))
            else: f107_clean.append(f10_raw)
            if bz_raw > 900 or bz_raw < -900: bz_clean.append(float('nan'))
            else: bz_clean.append(bz_raw)
            if vsw_raw > 9000 or vsw_raw < 0: vsw_clean.append(float('nan'))
            else: vsw_clean.append(vsw_raw)
            if dst_raw > 9000 or dst_raw < -9000: dst_clean.append(float('nan'))
            else: dst_clean.append(dst_raw)

        def fill_nans(data_list):
            arr = np.array(data_list, dtype=float)
            nans = np.isnan(arr)
            if np.all(nans) or not np.any(nans):
                return data_list
            valid_idx = np.where(~nans)[0]
            nan_idx = np.where(nans)[0]
            arr[nan_idx] = np.interp(nan_idx, valid_idx, arr[valid_idx])
            return arr.tolist()

        return year, doy, hour, fill_nans(f107_clean), fill_nans(kp_clean), fill_nans(bz_clean), fill_nans(vsw_clean), fill_nans(dst_clean), timestamps

    def draw_plot(self, timestamps, bz, vsw, dst, kp, alt_data, rho_data):
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
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 8), dpi=100)
        fig.patch.set_facecolor('#2b2b2b')

        ax1.set_facecolor('#2b2b2b')
        ax1.plot(timestamps, bz, color='#ff3d00', label='Bz (nT)', linewidth=1.5)
        ax1.set_ylabel('Bz (nT)', color='#ff3d00')
        ax1.tick_params(axis='y', labelcolor='#ff3d00')
        ax1.set_title('Solar Wind Conditions (L1 Point)')
        ax1.grid(True, alpha=0.3)
        ax1a = ax1.twinx()  
        ax1a.plot(timestamps, vsw, color='white', linewidth=1.5, linestyle='-')
        ax1a.set_ylabel('Velocity (km/s)', color='white')
        ax1a.tick_params(axis='y', labelcolor='white')

        ax2.set_facecolor('#2b2b2b')
        ax2.plot(timestamps, dst, color='#00e5ff', label='Dst (nT)', linewidth=1.5)
        ax2.set_ylabel('Dst (nT)', color='#00e5ff')
        ax2.tick_params(axis='y', labelcolor='#00e5ff')
        ax2.set_title('Earth Geomagnetic Response')
        ax2.grid(True, alpha=0.3)
        ax2a = ax2.twinx()  
        ax2a.step(timestamps, kp, color='yellow', linewidth=1.5)
        ax2a.set_ylabel('Kp Index (0-9)', color='yellow')
        ax2a.tick_params(axis='y', labelcolor='yellow')

        ax3.set_facecolor('#2b2b2b')
        ax3.plot(timestamps, alt_data, color='#00e676', linewidth=2)
        ax3.set_ylabel('Altitude (km)', color='#00e676')
        ax3.tick_params(axis='y', labelcolor='#00e676')
        ax3.set_title('Impact of Geomagnetic Storm on Orbital Decay')
        ax3.set_xlabel('Date')
        ax3.grid(True, alpha=0.3)
        ax3a = ax3.twinx()  
        ax3a.plot(timestamps, rho_data, color='#ff4081', linestyle='--', linewidth=1.5)
        ax3a.set_ylabel('Density (kg/m^3)', color='#ff4081')
        ax3a.tick_params(axis='y', labelcolor='#ff4081')

        fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

    def run_simulation(self):
        self.button_run.configure(state="disabled")
        self.button_load.configure(state="disabled")
        self.button_export.configure(state="disabled")
        self.tab.update()

        try:
            self.label_status.configure(text="Status: Fetching data from NASA HAPI...", text_color="yellow")
            self.tab.update() 

            start_date = self.entry_start.get().strip()
            end_date = self.entry_end.get().strip()
            m = float(self.entry_mass.get())
            A = float(self.entry_area.get())
            Cd = float(self.entry_cd.get())
            alt = float(self.entry_alt.get())
            isp = float(self.entry_isp.get())

            year, doy, hour, f107, kp, bz, vsw, dst, timestamps = self.fetch_nasa_data(start_date, end_date)

            self.label_status.configure(text="Status: Starting MATLAB Engine...", text_color="orange")
            self.tab.update()
            
            if self.app.eng is None: 
                self.app.eng = matlab.engine.start_matlab()
            
            self.label_status.configure(text="Status: Running Astrodynamics Simulation...", text_color="yellow")
            self.tab.update()

            alt_hist, rho_hist, delta_V, prop_mass = self.app.eng.M1_space_weather(
                matlab.double(year), matlab.double(doy), matlab.double(hour), matlab.double(f107), matlab.double(kp), m, A, Cd, alt, isp, nargout=4
            )

            alt_flat = [item[0] for item in alt_hist]
            rho_flat = [item[0] for item in rho_hist]
            
            # Cast MATLAB variables to Python floats to prevent unhashable type errors
            delta_V = float(delta_V)
            prop_mass = float(prop_mass)

            self.current_timestamps = timestamps
            self.current_alt = alt_flat
            self.current_rho = rho_flat
            self.current_bz = bz
            self.current_vsw = vsw
            self.current_dst = dst
            self.current_kp = kp

            # Reentry error solution
            if np.isnan(delta_V):
                result_text = "CRITICAL FAIL: Atmospheric Re-entry Detected!"
                self.label_results_data.configure(text=result_text, text_color="#ff3d00")
            else:
                result_text = f"Delta-V: {delta_V:.4f} m/s   |   Extra Propellant: {prop_mass:.2f} g"
                self.label_results_data.configure(text=result_text, text_color="#00e5ff")
                
            self.label_status.configure(text="Status: Simulation Complete!", text_color="#00e676") 
            
            self.draw_plot(timestamps, bz, vsw, dst, kp, alt_flat, rho_flat)
            self.button_export.configure(state="normal")

        except Exception as e:
            self.label_status.configure(text=f"Error: {str(e)}", text_color="red")
        finally:
            self.button_run.configure(state="normal")
            self.button_load.configure(state="normal")
            self.tab.update()

    def load_local_data(self):
        filepath = filedialog.askopenfilename(
            title="Select OMNIWeb File (CSV)",
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not filepath: return

        self.button_run.configure(state="disabled")
        self.button_load.configure(state="disabled")
        self.button_export.configure(state="disabled")
        
        filename = filepath.split('/')[-1]
        self.label_status.configure(text=f"Status: Reading local file {filename}...", text_color="yellow")
        self.tab.update()

        try:
            year, doy, hour, timestamps = [], [], [], []
            f107_clean, kp_clean, bz_clean, vsw_clean, dst_clean = [], [], [], [], []

            with open(filepath, mode='r') as file:
                lines = file.readlines()
                for line in lines:
                    if line.strip() == "" or line.lower().startswith("date") or line.lower().startswith("year") or line.lower().startswith("time"):
                        continue
                    parts = line.strip().split(',')
                    if len(parts) < 6: continue 
                    
                    dt_raw = datetime.strptime(parts[0][:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                    year.append(float(dt_raw.year))
                    doy.append(float(dt_raw.timetuple().tm_yday))
                    hour.append(float(dt_raw.hour))
                    timestamps.append(dt_raw)
                    f107_clean.append(float(parts[1]))
                    kp_clean.append(float(parts[2]))
                    bz_clean.append(float(parts[3]))
                    vsw_clean.append(float(parts[4]))
                    dst_clean.append(float(parts[5]))

            m = float(self.entry_mass.get())
            A = float(self.entry_area.get())
            Cd = float(self.entry_cd.get())
            alt = float(self.entry_alt.get())
            isp = float(self.entry_isp.get())

            if self.app.eng is None: self.app.eng = matlab.engine.start_matlab()

            alt_hist, rho_hist, delta_V, prop_mass = self.app.eng.M1_space_weather(
                matlab.double(year), matlab.double(doy), matlab.double(hour), matlab.double(f107_clean), matlab.double(kp_clean), m, A, Cd, alt, isp, nargout=4
            )

            alt_flat = [item[0] for item in alt_hist]
            rho_flat = [item[0] for item in rho_hist]
            
            # Cast MATLAB variables to Python floats to prevent unhashable type errors
            delta_V = float(delta_V)
            prop_mass = float(prop_mass)

            self.current_timestamps = timestamps
            self.current_alt = alt_flat
            self.current_rho = rho_flat
            self.current_bz = bz_clean
            self.current_vsw = vsw_clean
            self.current_dst = dst_clean
            self.current_kp = kp_clean

            # Reentry error solution
            if np.isnan(delta_V):
                result_text = "CRITICAL FAIL: Atmospheric Re-entry Detected!"
                self.label_results_data.configure(text=result_text, text_color="#ff3d00")
            else:
                result_text = f"Delta-V: {delta_V:.4f} m/s   |   Extra Propellant: {prop_mass:.2f} g"
                self.label_results_data.configure(text=result_text, text_color="#00e5ff")
                
            self.label_status.configure(text="Status: Simulation Complete (Local Data)!", text_color="#00e676") 
            self.draw_plot(timestamps, bz_clean, vsw_clean, dst_clean, kp_clean, alt_flat, rho_flat)
            self.button_export.configure(state="normal")

        except Exception as e:
            self.label_status.configure(text=f"Error: {str(e)}", text_color="red")
        finally:
            self.button_run.configure(state="normal")
            self.button_load.configure(state="normal")
            self.tab.update()         

    def popout_plot(self):
        # Prevent execution if data is missing
        if not self.current_timestamps: 
            self.label_status.configure(text="Run simulation first.", text_color="orange")
            return

        selection = self.view_var.get()

        # New Tab
        popout_win = ctk.CTkToplevel(self.tab)
        popout_win.title(f"Full Screen: M1 - {selection}")
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
            
            if selection == "1. Solar Wind Conditions":
                ax.plot(self.current_timestamps, self.current_bz, color='#ff3d00', label='Bz (nT)', linewidth=1.5)
                ax.set_ylabel('Bz (nT)', color='#ff3d00')
                ax.tick_params(axis='y', labelcolor='#ff3d00')
                ax.set_title('Solar Wind Conditions (L1 Point)')
                ax.grid(True, alpha=0.3)
                
                ax1a = ax.twinx()  
                ax1a.plot(self.current_timestamps, self.current_vsw, color='white', linewidth=1.5, linestyle='-')
                ax1a.set_ylabel('Velocity (km/s)', color='white')
                ax1a.tick_params(axis='y', labelcolor='white')
                
            elif selection == "2. Earth Geomagnetic Response":
                ax.plot(self.current_timestamps, self.current_dst, color='#00e5ff', label='Dst (nT)', linewidth=1.5)
                ax.set_ylabel('Dst (nT)', color='#00e5ff')
                ax.tick_params(axis='y', labelcolor='#00e5ff')
                ax.set_title('Earth Geomagnetic Response')
                ax.grid(True, alpha=0.3)
                
                ax2a = ax.twinx()  
                ax2a.step(self.current_timestamps, self.current_kp, color='yellow', linewidth=1.5)
                ax2a.set_ylabel('Kp Index (0-9)', color='yellow')
                ax2a.tick_params(axis='y', labelcolor='yellow')
                
            elif selection == "3. Orbital Decay":
                ax.plot(self.current_timestamps, self.current_alt, color='#00e676', linewidth=2)
                ax.set_ylabel('Altitude (km)', color='#00e676')
                ax.tick_params(axis='y', labelcolor='#00e676')
                ax.set_title('Impact of Geomagnetic Storm on Orbital Decay')
                ax.grid(True, alpha=0.3)
                
                ax3a = ax.twinx()  
                ax3a.plot(self.current_timestamps, self.current_rho, color='#ff4081', linestyle='--', linewidth=1.5)
                ax3a.set_ylabel('Density (kg/m^3)', color='#ff4081')
                ax3a.tick_params(axis='y', labelcolor='#ff4081')

            ax.set_xlabel('Date')
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # toolbar
            toolbar = NavigationToolbar2Tk(canvas, frame)
            toolbar.update()
            toolbar.pack(side="bottom", fill="x")

    def export_csv(self):
        if not self.current_timestamps: return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filepath:
            try:
                with open(filepath, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Date (UTC)", "Bz [nT]", "Vsw [km/s]", "Dst [nT]", "Kp", "Altitude [km]", "Density [kg/m^3]"])
                    for t, b, v, d, k, a, r in zip(self.current_timestamps, self.current_bz, self.current_vsw, self.current_dst, self.current_kp, self.current_alt, self.current_rho):
                        writer.writerow([t.strftime("%Y-%m-%d %H:%M:%S"), b, v, d, k, a, r])
                self.label_status.configure(text="Status: Data successfully exported!", text_color="#00e676")
            except Exception as e:
                self.label_status.configure(text=f"Error exporting: {str(e)}", text_color="red")