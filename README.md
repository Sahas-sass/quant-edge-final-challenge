# Serendib University Endowment Fund ($10M Mandate)
### Quantitative Portfolio Construction, Extreme Value Theory & Multi-Layer Risk Engine
**Competition:** QuantEdge 1.0 &mdash; National STEM Quantitative Investment Research Challenge (Finals)  
**Client Mandate:** The Serendib University Endowment Fund (USD 10 Million Institutional Mandate)  
**Core Investment Philosophy:**  
> *"Avoiding large losses is more important than maximizing gains."*  
> *"A good investment decision is not the one with the highest expected return &mdash; it is the one whose downside you have actually measured, tested, and can defend."*

---

## 1. Quickstart & One-Command Execution

### A. Launch the Production Streamlit Interactive Dashboard
```bash
streamlit run src/app.py
```
*(Translates complex quantitative risk analysis into an interactive, intuitive dashboard for institutional investment committees).*

### B. Reproduce the Entire Quantitative Pipeline & Compile Reports
```bash
python run_all.py
```
*Executes all 5 quantitative layers, calibrates models, runs out-of-sample backtests, and compiles:*
1. **1-Page Executive Tear Sheet PDF**: `output/tear_sheet/Serendib_Endowment_Executive_Tear_Sheet.pdf`
2. **13-Page Technical Investment Memo PDF**: `output/report/Serendib_Endowment_Investment_Memo.pdf`

---

## 2. Prescribed Investable Universe (7 ETFs)

| Ticker | Asset Name | Role in Portfolio | Capital Weight | USD Allocation |
| :--- | :--- | :--- | :---: | :---: |
| **`AGG`** | iShares Core US Aggregate Bond | Capital preservation anchor; steady coupon yield | **40.0%** | **$4,000,000** |
| **`SPY`** | SPDR S&P 500 ETF Trust | Primary engine for long-term real growth | **20.0%** | **$2,000,000** |
| **`GLD`** | SPDR Gold Shares | Real safe-haven, currency hedge, inflation buffer | **15.0%** | **$1,500,000** |
| **`EFA`** | iShares MSCI EAFE ETF | Developed international diversification | **10.0%** | **$1,000,000** |
| **`XLE`** | Energy Select Sector SPDR | Commodity stagflation hedge & cash flow buffer | **5.0%** | **$500,000** |
| **`XLK`** | Technology Select Sector SPDR | Secular productivity growth alpha | **5.0%** | **$500,000** |
| **`EEM`** | iShares MSCI Emerging Markets | High-growth demographic upside | **5.0%** | **$500,000** |
| **Total** | | **Balanced Conservative Endowment Allocation** | **100.0%** | **$10,000,000** |

---

## 3. The 5-Layer Quantitative Framework

### Layer 1: Modern Portfolio Theory & Institutional KPIs
* **Markowitz Mean-Variance Optimization**: Efficient frontier derivation, Global Minimum Variance (GMV), and Tangency Max Sharpe portfolios.
* **Conservative Endowment Portfolio**:
  * **Annualized Return:** `+7.89%` (Comfortably surpasses the university spending rule of **CPI + 4.0%**, ~6.5%–7.5%).
  * **Annualized Volatility:** `10.40%` (vs. 11.93% for 60/40 and 16.28% for 1/N).
  * **Sharpe Ratio (Rf=2%):** `0.61` | **Sortino Ratio:** `0.87`.
  * **Maximum Drawdown:** `-28.52%` (Cuts drawdown severity by over $618,000 vs. standard 60/40's -34.70%).
  * **Jensen's Alpha:** `+1.24%` annual risk-adjusted outperformance over CAPM.

### Layer 2 & 3: Value-at-Risk (VaR) & Expected Shortfall (CVaR)
We implement and compare **Historical Simulation, Parametric (Variance-Covariance), and Monte Carlo Simulation (Student-t copula, df=5, 25,000 paths)** at 90%, 95%, and 99% confidence:
* **The Normality Trap:** At 99% confidence, Parametric VaR ($1.49%) severely understates tail risk compared to Historical VaR ($1.84%) and Monte Carlo VaR ($2.13%).
* **Expected Shortfall Coherence:** VaR violates subadditivity ($VaR(X+Y) > VaR(X) + VaR(Y)$), creating false diversification signals. Expected Shortfall ($CVaR$) satisfies all coherence axioms (Artzner et al. 1999) and reveals a **50% loss severity surcharge** beyond the VaR threshold.

### Layer 4: Extreme Value Theory (EVT) Peaks-Over-Threshold
* **Pickands-Balkema-de Haan Theorem**: Exceedances over optimal threshold $u^* = 0.0064$ (90th quantile, $N_u = 497$) converge to the **Generalized Pareto Distribution (GPD)**.
* **Heavy Tail Proof**: MLE fitting yields shape parameter **$\xi = 0.2440 > 0$**, proving that portfolio drawdowns reside in the **Fréchet heavy-tailed domain**.
* **The "Tail Risk Gap":** Conventional Gaussian Expected Shortfall misses **+60.5%** of actual tail losses ($1.71% vs. 2.75% EVT-ES). EVT establishes a mathematically defensible worst-case ceiling of **2.75% ($275,160)**.

### Layer 5: Model Validation & Regulatory Backtesting (2020–2026, N=1,697 days)
* **Kupiec POF Test:** The EVT 99% VaR model recorded **16 violations vs. 17.0 expected** ($p = 0.8149$), failing to reject the null hypothesis and demonstrating remarkable calibration.
* **Christoffersen Independence Test:** Confirms violations do not cluster over time.
* **Basel Traffic Light:** Places the portfolio squarely in the **GREEN ZONE** with zero regulatory capital surcharge.

### Layer 6: Crisis Stress Testing on USD 10 Million Capital
* **2008 Lehman Collapse:** Portfolio drawdown restricted to `-22.64%` (saving >$3.2M compared to S&P 500's -55.2%).
* **March 2020 COVID Crash:** Peak loss limited to `-19.07%` (-$1.69M).
* **2022 500bps Rate Hike & Stagflation:** Drawdown capped at `-16.55%` (-$1.59M).
* **Custom 2026–27 Oil Shock & Sovereign Liquidity Freeze:** Geopolitical oil spike (+60%) and rate freeze capped at `-10.75%` (-$1.07M), with Gold (+$330k) and Energy (+$190k) acting as capital preservation buffers.

---

## 4. Repository Structure

```text
Round_2_Final_Challenge/
├── data/                                # Clean local data (100% offline grading guarantee)
│   ├── clean_prices.csv                 # 4,967 daily observations (2007-2026)
│   ├── log_returns.csv                  # Continuous log returns for econometrics
│   ├── simple_returns.csv               # Simple returns for portfolio weighting
│   └── data_cleaning_audit.csv          # ADF stationarity & outlier diagnostic table
├── output/
│   ├── tear_sheet/                      # 1-Page Executive Tear Sheet PDF
│   │   └── Serendib_Endowment_Executive_Tear_Sheet.pdf
│   └── report/                          # 13-Page Comprehensive Technical Investment Memo PDF
│       └── Serendib_Endowment_Investment_Memo.pdf
├── src/                                 # Modular Quantitative & Streamlit Engine
│   ├── app.py                           # Production Streamlit Interactive Web Application
│   ├── data_loader.py                   # Data ingestion, cleaning, and ADF stationarity tests
│   ├── portfolio_engine.py              # Markowitz frontier, Max Sharpe, GMV & institutional KPIs
│   ├── risk_engine.py                   # 3 VaR methods & Expected Shortfall at 90/95/99%
│   ├── evt_engine.py                    # Extreme Value Theory (POT GPD) & Tail Risk Gap
│   ├── backtest_engine.py               # Out-of-sample Kupiec, Christoffersen & Basel Traffic Light
│   ├── stress_engine.py                 # Risk budgeting & crisis stress testing on $10M
│   ├── generate_tear_sheet.py           # ReportLab 1-page executive tear sheet generator
│   └── generate_memo.py                 # ReportLab 13-page technical memo generator
├── requirements.txt                     # Pinned project dependencies
├── run_all.py                           # Master one-command reproduction runner
└── README.md                            # Complete documentation & AI disclosure
```

---

## 5. Mandatory AI Tools Disclosure (Section 8.7)

*In strict compliance with the QuantEdge 1.0 Competitor Briefing disclosure requirements:*
* **AI Tool(s) Used:** Google Antigravity (powered by Gemini 3.8 Flash High).
* **Purpose:** Syntax acceleration, Streamlit front-end layout scaffolding, and ReportLab PDF layout budgeting.
* **Human Validation:** All mathematical equations (GPD log-likelihood, MPT quadratic program, Kupiec POF test, Christoffersen Markov transitions), portfolio weight selections, economic justifications, and committee recommendations were independently derived, verified, and audited by the competing team. All code is 100% reproducible.
