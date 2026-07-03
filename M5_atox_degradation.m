function [t_yrs, fluence_hist, thick_hist, alpha_hist, temp_hist, pass_flag] = M5_atox_degradation(alt_km, f107_index, years, Ey_e24, th_init_mm, alpha_init, eps_ir, alpha_sub)
% PL5_ATOX_DEGRADATION_SIM
% Evaluates LEO Atomic Oxygen (ATOX) erosion and coupled thermo-optical 
% degradation using altitude-dependent orbital dynamics.

% 1. Environmental Model (ATOX Density & Velocity)
% Earth physical constants
mu = 3.986004418e5; % Earth's gravitational parameter [km^3/s^2]
R_earth = 6371;      % Mean Earth radius [km]

% Calculate exact circular orbital velocity based on altitude [km/s]
v_orb_km_s = sqrt(mu / (R_earth + alt_km)); 
v_orb = v_orb_km_s * 1e5; % Convert to [cm/s] for flux calculation

% Atomic Oxygen density model (scaled by F10.7 index)
n_300 = 1e9 * (f107_index / 70)^2; 
scale_H = 40 + (f107_index / 100) * 20; 
N_O = n_300 * exp(-(alt_km - 300) / scale_H); % Density [atoms/cm^3]

% Calculated ATOX Flux [atoms/cm^2/s]
flux = N_O * v_orb; 

% 2. Integration over Mission Lifetime
sec_per_yr = 365.25 * 24 * 3600;
t_yrs = linspace(0, years, 100);
fluence_hist = flux * t_yrs * sec_per_yr; % Total Fluence [atoms/cm^2]

% 3. Structural Erosion Calculation
Ey = Ey_e24 * 1e-24; % Erosion yield [cm^3/atom]
erosion_cm = fluence_hist * Ey; 

th_init_cm = th_init_mm / 10;
thick_hist_cm = th_init_cm - erosion_cm;
thick_hist = thick_hist_cm * 10; % Back to [mm]
thick_hist(thick_hist < 0) = 0; % Cap at zero

% 4. Thermo-Optical Degradation (Carpet Effect)
% Asymptotic increase in absorptivity due to surface roughening
alpha_max_rough = min(0.95, alpha_init + 0.15); 
alpha_hist = alpha_init + (alpha_max_rough - alpha_init) * (1 - exp(-fluence_hist / 1.5e21));

% Substrate exposure if layer is fully eroded
alpha_hist(thick_hist == 0) = alpha_sub; 

% 5. Thermal Impact (Equilibrium Temperature)
S = 1361; % Solar constant [W/m^2]
sigma = 5.67e-8; % Stefan-Boltzmann constant
temp_hist = ((alpha_hist .* S) / (eps_ir * sigma)).^0.25 - 273.15; % [Celsius]

% 6. Survival Flag
if min(thick_hist) > 0
    pass_flag = 1; % PASS
else
    pass_flag = 0; % FAIL
end
end