function [received_dose, safety_margin_tid, status_flag_tid, min_shielding, derivative_array, received_flu, safety_margin_flu, status_flag_flu, min_cover] = M2_radiation_analysis(depth_array_tid, dose_array_tid, target_thickness, dose_limit_tid, depth_array_eq, flu_array_eq, target_cover, flu_limit, rdm)
% PL2_RADIATION_ANALYSIS Evaluates spacecraft survivability against ionizing and non-ionizing radiation.
%
% This function integrates two distinct environmental models:
%   1. SHIELDOSE-2 (TID): Calculates Total Ionizing Dose for internal avionics.
%   2. EQFLUX (DD): Calculates Displacement Damage (1-MeV equivalent fluence) for external solar panels.
%
% INPUTS:
%   depth_array_tid  - Aluminum shielding equivalent depth from SHIELDOSE-2 [mm]
%   dose_array_tid   - Total Ionizing Dose (TID) curve from SPENVIS [krad]
%   target_thickness - Current spacecraft shielding design thickness [mm]
%   dose_limit_tid   - Maximum allowable TID for the specific microchip [krad]
%   depth_array_eq   - Coverglass shielding depth from EQFLUX [mm]
%   flu_array_eq     - 1-MeV equivalent electron fluence curve from SPENVIS [e-/cm2]
%   target_cover     - Current solar array coverglass design thickness [mm]
%   flu_limit        - Maximum allowable fluence for solar cell degradation [e-/cm2]
%   rdm              - Radiation Design Margin (ECSS standard safety multiplier)
%
% OUTPUTS:
%   received_dose    - Interpolated true TID at the current target thickness [krad]
%   safety_margin_tid- Remaining TID tolerance accounting for RDM [krad]
%   status_flag_tid  - 1 (PASS) if safe, 0 (FAIL) if effective dose exceeds limit
%   min_shielding    - Exact minimum Al thickness required to pass TID requirements [mm]
%   derivative_array - Rate of TID attenuation (-dD/dx) to visualize Bremsstrahlung
%   received_flu     - Interpolated true 1-MeV fluence at current coverglass [e-/cm2]
%   safety_margin_flu- Remaining DD tolerance accounting for RDM [e-/cm2]
%   status_flag_flu  - 1 (PASS) if safe, 0 (FAIL) if effective fluence exceeds limit
%   min_cover        - Exact minimum coverglass required to pass DD requirements [mm]

    %% 0. FAIL-SAFE INITIALIZATION
    % Pre-allocate all outputs to NaN or default values.
    % This ensures that the MATLAB engine will always return the exact number 
    % of required arguments to the Python frontend, preventing execution crashes 
    % even if the user decides to run the simulation without loading one of the SPENVIS files.
    received_dose = NaN; safety_margin_tid = NaN; status_flag_tid = -1; min_shielding = NaN; derivative_array = NaN;
    received_flu  = NaN; safety_margin_flu = NaN; status_flag_flu = -1; min_cover     = NaN;

    %% 1. AVIONICS ANALYSIS (Total Ionizing Dose - SHIELDOSE-2)
    % Executes only if valid TID data arrays have been passed from Python.
    if depth_array_tid(1) ~= -1
        
        % Force arrays to column vectors to prevent matrix dimension mismatches
        depth_array_tid = depth_array_tid(:);
        dose_array_tid = dose_array_tid(:);
        
        % Filter strictly positive data points to prevent log(0) computational errors
        valid_idx1 = depth_array_tid > 0 & dose_array_tid > 0;
        d_arr1 = depth_array_tid(valid_idx1);
        dose_arr1 = dose_array_tid(valid_idx1);
        
        % Ensure strict uniqueness (Monotonicity Filter)
        % SPENVIS text files often contain overlapping tables. The 'unique' function
        % removes duplicated depths, strictly enforcing the monotonic behavior required 
        % for accurate numerical interpolation.
        [d_arr1_u, idx_u1] = unique(d_arr1, 'stable');
        dose_arr1_u = dose_arr1(idx_u1);
        
        % 1.1 PHYSICS ANALYSIS: Calculate Attenuation Rate (-dD/dx)
        % Evaluates how fast the radiation is being blocked. A drop to zero implies
        % that Bremsstrahlung (X-rays) has become the dominant radiation source.
        dD = gradient(dose_arr1_u);
        dx = gradient(d_arr1_u);
        deriv = zeros(length(depth_array_tid), 1);
        deriv(idx_u1) = -(dD ./ dx); % Negative gradient applied to represent positive attenuation drop
        deriv(isnan(deriv) | isinf(deriv)) = 0; % Sanitize numerical noise
        derivative_array = deriv(:)'; 

        % 1.2 FORWARD CALCULATION: Dose at Target Thickness (Log-Log Interpolation)
        log_depth1 = log10(d_arr1_u);
        log_dose1 = log10(dose_arr1_u);
        
        if target_thickness <= min(d_arr1_u)
            received_dose = max(dose_arr1_u);
        elseif target_thickness >= max(d_arr1_u)
            received_dose = min(dose_arr1_u);
        else
            log_received = interp1(log_depth1, log_dose1, log10(target_thickness), 'linear');
            received_dose = 10^(log_received);
        end

        % 1.3 OPERATIONAL CHECKS (Applying Radiation Design Margin)
        effective_dose = received_dose * rdm;
        safety_margin_tid = dose_limit_tid - effective_dose;
        status_flag_tid = double(effective_dose <= dose_limit_tid);

        % 1.4 REVERSE ENGINEERING: Minimum Shielding Required
        % Determine the exact geometric thickness required to meet the RDM-enforced safety limit.
        [sorted_doses, sort_idx1] = sort(dose_arr1_u, 'ascend');
        sorted_depths = d_arr1_u(sort_idx1);
        [unique_doses, unique_idx1] = unique(sorted_doses, 'stable');
        unique_depths = sorted_depths(unique_idx1);
        
        target_dose = dose_limit_tid / rdm;

        if target_dose >= max(unique_doses)
            min_shielding = 0.0; % Component is extremely robust; no additional shielding required
        elseif target_dose <= min(unique_doses)
            min_shielding = NaN; % Environment is too harsh; structural limits exceeded
        else
            log_min_shield = interp1(log10(unique_doses), log10(unique_depths), log10(target_dose), 'linear');
            min_shielding = 10^(log_min_shield);
        end
    end

    %% 2. SOLAR PANELS ANALYSIS (Displacement Damage - EQFLUX)
    % Executes only if valid EQFLUX data arrays have been passed from Python.
    if depth_array_eq(1) ~= -1
        
        depth_array_eq = depth_array_eq(:);
        flu_array_eq = flu_array_eq(:);
        
        valid_idx2 = depth_array_eq > 0 & flu_array_eq > 0;
        d_arr2 = depth_array_eq(valid_idx2);
        flu_arr2 = flu_array_eq(valid_idx2);
        
        % Ensure strict uniqueness (Monotonicity Filter) for EQFLUX summary tables
        [d_arr2_u, idx_u2] = unique(d_arr2, 'stable');
        flu_arr2_u = flu_arr2(idx_u2);
        
        % 2.1 FORWARD CALCULATION: Fluence at Target Coverglass (Log-Log Interpolation)
        log_depth2 = log10(d_arr2_u);
        log_flu2 = log10(flu_arr2_u);
        
        if target_cover <= min(d_arr2_u)
            received_flu = max(flu_arr2_u);
        elseif target_cover >= max(d_arr2_u)
            received_flu = min(flu_arr2_u);
        else
            log_received_flu = interp1(log_depth2, log_flu2, log10(target_cover), 'linear');
            received_flu = 10^(log_received_flu);
        end

        % 2.2 OPERATIONAL CHECKS (Applying Radiation Design Margin)
        effective_flu = received_flu * rdm;
        safety_margin_flu = flu_limit - effective_flu;
        status_flag_flu = double(effective_flu <= flu_limit);

        % 2.3 REVERSE ENGINEERING: Minimum Coverglass Required
        [sorted_flus, sort_idx2] = sort(flu_arr2_u, 'ascend');
        sorted_covers = d_arr2_u(sort_idx2);
        [unique_flus, unique_idx2] = unique(sorted_flus, 'stable');
        unique_covers = sorted_covers(unique_idx2);
        
        target_flu = flu_limit / rdm;

        if target_flu >= max(unique_flus)
            min_cover = 0.0; % Cell is extremely robust
        elseif target_flu <= min(unique_flus)
            min_cover = NaN; % Environment exceeds physical coverglass limits
        else
            log_min_cover = interp1(log10(unique_flus), log10(unique_covers), log10(target_flu), 'linear');
            min_cover = 10^(log_min_cover);
        end
    end
  end