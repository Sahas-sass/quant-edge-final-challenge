"""
risk_engine.py
Layer 2 - Value-at-Risk (VaR) & Layer 3 - Expected Shortfall (CVaR)
Implements and rigorously compares 3 VaR/ES methodologies:
  1. Historical Simulation (Non-parametric empirical loss distribution)
  2. Parametric / Variance-Covariance (Gaussian elliptical assumption)
  3. Monte Carlo Simulation (Multivariate Student-t copula/innovations, 25,000 paths)

Confidence Levels: 90%, 95%, 99%
Coherent Risk Measure Justification: Mathematical & economic rationale for CVaR over VaR.
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

TICKERS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]
CONFIDENCE_LEVELS = [0.90, 0.95, 0.99]


def compute_historical_var_es(losses, alpha=0.95):
    """
    Computes Historical Simulation VaR and Expected Shortfall (CVaR).
    Losses are defined as positive: L_t = -R_t.
    """
    var = np.percentile(losses, alpha * 100.0)
    tail_losses = losses[losses >= var]
    es = np.mean(tail_losses) if len(tail_losses) > 0 else var
    return var, es


def compute_parametric_var_es(returns, alpha=0.95):
    """
    Computes Parametric (Variance-Covariance / Gaussian) VaR and ES.
    Assumes returns ~ N(mu, sigma^2).
    Loss = -R ~ N(-mu, sigma^2).
    VaR_alpha = -mu + z_alpha * sigma
    ES_alpha = -mu + (phi(z_alpha) / (1 - alpha)) * sigma
    """
    mu = np.mean(returns)
    sigma = np.std(returns, ddof=1)
    z_alpha = stats.norm.ppf(alpha)
    var = -mu + z_alpha * sigma
    pdf_z = stats.norm.pdf(z_alpha)
    es = -mu + (pdf_z / (1.0 - alpha)) * sigma
    return var, es


def compute_monte_carlo_var_es(returns_matrix, weights, alpha=0.95, n_sim=25000, df=5.0, random_state=42):
    """
    Computes Monte Carlo Simulation VaR and ES using multivariate Student-t innovations
    to properly capture joint fat tails and heavy-tailed co-movements.
    """
    rng = np.random.default_rng(random_state)
    mu_vec = returns_matrix.mean().values
    cov_mat = returns_matrix.cov().values
    w_vec = np.array([weights[t] for t in returns_matrix.columns])

    # Cholesky decomposition of covariance matrix
    L = np.linalg.cholesky(cov_mat)

    # Generate multivariate standard normal samples
    z = rng.standard_normal((n_sim, len(w_vec)))

    # Scale by inverse chi-square for Student-t copula innovations
    if df is not None and df > 2:
        chi2 = rng.chisquare(df, size=(n_sim, 1))
        scale = np.sqrt(df / chi2)
        innovations = z * scale
    else:
        innovations = z

    # Correlated asset returns: R_sim = mu + L * innovations^T
    simulated_asset_returns = mu_vec + (innovations @ L.T)
    simulated_port_returns = simulated_asset_returns @ w_vec
    simulated_losses = -simulated_port_returns

    var = np.percentile(simulated_losses, alpha * 100.0)
    tail_losses = simulated_losses[simulated_losses >= var]
    es = np.mean(tail_losses) if len(tail_losses) > 0 else var
    return var, es


def evaluate_portfolio_risk_suite(returns_df, weights, alphas=CONFIDENCE_LEVELS, n_sim=25000):
    """
    Computes VaR and ES across all 3 methodologies and confidence levels.
    Returns:
      summary_df: Formatted DataFrame comparing methods side-by-side.
      full_dict: Raw numerical results dictionary.
    """
    w_vec = np.array([weights[t] for t in TICKERS])
    port_returns = returns_df[TICKERS].dot(w_vec)
    port_losses = -port_returns

    results = []
    full_dict = {}

    for a in alphas:
        conf_pct = int(a * 100)

        # 1. Historical Simulation
        var_hist, es_hist = compute_historical_var_es(port_losses, alpha=a)

        # 2. Parametric (Normal)
        var_param, es_param = compute_parametric_var_es(port_returns, alpha=a)

        # 3. Monte Carlo Simulation (Student-t, df=5)
        var_mc, es_mc = compute_monte_carlo_var_es(returns_df[TICKERS], weights, alpha=a, n_sim=n_sim, df=5.0)

        full_dict[f"VaR_Hist_{conf_pct}"] = var_hist
        full_dict[f"ES_Hist_{conf_pct}"] = es_hist
        full_dict[f"VaR_Param_{conf_pct}"] = var_param
        full_dict[f"ES_Param_{conf_pct}"] = es_param
        full_dict[f"VaR_MC_{conf_pct}"] = var_mc
        full_dict[f"ES_MC_{conf_pct}"] = es_mc

        results.append({
            "Confidence_Level": f"{conf_pct}%",
            "Historical_VaR": var_hist,
            "Parametric_VaR": var_param,
            "Monte_Carlo_VaR": var_mc,
            "Historical_ES": es_hist,
            "Parametric_ES": es_param,
            "Monte_Carlo_ES": es_mc,
            "Fat_Tail_Spread_VaR_MC_vs_Param": ((var_mc - var_param) / var_param) * 100.0,
            "Fat_Tail_Spread_ES_MC_vs_Param": ((es_mc - es_param) / es_param) * 100.0
        })

    summary_df = pd.DataFrame(results).set_index("Confidence_Level")
    return summary_df, full_dict, port_returns


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import download_and_clean_data
    from portfolio_engine import ENDOWMENT_WEIGHTS

    _, _, simple_ret, _ = download_and_clean_data()
    summary_df, _, _ = evaluate_portfolio_risk_suite(simple_ret, ENDOWMENT_WEIGHTS)
    print("\n--- Conservative Endowment Portfolio: VaR & ES Across 3 Methodologies ---")
    cols_show = ["Historical_VaR", "Parametric_VaR", "Monte_Carlo_VaR", "Historical_ES", "Parametric_ES", "Monte_Carlo_ES", "Fat_Tail_Spread_ES_MC_vs_Param"]
    print(summary_df[cols_show].to_string())
