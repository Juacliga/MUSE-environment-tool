function [t_hours, T_hist, V_surf_hist, E_int_hist, esd_flag] = M3_plasma_charging(ecl_start, ecl_dur, sub_start, sub_dur, Ne_peak, Te_peak, J_R_peak, mass, cp, area, J_photo_uA, sey, sigma_25, E_act, eps_r, E_breakdown)
% PL3_PLASMA_CHARGING_SIM Resolves Thermo-Electric Coupled ODEs for GEO Environments
q = 1.602e-19; kB = 1.38e-23; me = 9.109e-31; mi = 1.673e-27;      
eps0 = 8.854e-12; sigma_SB = 5.67e-8; Gs = 1361;           
alpha = 0.85; eps_ir = 0.80; % Radiator thermal properties      
eps_dielec = eps0 * eps_r;
J_ph0 = J_photo_uA * 1e-6; 
Ne_quiet = 10 * 1e6; Te_quiet_eV = 1.0;         
dt = 30; t_steps = 0:dt:(24*3600); N = length(t_steps);
T_hist = zeros(1, N); V_surf_hist = zeros(1, N); E_int_hist = zeros(1, N);
Q_in_sun = alpha * Gs * (area / 4);
T_hist(1) = (Q_in_sun / (eps_ir * sigma_SB * area))^0.25;
E_int_hist(1) = 0;
ecl_on = ecl_start * 3600; ecl_off = ecl_on + (ecl_dur * 60);
sub_mid = (sub_start * 3600) + ((sub_dur * 60) / 2); 
sub_spread = (sub_dur * 60) / 4; 
opt = optimset('Display', 'off');

for k = 1:N-1
    time = t_steps(k);
    sunlight = (time < ecl_on) || (time > ecl_off);
    pulse = exp(-0.5 * ((time - sub_mid) / sub_spread)^2);
    
    Ne_m3 = Ne_quiet + ((Ne_peak * 1e6) - Ne_quiet) * pulse;
    Te_eV = Te_quiet_eV + ((Te_peak * 1000) - Te_quiet_eV) * pulse;
    J_R_flux = (J_R_peak * 1e-12 * 10000) * pulse;
    Te_K = Te_eV * 11604;
    
    Qin = double(sunlight) * Q_in_sun;
    Qout = eps_ir * sigma_SB * area * T_hist(k)^4;
    dTdt = (Qin - Qout) / (mass * cp);
    T_hist(k+1) = T_hist(k) + dTdt * dt;
    
    kB_eV = 8.617e-5; 
    sigma_T = sigma_25 * exp((E_act / kB_eV) * (1/298.15 - 1/T_hist(k)));
    dEdt = (J_R_flux - sigma_T * E_int_hist(k)) / eps_dielec;
    E_int_hist(k+1) = E_int_hist(k) + dEdt * dt;
    
    Je0 = (q * Ne_m3 / 2) * sqrt((2 * kB * Te_K) / (pi * me));
    Ji0 = (q * Ne_m3 / 2) * sqrt((2 * kB * Te_K) / (pi * mi)); 
    
    func = @(V) calc_net_current(V, Je0, Ji0, J_ph0 * double(sunlight), Te_eV, sey);
    
    % Dynamic bounded root finding to prevent numerical collapse
    v_min = -10 * Te_eV; 
    v_max = 200; 
    if func(v_min) * func(v_max) <= 0
        V_sol = fzero(func, [v_min, v_max], opt);
    else
        V_sol = fminsearch(@(V) abs(func(V)), 0);
    end
    V_surf_hist(k) = V_sol;
end
V_surf_hist(N) = V_surf_hist(N-1);
t_hours = t_steps / 3600;
T_hist = T_hist - 273.15; 
esd_flag = double(max(E_int_hist) > E_breakdown);
end

function J_net = calc_net_current(V, Je0, Ji0, J_ph0, Te_eV, sey)
T_ph_eV = 1.5; 
if V < 0
    Je = -Je0 * exp(V / Te_eV) * (1 - sey);
    Ji = Ji0 * (1 - V / Te_eV); 
    J_ph = J_ph0;
else
    Je = -Je0 * (1 + V / Te_eV) * (1 - sey);
    Ji = Ji0 * exp(-V / Te_eV);
    J_ph = J_ph0 * exp(-V / T_ph_eV); 
end
J_net = Je + Ji + J_ph;
end