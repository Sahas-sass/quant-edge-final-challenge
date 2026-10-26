"""
backtest_engine.py
Layer 5 - Model Validation & Regulatory Backtesting
Out-of-sample backtesting of VaR models on the Conservative Endowment Portfolio:
  1. Kupiec Proportion-of-Failures (POF) Unconditional Coverage Test
  2. Christoffersen Markov Independence Test (Violation Clustering)
  3. Christoffersen Conditional Coverage (Joint) Test
  4. Basel Committee Traffic Light Framework (Green, Yellow, Red Zones)

Partitioning:
  - In-Sample Calibration: 2007-01-01 to 2019-12-31 (GFC & Post-Crisis Recovery)
  - Out-of-Sample Testing: 2020-01-01 to 2026-10-01 (COVID Crash, 2022 Inflation/Rate Hike, 2023-2026)
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

TICKERS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]
CONFIDENCE_LEVELS = [0.95, 0.99]
SPLIT_DATE = "2020-01-01"


def kupiec_pof_test(violations, total_obs, alpha=0.99):
    """
    Kupiec Proportion of Failures (POF) Likelihood Ratio test.
    H0: True violation probability equals (1 - alpha).
    """
    p = 1.0 - alpha  # Theoretical expected violation probability (e.g. 0.01 for 99% VaR)
    x = int(violations)
    N = int(total_obs)

    if x == 0:
        lr_pof = -2.0 * np.log((1.0 - p) ** N)
    else:
        p_hat = x / N
        lr_pof = -2.0 * (
            (N - x) * np.log(1.0 - p) + x * np.log(p)
            - (N - x) * np.log(1.0 - p_hat) - x * np.log(p_hat)
        )
    lr_pof = max(0.0, lr_pof)
    p_val = 1.0 - stats.chi2.cdf(lr_pof, df=1)
    return lr_pof, p_val


def christoffersen_independence_test(hit_sequence):
    """
    Christoffersen Markov independence test.
    Tests whether violations occur independently or cluster in time.
    H0: Violations are independent (pi_01 = pi_11).
    """
    hits = np.array(hit_sequence, dtype=int)
    n00 = n01 = n10 = n11 = 0

    for t in range(len(hits) - 1):
        if hits[t] == 0 and hits[t + 1] == 0:
            n00 += 1
        elif hits[t] == 0 and hits[t + 1] == 1:
            n01 += 1
        elif hits[t] == 1 and hits[t + 1] == 0:
            n10 += 1
        elif hits[t] == 1 and hits[t + 1] == 1:
            n11 += 1

    pi0 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    pi1 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0
    pi = (n01 + n11) / (n00 + n01 + n10 + n11) if (n00 + n01 + n10 + n11) > 0 else 0.0

    if pi == 0 or pi == 1 or (n01 == 0 and n11 == 0):
        return 0.0, 1.0

    ll_null = (n00 + n10) * np.log(1.0 - pi + 1e-12) + (n01 + n11) * np.log(pi + 1e-12)
    ll_alt = 0.0
    if n00 > 0: ll_alt += n00 * np.log(1.0 - pi0 + 1e-12)
    if n01 > 0: ll_alt += n01 * np.log(pi0 + 1e-12)
    if n10 > 0: ll_alt += n10 * np.log(1.0 - pi1 + 1e-12)
    if n11 > 0: ll_alt += n11 * np.log(pi1 + 1e-12)

    lr_ind = -2.0 * (ll_null - ll_alt)
    lr_ind = max(0.0, lr_ind)
    p_val = 1.0 - stats.chi2.cdf(lr_ind, df=1)
    return lr_ind, p_val


def basel_traffic_light_zone(violations, total_obs, alpha=0.99):
    """
    Standard Basel Committee on Banking Supervision Traffic Light System.
    Normalized to a standard 250-day window for 99% VaR:
      - Green Zone: <= 4 violations (Model acceptable, no capital penalty)
      - Yellow Zone: 5 to 9 violations (Supervisory monitoring, capital penalty multiplier)
      - Red Zone: >= 10 violations (Model rejected, mandatory capital penalty)
    """
    scaled_v = violations * (250.0 / total_obs)
    if scaled_v <= 4.49:
        return "GREEN"
    elif scaled_v <= 9.49:
        return "YELLOW"
    else:
        return "RED"


def run_comprehensive_out_of_sample_backtest(returns_df, weights, split_date=SPLIT_DATE, alphas=CONFIDENCE_LEVELS):
    """
    Performs out-of-sample backtest across:
      1. Parametric (Normal) VaR
      2. Historical Simulation VaR
      3. Monte Carlo (Student-t) VaR
      4. Extreme Value Theory (EVT-POT) VaR
    """
    from portfolio_engine import compute_portfolio_returns
    from risk_engine import compute_parametric_var_es, compute_historical_var_es, compute_monte_carlo_var_es
    from evt_engine import compute_evt_pot_var_es, select_optimal_threshold

    port_returns = compute_portfolio_returns(returns_df, weights)
    port_losses = -port_returns

    # Split into In-Sample (Calibration) and Out-of-Sample (Test)
    train_returns = returns_df[returns_df.index < split_date]
    test_returns = returns_df[returns_df.index >= split_date]

    train_port_returns = port_returns[port_returns.index < split_date]
    test_port_returns = port_returns[port_returns.index >= split_date]

    train_losses = port_losses[port_losses.index < split_date]
    test_losses = port_losses[port_losses.index >= split_date]

    N_test = len(test_losses)

    # In-Sample Calibration of Models
    opt_thresh_row, _ = select_optimal_threshold(train_losses)

    backtest_records = []
    trajectories = {}

    for a in alphas:
        target_violation_rate = 1.0 - a
        expected_v = N_test * target_violation_rate

        # 1. Parametric
        v_param, e_param = compute_parametric_var_es(train_port_returns, alpha=a)
        # 2. Historical
        v_hist, e_hist = compute_historical_var_es(train_losses, alpha=a)
        # 3. Monte Carlo (pass only TICKERS)
        v_mc, e_mc = compute_monte_carlo_var_es(train_returns[TICKERS], weights, alpha=a, n_sim=25000, df=5.0)
        # 4. EVT-POT
        v_evt, e_evt, _ = compute_evt_pot_var_es(train_losses, alpha=a, optimal_threshold_row=opt_thresh_row)

        models = [
            ("Parametric (Normal) VaR", v_param, e_param),
            ("Historical Simulation VaR", v_hist, e_hist),
            ("Monte Carlo (Student-t) VaR", v_mc, e_mc),
            ("Extreme Value Theory (EVT-POT) VaR", v_evt, e_evt)
        ]

        for m_name, var_val, es_val in models:
            hits = (test_losses > var_val).astype(int)
            v_count = int(hits.sum())
            v_rate = v_count / N_test

            lr_pof, p_pof = kupiec_pof_test(v_count, N_test, alpha=a)
            lr_ind, p_ind = christoffersen_independence_test(hits)
            lr_cc = lr_pof + lr_ind
            p_cc = 1.0 - stats.chi2.cdf(lr_cc, df=2)
            zone = basel_traffic_light_zone(v_count, N_test, alpha=a)

            # Realized Shortfall on Violations
            realized_es = float(test_losses[hits == 1].mean()) if v_count > 0 else 0.0
            es_bias_pct = ((realized_es - es_val) / es_val) * 100.0 if es_val > 0 else 0.0

            backtest_records.append({
                "Confidence": f"{int(a*100)}%",
                "Model": m_name,
                "Test_Obs": N_test,
                "VaR_Threshold": var_val,
                "Violations": v_count,
                "Expected_Violations": round(expected_v, 1),
                "Violation_Rate": v_rate,
                "Kupiec_pVal": p_pof,
                "Christoffersen_pVal": p_ind,
                "Joint_CC_pVal": p_cc,
                "Basel_Zone": zone,
                "Model_ES": es_val,
                "Realized_ES": realized_es,
                "ES_Bias_Pct": es_bias_pct
            })

            trajectories[(int(a*100), m_name)] = {
                "dates": test_losses.index,
                "losses": test_losses.values,
                "var_val": var_val,
                "hits": hits.values
            }

    df_backtest = pd.DataFrame(backtest_records)
    return df_backtest, trajectories, test_losses


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import download_and_clean_data
    from portfolio_engine import ENDOWMENT_WEIGHTS

    _, _, simple_ret, _ = download_and_clean_data()
    df_bt, trajs, _ = run_comprehensive_out_of_sample_backtest(simple_ret, ENDOWMENT_WEIGHTS)
    print("\n--- Out-of-Sample Backtesting Performance Summary (2020-2026) ---")
    cols_show = ["Confidence", "Model", "Violations", "Expected_Violations", "Violation_Rate", "Kupiec_pVal", "Basel_Zone", "ES_Bias_Pct"]
    print(df_bt[cols_show].to_string(index=False))
