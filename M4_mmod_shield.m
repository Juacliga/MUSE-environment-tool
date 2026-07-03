function [vel_range, dc_mono, dc_whipple, mass_mono, mass_whipple, time_yrs, prob_survival] = M4_mmod_shield(area, years, flux_rate, v_imp, rho_p, S_standoff, rho_t, sigma_y_mpa, c_t, dp_design, theta_deg)
% PL4_MMOD_SHIELD_SIM
% Evaluates Ballistic Limits and Mass Trade-offs for Spacecraft Shielding
% Implements the 3-Regime Christiansen BLE (Ballistic, Shatter, Hypervelocity)

% 1. Convert Units and Calculate Normal Velocity
sigma_y = sigma_y_mpa * 0.145038; % Convert MPa to ksi
theta = theta_deg * (pi / 180);   % Convert degrees to radians

% The normal component of velocity drives penetration depth
v_n = v_imp * cos(theta); 
if v_n < 0.1
    v_n = 0.1; % Prevent division by zero
end

% 2. MASS OPTIMIZATION (Cour-Palais for Mono, Christiansen for Whipple)
% Monolithic Requirement
P = 5.24 * (dp_design^(19/18)) * (rho_p/rho_t)^0.5 * (v_n/c_t)^(2/3);
t_mono = 1.8 * P; % [cm]
mass_mono = (t_mono / 100) * rho_t * 1000; % [kg/m^2]

% Whipple Requirement (V > 7 km/s Hypervelocity regime for baseline design)
t_bumper = 0.25 * dp_design * (rho_p / rho_t);
t_rear = (41.56 * dp_design^3 * rho_p * v_n) / (S_standoff^2 * sigma_y);
mass_whipple = ((t_bumper + t_rear) / 100) * rho_t * 1000; % [kg/m^2]

% 3. BALLISTIC LIMIT CURVES (Critical Diameter vs Normal Velocity)
vel_range = linspace(1, 15, 100); 
dc_mono = zeros(1, 100);
dc_whipple = zeros(1, 100);

% Fixed limits for the Shatter Regime Interpolation
% Calculated exactly at V_n = 3 km/s (Ballistic Limit) and V_n = 7 km/s (Hypervelocity Limit)
P_eff_3 = (t_rear + t_bumper) / 1.8; 
dc_3 = (P_eff_3 / (5.24 * (rho_p/rho_t)^0.5 * (3.0/c_t)^(2/3)))^(18/19);
dc_7 = ((t_rear * S_standoff^2 * sigma_y) / (41.56 * rho_p * 7.0))^(1/3);

for i = 1:100
    V_n_iter = vel_range(i) * cos(theta);
    if V_n_iter < 0.1
        V_n_iter = 0.1;
    end

    % A. Inverse Cour-Palais (Monolithic)
    P_lim = t_mono / 1.8;
    dc_mono(i) = (P_lim / (5.24 * (rho_p/rho_t)^0.5 * (V_n_iter/c_t)^(2/3)))^(18/19);

    % B. Inverse Christiansen 3-Regime (Whipple Shield)
    if V_n_iter < 3.0
        % Regime 1: Low Velocity (Intact Projectile Cratering)
        dc_whipple(i) = (P_eff_3 / (5.24 * (rho_p/rho_t)^0.5 * (V_n_iter/c_t)^(2/3)))^(18/19);

    elseif V_n_iter > 7.0
        % Regime 3: Hypervelocity (Debris Cloud Melt/Vaporization)
        dc_whipple(i) = ((t_rear * S_standoff^2 * sigma_y) / (41.56 * rho_p * V_n_iter))^(1/3);

    else
        % Regime 2: The Shatter Regime (Linear Interpolation)
        % This creates the characteristic "dip" in the performance curve
        dc_whipple(i) = dc_3 + ((dc_7 - dc_3) / (7.0 - 3.0)) * (V_n_iter - 3.0);
    end
end

% 4. POISSON PROBABILITY OF SURVIVAL
time_yrs = linspace(0, years, 100);
prob_survival = exp(-flux_rate * area .* time_yrs);

end