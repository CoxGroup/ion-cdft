import numpy as np
import lmft_utils as lmft
import plot_utils as plt
import neural_utils as neural
import scipy.constants as const

alpha_updates_default_onetype = {
    10: 0.0001,
    20: 0.001,
    50: 0.001,
    100: 0.005,
    300: 0.005,
    900: 0.008,
    2000: 0.01,
    5000: 0.1,
}

alpha_updates_default_onetype_LR = {
    10: 0.0001,
    20: 0.0005,
    50: 0.0006,
    100: 0.0008,
    300: 0.001,
    900: 0.002,
    2000: 0.005,
    2500: 0.007,
    3000: 0.01,
    3500: 0.05,
    4000: 0.1,
}
alpha_updates_default_twotype = {
    10: 0.000001,
    20: 0.00001,
    50: 0.00002,
    100: 0.00004,
    200: 0.00006,
    400: 0.0001,
    1000: 0.0002,
    1200: 0.0004,
    1400: 0.0005,
    1700: 0.0006,
    1800: 0.0007,
    1900: 0.0008,
    2100: 0.0009,
    2200: 0.001,
    2300: 0.0011,
    2400: 0.0012,
    2600: 0.0013,
    2800: 0.0014,
    3000: 0.0015,
    3200: 0.0016,
    3400: 0.0018,
    3600: 0.0020,
    3800: 0.0021,
    4000: 0.0023,
    4200: 0.0025,
    4400: 0.0026,
    4600: 0.0028,
    4800: 0.0030,
    5000: 0.0032,
    5200: 0.0035,
    5400: 0.0036,
    5500: 0.0040,
    5800: 0.0050,
    6000: 0.0060,
    6200: 0.008,
    6400: 0.015,
    7000: 0.02,
    8000: 0.03,
    9000: 0.07,
    10000: 0.08,
}

alpha_restr_updates_default = {
    1100: 0.015,
    1200: 0.02,
    1500: 0.05,
    1800: 0.08,
    2000: 0.10,
    2200: 0.15,
}


def minimise_SR_onetype(model, zbins, muloc, initial_guess, input_bins=1001,
                        plot=False, maxiter=10000, 
                        alpha_initial=1e-6, alpha_updates=None, 
                        print_every=1000, plot_every=1000, tolerance=5e-6,
                        output_dict=False):
    """
    Calculate the density profile with neural DFT using a standard Picard iteration.

    Parameters:
    - model (tf.keras.Model): Keras model for calculating the one-body direct correlation function.
    - zbins (array-like): Spatial grid points.
    - muloc (array-like): Local chemical potential
    - plot (bool): Toggle for interactive plotting.
    - maxiter (int): Maximum number of Picard steps.
    - alpha_initial (float): Initial value for the Picard parameter alpha.
    - alpha_updates (dict): Iteration thresholds and corresponding alpha values.
    - initial_guess (float): Initial guess for the density profile.
    - print_every (int): Print the iteration number every n steps.
    - plot_every (int): Update the plot every n steps.
    - tolerance (float): Convergence tolerance.

    Returns:
    - tuple: z coordinates and density profile.
    """
    
    # setting up grid
    rho_new = np.zeros_like(zbins)
    valid = np.isfinite(muloc)
    rho = initial_guess * np.ones_like(zbins)
    L = zbins[-1] - zbins[0]
    log_rho_new = np.zeros_like(zbins)
    log_rho = np.zeros_like(zbins)
    valid = np.isfinite(muloc)
    log_rho[valid] = np.log(initial_guess)
    log_rho[~valid] = -np.inf 

    # Picard iteration parameter
    alpha = alpha_initial
    if alpha_updates is None:
        alpha_updates = alpha_updates_default_onetype

    if plot:
        fig, ax = plt.configure_plot(zbins)
        color_count = 0


    for i in range(maxiter + 1):
        if i in alpha_updates:
            alpha = alpha_updates[i]

        if plot and i % plot_every == 0:
            plt.plot_interactive_SR_onetype(fig, ax, zbins, rho, muloc, color_count)
            color_count += 1

        # correlation from trained SR model
        c1_pred = neural.c1_onetype(model, rho, input_bins, output_dict=output_dict)
        
        # update density
        log_rho_new[valid] = muloc[valid] + c1_pred[valid]
        log_rho_new[~valid] = -np.inf 
        rho_new = np.exp(log_rho_new)
        log_rho = (1 - alpha) * log_rho + alpha * log_rho_new
        rho = np.exp(log_rho)
        
        # check convergence
        delta = np.max(np.abs(rho_new - rho))
         

        if np.isnan(delta):
            print("Not converged: delta is NaN")
            return None, None
        
        relative_error = delta / np.max(rho)
        
        if plot and i % print_every == 0:
            print(f"Iteration {i}: delta = {delta}")

        if delta < tolerance or relative_error < tolerance:
            print(f"Converged after {i} iterations (delta = {delta})")
            if plot:
                plt.plot_end_SR_onetype(zbins, rho, muloc, ax)
            return zbins, rho

    print(f"Not converged after {i} iterations (delta = {delta})")
    return None, None


def minimise_SR_twotype(model_H, model_O, zbins, muloc_H, muloc_O, input_bins=335,
                        plot=True, maxiter=100000, alpha_initial=0.000001, 
                        alpha_updates=None, initial_guess=0.04,
                        print_every=1000, plot_every=1000, tolerance=1e-5,
                        output_dict=False):
    """
    Calculate the density profile with neural DFT using a standard Picard iteration.

    Parameters:
    - model (tf.keras.Model): The Keras model to be used for the calculation of the 
                              one-body direct correlation function.
    - profiles (np.recarray): A numpy structured array which must contain the keys 
                              'xbins' (planar position coordinate) and 'muloc' 
                              (local chemical potential). If 'rho' is given, it 
                              is interpreted as the reference density profile for 
                              comparison, e.g., obtained from simulation.
    - plot (bool): Toggle interactive plotting.
    - maxiter (int): Maximum number of Picard steps.
    - alpha_initial (float): Initial value for the relaxation parameter alpha.
    - alpha_updates (dict): Dictionary of iteration thresholds and corresponding 
                            alpha values to update alpha during iterations.
    - initial_guess (float): Initial guess for the density profile.

    Returns:
    - tuple: z coordinates and density profile.
    """
    
    # setting up grid
    rho_H_new = np.zeros_like(zbins)
    rho_O_new = np.zeros_like(zbins)
    validH = np.isfinite(muloc_H) 
    validO = np.isfinite(muloc_O)
    rho_H = initial_guess * np.ones_like(zbins)
    rho_O = initial_guess * np.ones_like(zbins)
    log_rho_H_new = np.zeros_like(zbins)
    log_rho_O_new = np.zeros_like(zbins)
    log_rho_H = np.zeros_like(zbins)
    log_rho_O = np.zeros_like(zbins)
    log_rho_H[validH] = np.log(initial_guess)
    log_rho_O[validO] = np.log(initial_guess)
    log_rho_H[~validH] = -np.inf
    log_rho_O[~validO] = -np.inf
    


    # Picard iteration parameter
    alpha = alpha_initial
    if alpha_updates is None:
        alpha_updates = alpha_updates_default_twotype
    
    if plot:
        fig, ax = plt.configure_plot(zbins)
        color_count = 0
  
    for i in range(maxiter + 1):
        if i in alpha_updates:
            alpha = alpha_updates[i]
        
        
        if plot and i % plot_every == 0:
            plt.plot_interactive_SR_twotype(fig, ax, zbins, rho_H, rho_O, muloc_H, muloc_O, color_count)
            color_count += 1
            
        # correlation from trained SR model
        c1_H_pred, c1_O_pred = neural.c1_twotype(model_H, model_O, rho_H, rho_O, input_bins, return_c2=False, output_dict=output_dict)
        
        # update density
        log_rho_H_new[validH] = muloc_H[validH]  + c1_H_pred[validH]
        log_rho_O_new[validO] = muloc_O[validO]  + c1_O_pred[validO]
        log_rho_H_new[~validH] = -np.inf
        log_rho_O_new[~validO] = -np.inf
        rho_H_new = np.exp(log_rho_H_new)
        rho_O_new = np.exp(log_rho_O_new)
        log_rho_H = (1 - alpha) * log_rho_H + alpha * log_rho_H_new
        log_rho_O = (1 - alpha) * log_rho_O + alpha * log_rho_O_new
        rho_H = np.exp(log_rho_H)
        rho_O = np.exp(log_rho_O)
        
        
        delta_H = np.max(np.abs(rho_H_new - rho_H))
        delta_O = np.max(np.abs(rho_O_new - rho_O))
        delta = max(delta_H, delta_O)
        
        if np.isnan(delta):
            print("Not converged: delta is NaN")
            return  None, None, None

        relative_error = delta / max(np.max(rho_O), np.max(rho_H))
        
        if i % print_every == 0:
            print(f"Iteration {i}: delta = {delta}")

        if delta < tolerance or relative_error < tolerance:
            print(f"Converged after {i} iterations (delta = {delta})")
            if plot:
                plt.plot_end_SR_twotype(zbins, rho_H, rho_O, muloc_H, muloc_O, ax)
            return zbins, rho_H, rho_O
        
    print(f"Not converged after {maxiter} iterations (delta = {delta})")
    return None, None, None #zbins, best_rho_H, best_rho_O


def mu_correction(q, kappa_inv, temp):
    prefactor = const.elementary_charge**2 /(4 * const.pi * const.epsilon_0 * 1e-10 )
    beta = 1/ (const.Boltzmann * temp) 

    first = - q**2 / (kappa_inv * np.pi**0.5  )
    return prefactor*first*beta


def minimise_LR_twotype(model_H, model_O, zbins, muloc_H, muloc_O,
                        q_H, q_O, kappa_inv, temp, dielectric,
                        input_bins=667,
                        plot=True, maxiter=100000, alpha_initial=0.000001, 
                        alpha_updates=None, alpha_restr_updates=None, initial_guess=0.04,
                        print_every=1000, plot_every=1000, tolerance=1e-5,
                        tolerance_restr = 1e-3, output_dict=False):
    """
    Calculate the density profile with neural DFT using a standard Picard iteration 
    for two types of particles for long-range interactions.

    Parameters:
    - model (tf.keras.Model): The Keras model to be used for the calculation of the 
                              one-body direct correlation function.
    - profiles (np.recarray): A numpy structured array which must contain the keys 
                              'xbins' (planar position coordinate) and 'muloc' 
                              (local chemical potential). If 'rho' is given, it 
                              is interpreted as the reference density profile for 
                              comparison, e.g., obtained from simulation.
    - plot (bool): Toggle interactive plotting.
    - maxiter (int): Maximum number of Picard steps.
    - alpha_initial (float): Initial value for the relaxation parameter alpha.
    - alpha_updates (dict): Dictionary of iteration thresholds and corresponding 
                            alpha values to update alpha during iterations.
    - initial_guess (float): Initial guess for the density profile.
    - print_every (int): Print the iteration number every n steps.
    - plot_every (int): Update the plot every n steps.
    - tolerance (float): Convergence tolerance for rho.
    - tolerance_restr (float): Convergence tolerance for the restructuring potential.
    
    

    Returns:
    - tuple: z coordinates and density profile.
    """
    
    # setting up grid
    rho_H_new = np.zeros_like(zbins)
    rho_O_new = np.zeros_like(zbins)
    validH = np.isfinite(muloc_H) 
    validO = np.isfinite(muloc_O)
    rho_H = initial_guess * np.ones_like(zbins)
    rho_O = initial_guess * np.ones_like(zbins)
    log_rho_H_new = np.zeros_like(zbins)
    log_rho_O_new = np.zeros_like(zbins)
    log_rho_H = np.zeros_like(zbins)
    log_rho_O = np.zeros_like(zbins)
    log_rho_H[validH] = np.log(initial_guess)
    log_rho_O[validO] = np.log(initial_guess)
    log_rho_H[~validH] = -np.inf
    log_rho_O[~validO] = -np.inf
    prefactor_restructure = lmft.calculate_prefactor(temp, dielectric)
    delta_phi = np.zeros_like(zbins)
    mu_H_correction = np.zeros_like(zbins)
    mu_O_correction = np.zeros_like(zbins)
    kbins = lmft.compute_wave_numbers(len(zbins), zbins[1] - zbins[0])
    delta_restr = 1 # initial value for delta
    
    # chemical potential correction
    mu_H_correction = mu_correction(np.abs(q_H), kappa_inv, temp) * np.ones_like(zbins)
    mu_O_correction = mu_correction(np.abs(q_O), kappa_inv, temp) * np.ones_like(zbins) 
   
    # Picard iteration parameter
    alpha = alpha_initial
    alpha_restr = 0.01
    if alpha_updates is None:
        alpha_updates = alpha_updates_default_twotype
        
    if alpha_restr_updates is None:
        alpha_restr_updates = alpha_restr_updates_default
    
    if plot:
        fig, ax = plt.configure_4panels(zbins)
        color_count = 0
  
    for i in range(maxiter + 1):
        if i in alpha_updates:
            alpha = alpha_updates[i]
        if i in alpha_restr_updates:
            alpha_restr = alpha_restr_updates[i]
        
            
        # correlation from trained SR model
        c1_H_pred_SR, c1_O_pred_SR = neural.c1_twotype(model_H, model_O, rho_H, rho_O, input_bins, return_c2=False, output_dict=output_dict)
        
        
        c1_H_LR = c1_H_pred_SR - mu_H_correction + q_H * delta_phi
        c1_O_LR = c1_O_pred_SR - mu_O_correction + q_O * delta_phi    
        
        # update density
        log_rho_H_new[validH] = muloc_H[validH]  + c1_H_LR[validH]
        log_rho_O_new[validO] = muloc_O[validO]  + c1_O_LR[validO]
        log_rho_H_new[~validH] = -np.inf
        log_rho_O_new[~validO] = -np.inf
        rho_H_new = np.exp(log_rho_H_new)
        rho_O_new = np.exp(log_rho_O_new)
        log_rho_H = (1 - alpha) * log_rho_H + alpha * log_rho_H_new
        log_rho_O = (1 - alpha) * log_rho_O + alpha * log_rho_O_new
        rho_H = np.exp(log_rho_H)
        rho_O = np.exp(log_rho_O)




        #if delta_restr > tolerance_restr:
        charge_density = rho_O * q_O + rho_H * q_H
        kbins, n_k = lmft.fourier_transform(zbins, charge_density, kbins)
        delta_phi_new = - lmft.restructure_electrostatic_potential(n_k, kbins, zbins, kappa_inv) * prefactor_restructure
        
        delta_H = np.max(np.abs(rho_H_new - rho_H))
        delta_O = np.max(np.abs(rho_O_new - rho_O))
        delta = max(delta_H, delta_O)
        
        
        
        
        delta_restr = np.max(np.abs(delta_phi_new - delta_phi))
        if delta < 1e-2 and delta_restr > tolerance_restr:
            delta_phi =  (1 - alpha_restr) * delta_phi + alpha_restr * delta_phi_new
        else :
            delta_phi = delta_phi_new
        
        
        if np.isnan(delta):
            print("Not converged: delta is NaN")
            return  None, None, None

        #relative_error = delta / max(np.max(rho_O), np.max(rho_H))
        
        if plot and i % plot_every == 0:
            charge_density = rho_O * q_O + rho_H * q_H
            kbins, n_k = lmft.fourier_transform(zbins, charge_density, kbins)
            delta_phi_temp = -lmft.restructure_electrostatic_potential(n_k, kbins, zbins, kappa_inv) * prefactor_restructure
            plt.plot_interactive_4panels(fig, ax, zbins, rho_H, rho_O,
                                         charge_density, delta_phi_temp,
                                         muloc_H, muloc_O, color_count)
            color_count += 1

        if i % print_every == 0:
            print(f"Iteration {i}: delta_rho = {delta:.7f}, delta_restr = {delta_restr:.7f}")


        if delta < tolerance and delta_restr < tolerance_restr:
            print(f"=====================================================")
            print(f"Converged after {i} iterations")
            print(f"Final delta = {delta:.7f} [AA^-3]")
            print(f"Final delta_restr = {delta_restr:.7f} [kT/e]")
            
            if plot:
                plt.plot_end_4panels(zbins, rho_H, rho_O, muloc_H, muloc_O, ax)
            return zbins, rho_H, rho_O
        
    print(f"Not converged after {maxiter} iterations (delta = {delta:.7f})")
    return None, None, None 

def calculate_charge_density(rho_new, charge, L, zbins):
    total_number_particle = np.trapz(rho_new, zbins) 
    total_charge = total_number_particle * charge
    background_charge_density = total_charge / L
    n_z = rho_new * charge - background_charge_density
    return n_z

def update_electrostatic_potential(n_z, zbins, dz, kappa_inv, prefactor):
    N = len(zbins)
    kbins = lmft.compute_wave_numbers(N, dz)
    kbins, n_k = lmft.fourier_transform(zbins, n_z, kbins)
    lmf_z = lmft.restructure_electrostatic_potential(n_k, kbins, zbins, kappa_inv) * prefactor
    return lmf_z


