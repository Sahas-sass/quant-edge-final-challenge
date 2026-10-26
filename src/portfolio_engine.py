"""
portfolio_engine.py
Layer 1 - Foundations: Modern Portfolio Theory, Markowitz Efficient Frontier,
CAPM Analytics, and Institutional Performance KPIs.

Mandate: The Serendib University Endowment Fund (USD 10 Million)
Target: Balance capital preservation, income, and real growth while avoiding large drawdowns.
"""

import os
import numpy as np
import pandas as pd
from scipy import optimize
import statsmodels.api as sm

TICKERS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]
BENCHMARK_TICKER = "SPY"

# Prescribed Conservative Institutional Endowment Portfolio Weights
# Tailored for capital preservation, real inflation protection, and downside defense
ENDOWMENT_WEIGHTS = {
    "AGG": 0.40,  # 40% US Investment Grade Bonds (Capital Preservation & Income)
    "SPY": 0.20,  # 20% US Large-Cap Equities (Core Real Growth)
    "GLD": 0.15,  # 15% Gold (Geopolitical Safe-Haven & Real Asset Inflation Hedge)
    "EFA": 0.10,  # 10% Developed International Equities (Global Diversification)
    "XLE": 0.05,  # 5% Energy Select Sector (Commodity/Stagflation Value Hedge)
    "XLK": 0.05,  # 5% Technology Growth (Secular Productivity Upside)
    "EEM": 0.05   # 5% Emerging Markets (High-Growth Long-Horizon Allocation)
}


def compute_portfolio_returns(returns_df, weights):
    """
    Computes portfolio daily returns given an asset returns DataFrame and weight vector.
    """
    w = np.array([weights[t] for t in TICKERS])
    port_returns = returns_df[TICKERS].dot(w)
    return port_returns


def compute_drawdown_series(returns_series):
    """
    Computes wealth index, peak cumulative wealth, drawdown series, and maximum drawdown.
    """
    wealth_index = (1.0 + returns_series).cumprod()
    peaks = wealth_index.cummax()
    drawdown = (wealth_index - peaks) / peaks
    max_drawdown = drawdown.min()
    return wealth_index, drawdown, max_drawdown


def calculate_institutional_kpis(returns_series, benchmark_series, rf_series=None):
    """
    Calculates standard institutional performance and risk KPIs required by Section 8.1:
      - Annualized Return & Annualized Volatility
      - Sharpe Ratio (ex-post excess return over Rf)
      - Sortino Ratio (downside risk with MAR = Rf)
      - Maximum Drawdown (MDD) & Calmar Ratio
      - CAPM Beta, Jensen's Alpha (annualized), R-Squared
      - Treynor Ratio (excess return / beta)
      - Information Ratio (tracking error relative to benchmark)
    """
    N = len(returns_series)
    ann_factor = 252.0

    # Risk-free rate
    if rf_series is not None:
        daily_rf = rf_series.reindex(returns_series.index).fillna(0.0)
    else:
        daily_rf = pd.Series(0.02 / ann_factor, index=returns_series.index)

    ann_rf = daily_rf.mean() * ann_factor

    # 1. Return & Volatility
    ann_return = returns_series.mean() * ann_factor
    ann_vol = returns_series.std() * np.sqrt(ann_factor)

    # 2. Sharpe Ratio
    excess_returns = returns_series - daily_rf
    sharpe_ratio = (excess_returns.mean() * ann_factor) / (ann_vol + 1e-8)

    # 3. Sortino Ratio (Downside deviation below daily_rf)
    downside_diff = returns_series - daily_rf
    downside_deviations = np.where(downside_diff < 0, downside_diff, 0.0)
    downside_std = np.sqrt(np.mean(downside_deviations ** 2)) * np.sqrt(ann_factor)
    sortino_ratio = (excess_returns.mean() * ann_factor) / (downside_std + 1e-8)

    # 4. Drawdowns & Calmar Ratio
    _, drawdown, max_dd = compute_drawdown_series(returns_series)
    calmar_ratio = ann_return / abs(max_dd) if abs(max_dd) > 1e-6 else np.nan

    # 5. CAPM Regression: (R_p - R_f) = Alpha + Beta * (R_m - R_f)
    mkt_excess = benchmark_series - daily_rf
    df_reg = pd.DataFrame({"y": excess_returns, "x": mkt_excess}).dropna()
    X = sm.add_constant(df_reg["x"])
    model = sm.OLS(df_reg["y"], X).fit()
    alpha_daily = model.params["const"]
    beta = model.params["x"]
    jensens_alpha = alpha_daily * ann_factor  # Annualized Alpha
    r_squared = model.rsquared

    # 6. Treynor Ratio
    treynor_ratio = (excess_returns.mean() * ann_factor) / beta if abs(beta) > 1e-4 else np.nan

    # 7. Information Ratio vs Benchmark
    tracking_diff = returns_series - benchmark_series
    tracking_error = tracking_diff.std() * np.sqrt(ann_factor)
    info_ratio = (tracking_diff.mean() * ann_factor) / (tracking_error + 1e-8)

    kpis = {
        "Annualized_Return": ann_return,
        "Annualized_Volatility": ann_vol,
        "Annualized_Rf": ann_rf,
        "Sharpe_Ratio": sharpe_ratio,
        "Sortino_Ratio": sortino_ratio,
        "Max_Drawdown": max_dd,
        "Calmar_Ratio": calmar_ratio,
        "CAPM_Beta": beta,
        "Jensens_Alpha": jensens_alpha,
        "Treynor_Ratio": treynor_ratio,
        "Information_Ratio": info_ratio,
        "R_Squared": r_squared
    }
    return kpis


def optimize_markowitz_portfolios(returns_df, rf=0.02):
    """
    Computes the Markowitz Efficient Frontier, Maximum Sharpe Portfolio,
    and Global Minimum Variance (GMV) Portfolio.
    Constraints: Long-only (w_i >= 0), fully invested (sum w_i = 1).
    """
    ann_factor = 252.0
    mean_ret = returns_df[TICKERS].mean() * ann_factor
    cov_matrix = returns_df[TICKERS].cov() * ann_factor
    num_assets = len(TICKERS)

    def port_perf(weights):
        r = np.sum(mean_ret * weights)
        v = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        s = (r - rf) / v
        return r, v, s

    # 1. Global Minimum Variance (GMV)
    def min_vol(w):
        return np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))

    bounds = tuple((0.0, 1.0) for _ in range(num_assets))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    init_guess = np.ones(num_assets) / num_assets

    res_gmv = optimize.minimize(min_vol, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    w_gmv = {ticker: float(res_gmv.x[i]) for i, ticker in enumerate(TICKERS)}

    # 2. Maximum Sharpe Ratio (Tangency)
    def neg_sharpe(w):
        r, v, s = port_perf(w)
        return -s

    res_max_s = optimize.minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
    w_max_sharpe = {ticker: float(res_max_s.x[i]) for i, ticker in enumerate(TICKERS)}

    # 3. 60/40 Equity/Bond Baseline
    w_60_40 = {t: 0.0 for t in TICKERS}
    w_60_40["SPY"] = 0.60
    w_60_40["AGG"] = 0.40

    # 4. Equal Weight (1/N)
    w_equal = {t: 1.0 / num_assets for t in TICKERS}

    # 5. Efficient Frontier points
    frontier_vols = []
    frontier_rets = []
    target_returns = np.linspace(mean_ret.min(), mean_ret.max() * 0.98, 40)
    for target in target_returns:
        cons = (
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'eq', 'fun': lambda w, t=target: np.sum(mean_ret * w) - t}
        )
        res_frontier = optimize.minimize(min_vol, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
        if res_frontier.success:
            frontier_vols.append(res_frontier.fun)
            frontier_rets.append(target)

    portfolios = {
        "Conservative_Endowment": ENDOWMENT_WEIGHTS,
        "Max_Sharpe_Tangency": w_max_sharpe,
        "Global_Min_Variance": w_gmv,
        "Standard_60_40": w_60_40,
        "Equal_Weight_1_N": w_equal
    }

    frontier_data = {
        "Target_Returns": np.array(frontier_rets),
        "Volatilities": np.array(frontier_vols)
    }

    return portfolios, frontier_data


def compare_all_portfolios(simple_returns, rf_annual=0.02):
    """
    Evaluates institutional KPIs across all key candidate portfolios.
    """
    portfolios, frontier = optimize_markowitz_portfolios(simple_returns, rf=rf_annual)
    rf_daily = simple_returns["RF"] if "RF" in simple_returns.columns else None
    benchmark = simple_returns[BENCHMARK_TICKER]

    records = []
    perf_series_dict = {}

    for name, weights in portfolios.items():
        ret_series = compute_portfolio_returns(simple_returns, weights)
        perf_series_dict[name] = ret_series
        kpis = calculate_institutional_kpis(ret_series, benchmark, rf_series=rf_daily)
        row = {"Portfolio": name}
        row.update(kpis)
        # Format weights summary
        row["Weights_Summary"] = ", ".join([f"{t}:{weights[t]*100:.1f}%" for t in TICKERS if weights[t] > 0.01])
        records.append(row)

    df_kpis = pd.DataFrame(records).set_index("Portfolio")
    return df_kpis, portfolios, perf_series_dict, frontier


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import download_and_clean_data

    _, _, simple_ret, _ = download_and_clean_data()
    df_kpis, ports, _, _ = compare_all_portfolios(simple_ret)
    print("\n--- Institutional Portfolio Performance & KPI Comparison ---")
    cols_display = ["Annualized_Return", "Annualized_Volatility", "Sharpe_Ratio", "Sortino_Ratio", "Max_Drawdown", "Calmar_Ratio", "CAPM_Beta", "Jensens_Alpha"]
    print(df_kpis[cols_display].to_string())
