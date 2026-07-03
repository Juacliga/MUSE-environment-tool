function [altitude_hist, rho_hist, delta_V, propellant_mass_g] = M1_space_weather(year, doy, hour, F107, Kp, m, A, Cd, initial_altitude_km, Isp)
% Simulates orbital decay due to Space Weather
year = year(:); doy = doy(:); hour = hour(:); F107 = F107(:); Kp = Kp(:);
num_steps = length(year);
if num_steps == 0
    error('MATLAB Engine: Received empty data arrays.');
end
ballistic_coeff = (Cd * A) / m; 
mu = 3.986e14; Rt = 6371e3; dt = 3600;          
a = Rt + (initial_altitude_km * 1000);                     
altitude_hist = zeros(num_steps, 1);
rho_hist = zeros(num_steps, 1);
Kp_table = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
Ap_table = [0, 4, 7, 15, 27, 48, 80, 132, 207, 400];
F107_avg = mean(F107(~isnan(F107)));
if isnan(F107_avg), F107_avg = 150; end

reentry_triggered = false; % Survival flag

for i = 1:num_steps
    if isnan(F107(i)) || isnan(Kp(i))
        if i > 1, F107_current = F107_prev; Kp_current = Kp_prev;
        else, F107_current = 100; Kp_current = 2; end
    else
        F107_current = F107(i); Kp_current = Kp(i);
    end
    F107_prev = F107_current; Kp_prev = Kp_current;
    
    altitude_m = a - Rt;
    
    % % ATMOSPHERIC RE-ENTRY CONTROL (If altitude drops below 100 km)
    if altitude_m <= 100000 
        reentry_triggered = true;
    end
    
    if reentry_triggered
        altitude_hist(i) = 0; % Zero altitude, spacecraft destroyed
        rho_hist(i) = NaN;    % Density calculation aborted
        continue;             % Skip iteration to avoid complex numbers in sqrt
    end
    
    Ap_current = interp1(Kp_table, Ap_table, Kp_current, 'linear', 'extrap');
    [~, density_out] = atmosnrlmsise00(altitude_m, 0, 0, year(i), doy(i), hour(i)*3600, F107_current, F107_avg, Ap_current);
    rho = density_out(6);
    da = - rho * ballistic_coeff * sqrt(mu * a) * dt;
    a = a + da; 
    altitude_hist(i) = (a - Rt) / 1000; 
    rho_hist(i) = rho;
end

% If satellite re-entered, required Delta-V is uncalculable (Mission Failed)
if reentry_triggered
    delta_V = NaN;
    propellant_mass_g = NaN;
else
    altitude_lost_m = (initial_altitude_km * 1000) - (altitude_hist(end) * 1000);
    V_orb = sqrt(mu / (Rt + (initial_altitude_km * 1000)));
    delta_V = (V_orb / (2 * (Rt + (initial_altitude_km * 1000)))) * altitude_lost_m;
    g0 = 9.80665;       
    propellant_mass = m * (1 - exp(-delta_V / (Isp * g0)));
    propellant_mass_g = propellant_mass * 1000;
end
end