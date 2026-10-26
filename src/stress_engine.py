"""
stress_engine.py
Layer 6 - From Metrics to Decisions: Risk Budgeting & Crisis Stress Testing
Applied to The Serendib University Endowment Fund (USD 10 Million Mandate).

Components:
  1. Risk Budgeting: Marginal VaR, Component VaR, and % Risk Contribution for asset sizing.
  2. Historical Crisis Stress Testing:
     - 2008 Global Financial Crisis (Lehman Shock)
     - March 2020 COVID Liquidity Crash
     - 2022 Fed Rate-Hiking & Stagflation Drawdown
  3. Custom Hypothetical Stress Scenario:
     - "2026-2027 Geopolitical Energy Shock & Sovereign Debt Liquidity Freeze"
  4. Dollar Loss Attribution on the USD 10 Million Portfolio.
"""

import os
import numpy as np
import pandas as pd

TICKERS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]
ENDOWMENT_CAPITAL = 10_000_000.0  # USD 10 Million

# Historical Crisis Period Windows
HISTORICAL_CRISIS_WINDOWS = {
    "2008_GFC_Lehman_Crash": {
        "Name": "2008 Global Financial Crisis (Lehman Shock)",
        "Start": "2008-09-01",
        "End": "2008-11-20",
        "Description": "Lehman Brothers bankruptcy, interbank liquidity freeze, severe equity sell-off."
    },
    "2020_COVID_Crash": {
        "Name": "March 2020 COVID-19 Liquidity Crash",
        "Start": "2020-02-19",
        "End": "2020-03-23",
        "Description": "Global pandemic lockdowns, dash-for-cash across asset classes, rapid market drop."
    },
    "2022_Fed_Rate_Shock": {
        "Name": "2022 Fed Rate-Hiking & Stagflation Drawdown",
        "Start": "2022-01-03",
        "End": "2022-10-14",
        "Description": "Aggressive 500bps monetary tightening, simultaneous breakdown of stock/bond correlation."
    }
}

# Team-Designed Custom Hypothetical Shock Vector (%)
CUSTOM_STAGFLATION_SHOCK = {
    "Name": "2026-27 Geopolitical Oil Shock & Sovereign Liquidity Freeze",
    "Description": "Strait of Hormuz disruption spikes crude +60%, stagflation persists, Fed holds rates high, tech valuation compresses, gold acts as sovereign reserve hedge.",
    "Asset_Shocks": {
        "SPY": -0.250,   # -25% US Large-Cap
        "EFA": -0.280,   # -28% Developed Int'l (Energy import dependency)
        "EEM": -0.350,   # -35% Emerging Markets (Strong USD & high import bills)
        "AGG": -0.120,   # -12% Sovereign Bonds (Yields spike 150bps)
        "GLD": +0.220,   # +22% Gold (Safe haven & reserve de-dollarization)
        "XLE": +0.380,   # +38% Energy Sector (Crude surge windfall)
        "XLK": -0.320    # -32% Tech Growth (High discount rates & multiples compression)
    }
}


def compute_risk_budgeting(returns_df, weights, alpha=0.99):
    """
    Computes Marginal VaR, Component VaR, and % Contribution to Total Portfolio VaR.
    Decomposes the total portfolio risk down to individual asset positions.
    """
    cov_mat = returns_df[TICKERS].cov().values
    w_vec = np.array([weights[t] for t in TICKERS])
    
    port_var = w_vec.T @ cov_mat @ w_vec
    port_vol = np.sqrt(port_var)
    z_alpha = stats_norm_ppf = 2.3263  # 99% z-score

    # Total Portfolio Parametric VaR (daily)
    port_var_daily = z_alpha * port_vol

    # Marginal VaR = (Cov * w) / port_vol * z_alpha
    cov_w = cov_mat @ w_vec
    marginal_var = (cov_w / port_vol) * z_alpha

    # Component VaR = w_i * Marginal_VaR_i
    component_var = w_vec * marginal_var

    # % Contribution to VaR = Component_VaR / Total_VaR
    pct_contrib = (component_var / port_var_daily) * 100.0

    records = []
    for i, t in enumerate(TICKERS):
        dollar_exposure = weights[t] * ENDOWMENT_CAPITAL
        dollar_cvar = component_var[i] * ENDOWMENT_CAPITAL
        records.append({
            "Ticker": t,
            "Weight": weights[t],
            "Dollar_Allocation": dollar_exposure,
            "Marginal_VaR_Daily": marginal_var[i],
            "Component_VaR_Daily": component_var[i],
            "Component_VaR_Dollar_99": dollar_cvar,
            "Pct_Risk_Contribution": pct_contrib[i]
        })

    df_budget = pd.DataFrame(records).set_index("Ticker")
    return df_budget, port_var_daily


def evaluate_historical_stress_scenarios(clean_prices, weights, capital=ENDOWMENT_CAPITAL):
    """
    Evaluates the exact realized historical performance and peak-to-trough drawdowns
    during historical crisis episodes.
    """
    w_vec = np.array([weights[t] for t in TICKERS])
    records = []

    for key, info in HISTORICAL_CRISIS_WINDOWS.items():
        sub_prices = clean_prices.loc[info["Start"]:info["End"], TICKERS]
        if len(sub_prices) < 2:
            continue

        # Cumulative asset returns over the crisis window
        asset_cum_ret = (sub_prices.iloc[-1] / sub_prices.iloc[0]) - 1.0
        # Portfolio return over the window
        port_cum_ret = float(np.sum(asset_cum_ret.values * w_vec))
        dollar_loss = port_cum_ret * capital

        # Maximum daily drawdown during the crisis window
        sub_returns = sub_prices.pct_change().dropna()
        port_daily_ret = sub_returns.dot(w_vec)
        wealth = (1.0 + port_daily_ret).cumprod()
        peak = wealth.cummax()
        max_dd_during = float(((wealth - peak) / peak).min())

        row = {
            "Crisis_Scenario": info["Name"],
            "Window": f"{info['Start']} to {info['End']}",
            "Trading_Days": len(sub_prices),
            "Cumulative_Return_Pct": port_cum_ret * 100.0,
            "Max_Drawdown_Pct": max_dd_during * 100.0,
            "Dollar_Impact_USD": dollar_loss,
            "Capital_Remaining_USD": capital + dollar_loss
        }
        # Add asset-specific cumulative returns
        for t in TICKERS:
            row[f"{t}_Return"] = asset_cum_ret[t] * 100.0

        records.append(row)

    return pd.DataFrame(records).set_index("Crisis_Scenario")


def evaluate_custom_hypothetical_stress(weights, capital=ENDOWMENT_CAPITAL, scenario=CUSTOM_STAGFLATION_SHOCK):
    """
    Applies the custom team-designed stress shock to the portfolio and computes asset-level attribution.
    """
    shocks = scenario["Asset_Shocks"]
    w_vec = np.array([weights[t] for t in TICKERS])
    shock_vec = np.array([shocks[t] for t in TICKERS])

    port_loss_pct = float(np.sum(w_vec * shock_vec))
    total_dollar_impact = port_loss_pct * capital

    attribution = []
    for t in TICKERS:
        w_i = weights[t]
        s_i = shocks[t]
        impact_pct = w_i * s_i
        dollar_impact = impact_pct * capital
        attribution.append({
            "Ticker": t,
            "Weight": w_i,
            "Asset_Shock_Pct": s_i * 100.0,
            "Portfolio_Contribution_Pct": impact_pct * 100.0,
            "Dollar_Impact_USD": dollar_impact
        })

    df_attr = pd.DataFrame(attribution).set_index("Ticker")
    summary = {
        "Scenario_Name": scenario["Name"],
        "Description": scenario["Description"],
        "Total_Portfolio_Return_Pct": port_loss_pct * 100.0,
        "Total_Dollar_Impact_USD": total_dollar_impact,
        "Capital_Post_Stress_USD": capital + total_dollar_impact
    }
    return summary, df_attr


def compare_stress_across_portfolios(clean_prices, capital=ENDOWMENT_CAPITAL):
    """
    Compares crisis drawdown and dollar losses across:
      1. Conservative Endowment Portfolio
      2. Standard 60/40 Portfolio
      3. Equal Weight (1/N) Portfolio
    """
    from portfolio_engine import ENDOWMENT_WEIGHTS

    ports = {
        "Conservative_Endowment": ENDOWMENT_WEIGHTS,
        "Standard_60_40": {"SPY": 0.60, "AGG": 0.40, "EFA": 0.0, "EEM": 0.0, "GLD": 0.0, "XLE": 0.0, "XLK": 0.0},
        "Equal_Weight_1_N": {t: 1.0 / len(TICKERS) for t in TICKERS}
    }

    comparison_records = []
    for p_name, w in ports.items():
        hist_df = evaluate_historical_stress_scenarios(clean_prices, w, capital=capital)
        custom_sum, _ = evaluate_custom_hypothetical_stress(w, capital=capital)

        for crisis in hist_df.index:
            comparison_records.append({
                "Portfolio": p_name,
                "Crisis": crisis,
                "Cumulative_Return_Pct": hist_df.loc[crisis, "Cumulative_Return_Pct"],
                "Max_Drawdown_Pct": hist_df.loc[crisis, "Max_Drawdown_Pct"],
                "Dollar_Impact_USD": hist_df.loc[crisis, "Dollar_Impact_USD"]
            })

        comparison_records.append({
            "Portfolio": p_name,
            "Crisis": custom_sum["Scenario_Name"],
            "Cumulative_Return_Pct": custom_sum["Total_Portfolio_Return_Pct"],
            "Max_Drawdown_Pct": custom_sum["Total_Portfolio_Return_Pct"],  # instantaneous shock
            "Dollar_Impact_USD": custom_sum["Total_Dollar_Impact_USD"]
        })

    return pd.DataFrame(comparison_records)


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import download_and_clean_data
    from portfolio_engine import ENDOWMENT_WEIGHTS

    clean_p, _, simple_r, _ = download_and_clean_data()
    df_budget, port_var_daily = compute_risk_budgeting(simple_r, ENDOWMENT_WEIGHTS)
    print("\n--- Conservative Endowment Portfolio Risk Budgeting (99% VaR) ---")
    print(df_budget[["Weight", "Dollar_Allocation", "Component_VaR_Dollar_99", "Pct_Risk_Contribution"]].to_string())

    print("\n--- Historical Crisis Stress Scenarios on USD 10M Endowment ---")
    hist_df = evaluate_historical_stress_scenarios(clean_p, ENDOWMENT_WEIGHTS)
    print(hist_df[["Window", "Cumulative_Return_Pct", "Max_Drawdown_Pct", "Dollar_Impact_USD"]].to_string())

    print("\n--- Custom 2026-27 Geopolitical Oil Shock & Sovereign Liquidity Freeze ---")
    custom_sum, custom_attr = evaluate_custom_hypothetical_stress(ENDOWMENT_WEIGHTS)
    print(f"Total Portfolio Return: {custom_sum['Total_Portfolio_Return_Pct']:.2f}% | Dollar Loss: ${custom_sum['Total_Dollar_Impact_USD']:,.2f}")
    print(custom_attr[["Weight", "Asset_Shock_Pct", "Portfolio_Contribution_Pct", "Dollar_Impact_USD"]].to_string())
