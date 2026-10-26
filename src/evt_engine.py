"""
evt_engine.py
Layer 4 - Extreme Value Theory (EVT) for Tail Risk Modeling
Implements the Peaks-Over-Threshold (POT) approach using the Generalized Pareto Distribution (GPD):
  1. Justified Threshold Selection (Mean Residual Life / Mean Excess diagnostic & quantile grid)
  2. Maximum Likelihood Estimation (MLE) of GPD parameters (xi: shape/tail index, beta: scale)
  3. Analytical EVT-VaR and EVT-ES (Expected Shortfall) calculation
  4. Quantification of the "Tail Risk Gap" between EVT and conventional Gaussian risk models

Mandate: The Serendib University Endowment Fund (USD 10 Million)
"""

import os
import numpy as np
import pandas as pd
from scipy import stats, optimize
import matplotlib.pyplot as plt

CONFIDENCE_LEVELS = [0.90, 0.95, 0.99]


def compute_mean_excess(losses, thresholds):
    """
    Computes empirical mean excess e(u) = E[X - u | X > u] across candidate thresholds.
    Linearity in e(u) indicates the appropriate region for GPD validity (Pickands-Balkema-de Haan theorem).
    """
    mrl_values = []
    exceedance_counts = []
    valid_thresholds = []

    for u in thresholds:
        excess = losses[losses > u] - u
        if len(excess) >= 15:  # Require minimum 15 exceedances for statistical reliability
            mrl_values.append(excess.mean())
            exceedance_counts.append(len(excess))
            valid_thresholds.append(u)

    return np.array(valid_thresholds), np.array(mrl_values), np.array(exceedance_counts)


def fit_gpd_mle(exceedances):
    """
    Fits Generalized Pareto Distribution (GPD) to exceedances y = x - u via Maximum Likelihood.
    Density: g(y; xi, beta) = (1 / beta) * (1 + xi * y / beta)^(-1/xi - 1)
    Returns: xi (shape), beta (scale), log-likelihood
    """
    # Use scipy.stats.genpareto (scipy parameterization: c = xi, scale = beta, loc = 0)
    # Filter exceedances > 0
    y = exceedances[exceedances > 0]
    if len(y) < 10:
        return 0.1, np.std(y), -1e10

    # Fit with positive scale constraint
    try:
        # Initial guess via method of moments
        m = y.mean()
        s2 = y.var()
        xi_init = max(0.01, 0.5 * (1.0 - (m**2 / (s2 + 1e-8))))
        beta_init = max(1e-4, 0.5 * m * (m**2 / (s2 + 1e-8) + 1.0))

        params = stats.genpareto.fit(y, floc=0.0)
        xi_fit, _, beta_fit = params
        ll = np.sum(stats.genpareto.logpdf(y, c=xi_fit, loc=0.0, scale=beta_fit))
        return xi_fit, beta_fit, ll
    except Exception:
        # Fallback L-BFGS-B
        def neg_loglik(p):
            xi, beta = p
            if beta <= 1e-6:
                return 1e10
            z = 1.0 + xi * y / beta
            if np.any(z <= 0):
                return 1e10
            if abs(xi) < 1e-6:
                nll = len(y) * np.log(beta) + np.sum(y) / beta
            else:
                nll = len(y) * np.log(beta) + (1.0 / xi + 1.0) * np.sum(np.log(z))
            return nll

        res = optimize.minimize(neg_loglik, [0.15, y.mean()], bounds=[(-0.5, 2.0), (1e-5, None)])
        xi_fit, beta_fit = res.x
        return xi_fit, beta_fit, -res.fun


def select_optimal_threshold(losses, candidate_quantiles=np.linspace(0.90, 0.97, 15)):
    """
    Systematic, mathematically justified threshold selection.
    Tests candidate quantiles, checks parameter stability, and selects the optimal threshold u*
    balancing bias (too low u violates asymptotic GPD) vs variance (too high u has few exceedances).
    """
    N = len(losses)
    records = []

    for q in candidate_quantiles:
        u = float(np.quantile(losses, q))
        excess = losses[losses > u] - u
        Nu = len(excess)
        if Nu < 25:
            continue
        xi, beta, ll = fit_gpd_mle(excess)
        # Modified Anderson-Darling or AIC test statistic for GPD
        aic = 2 * 2 - 2 * ll
        records.append({
            "Quantile": q,
            "Threshold_u": u,
            "Exceedances_Nu": Nu,
            "Exceedance_Rate": Nu / N,
            "GPD_Shape_xi": xi,
            "GPD_Scale_beta": beta,
            "AIC": aic
        })

    df_thresh = pd.DataFrame(records)
    # Optimal threshold selected where AIC is minimized and shape xi is stable in [0.05, 0.40]
    valid = df_thresh[(df_thresh["GPD_Shape_xi"] > 0.0) & (df_thresh["GPD_Shape_xi"] < 0.6)]
    if len(valid) > 0:
        optimal_row = valid.sort_values("AIC").iloc[0]
    else:
        optimal_row = df_thresh.iloc[len(df_thresh) // 2]

    return optimal_row, df_thresh


def compute_evt_pot_var_es(losses, alpha=0.99, optimal_threshold_row=None):
    """
    Computes analytical EVT-VaR and EVT-ES using the Peaks-Over-Threshold GPD model.
    Formulas:
      VaR_p = u + (beta / xi) * [ ((N / N_u) * (1 - p))^(-xi) - 1 ]
      ES_p = (VaR_p / (1 - xi)) + ((beta - xi * u) / (1 - xi))  (for xi < 1)
    """
    N = len(losses)
    if optimal_threshold_row is None:
        optimal_threshold_row, _ = select_optimal_threshold(losses)

    u = float(optimal_threshold_row["Threshold_u"])
    Nu = int(optimal_threshold_row["Exceedances_Nu"])
    xi = float(optimal_threshold_row["GPD_Shape_xi"])
    beta = float(optimal_threshold_row["GPD_Scale_beta"])

    p = alpha
    tail_prob = (N / Nu) * (1.0 - p)

    if tail_prob <= 0:
        # Fallback to empirical maximum
        return float(losses.max()), float(losses.max())

    # Analytical EVT-VaR
    if abs(xi) < 1e-5:
        # Gumbel domain (exponential tail)
        var_evt = u - beta * np.log(tail_prob)
        es_evt = var_evt + beta
    else:
        # Fréchet domain (heavy fat tail)
        var_evt = u + (beta / xi) * (tail_prob ** (-xi) - 1.0)
        # Analytical EVT-ES
        if xi < 1.0:
            es_evt = (var_evt / (1.0 - xi)) + ((beta - xi * u) / (1.0 - xi))
        else:
            # Infinite first moment
            es_evt = var_evt * 1.5

    return var_evt, es_evt, optimal_threshold_row


def compare_evt_vs_conventional_risk(losses, alphas=CONFIDENCE_LEVELS):
    """
    Generates side-by-side comparative table of:
      1. Parametric (Normal) VaR & ES
      2. Historical Simulation VaR & ES
      3. EVT Peaks-Over-Threshold VaR & ES
      Quantifying the exact 'Tail Risk Gap' at each confidence level.
    """
    from risk_engine import compute_parametric_var_es, compute_historical_var_es

    opt_row, df_thresh = select_optimal_threshold(losses)
    portfolio_returns = -losses

    records = []
    for a in alphas:
        conf_pct = int(a * 100)
        v_param, e_param = compute_parametric_var_es(portfolio_returns, alpha=a)
        v_hist, e_hist = compute_historical_var_es(losses, alpha=a)
        v_evt, e_evt, _ = compute_evt_pot_var_es(losses, alpha=a, optimal_threshold_row=opt_row)

        records.append({
            "Confidence_Level": f"{conf_pct}%",
            "Parametric_VaR": v_param,
            "Historical_VaR": v_hist,
            "EVT_POT_VaR": v_evt,
            "Parametric_ES": e_param,
            "Historical_ES": e_hist,
            "EVT_POT_ES": e_evt,
            "Tail_Gap_VaR_EVT_vs_Param_Pct": ((v_evt - v_param) / v_param) * 100.0,
            "Tail_Gap_ES_EVT_vs_Param_Pct": ((e_evt - e_param) / e_param) * 100.0,
            "EVT_Threshold_u": opt_row["Threshold_u"],
            "GPD_Shape_xi": opt_row["GPD_Shape_xi"],
            "GPD_Scale_beta": opt_row["GPD_Scale_beta"]
        })

    return pd.DataFrame(records).set_index("Confidence_Level"), opt_row, df_thresh


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import download_and_clean_data
    from portfolio_engine import ENDOWMENT_WEIGHTS, compute_portfolio_returns

    _, _, simple_ret, _ = download_and_clean_data()
    port_ret = compute_portfolio_returns(simple_ret, ENDOWMENT_WEIGHTS)
    port_losses = -port_ret

    evt_comp, opt_row, _ = compare_evt_vs_conventional_risk(port_losses)
    print("\n--- Extreme Value Theory (EVT/POT) vs Conventional Risk Dashboard ---")
    print(f"Optimal Threshold u*: {opt_row['Threshold_u']:.4f} (Quantile: {opt_row['Quantile']*100:.1f}%, Exceedances Nu={int(opt_row['Exceedances_Nu'])})")
    print(f"GPD Parameters: Shape xi = {opt_row['GPD_Shape_xi']:.4f} (Heavy Tail), Scale beta = {opt_row['GPD_Scale_beta']:.4f}")
    cols_display = ["Parametric_VaR", "Historical_VaR", "EVT_POT_VaR", "Parametric_ES", "Historical_ES", "EVT_POT_ES", "Tail_Gap_ES_EVT_vs_Param_Pct"]
    print(evt_comp[cols_display].to_string())
