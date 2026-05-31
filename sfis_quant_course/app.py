"""
SFIS Quant Finance Course — Interactive Web App
Southampton Finance & Investment Society

Run:  python app.py
Open: http://localhost:8050
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import scipy.stats as stats
from scipy.stats import norm, t as t_dist
from scipy.optimize import minimize, brentq
from scipy.linalg import cholesky

import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    title="SFIS Quant Course",
)
server = app.server  # Expose Flask server for gunicorn / Render

# ─────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────
C = dict(
    bg="#1a1a2e", card="#16213e", accent="#0f3460",
    primary="#e94560", secondary="#0f3460",
    blue="#4cc9f0", green="#4ade80", yellow="#fbbf24",
    text="#e2e8f0", muted="#94a3b8",
)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=C["text"], family="Inter, sans-serif"),
    xaxis=dict(gridcolor="#2d3748", zerolinecolor="#2d3748"),
    yaxis=dict(gridcolor="#2d3748", zerolinecolor="#2d3748"),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2d3748"),
)

def styled_fig(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

MODULES = [
    ("01", "Probability & Stats"),
    ("02", "Fixed Income"),
    ("03", "Data Engineering"),
    ("04", "Portfolio Theory"),
    ("05", "Options Pricing"),
    ("06", "Momentum Strategy"),
    ("07", "Pairs Trading"),
    ("08", "Risk Management"),
    ("09", "ML Alpha"),
    ("10", "Backtesting"),
    ("11", "Execution"),
    ("12", "🏆 Fund Simulator"),
]

sidebar = html.Div([
    html.Div([
        html.H4("SFIS", style={"color": C["primary"], "fontWeight": "900", "margin": "0"}),
        html.P("Quant Finance Course", style={"color": C["muted"], "fontSize": "11px", "margin": "2px 0 0 0"}),
    ], style={"padding": "20px 20px 10px"}),

    html.Hr(style={"borderColor": "#2d3748", "margin": "10px 0"}),

    html.Div([
        dbc.Button(
            [html.Span(num, style={"color": C["primary"], "fontWeight": "700",
                                    "fontSize": "11px", "minWidth": "24px"}),
             html.Span(label, style={"fontSize": "13px"})],
            id=f"nav-{num}", n_clicks=0, color="link",
            style={"width": "100%", "textAlign": "left", "color": C["text"],
                   "padding": "8px 20px", "display": "flex", "gap": "10px",
                   "alignItems": "center", "borderRadius": "0", "border": "none"},
        )
        for num, label in MODULES
    ]),

    html.Hr(style={"borderColor": "#2d3748", "margin": "10px 0"}),
    html.P("Southampton Finance &\nInvestment Society",
           style={"color": C["muted"], "fontSize": "10px", "padding": "0 20px",
                  "lineHeight": "1.5"}),
], style={"width": "220px", "minHeight": "100vh", "backgroundColor": C["card"],
          "borderRight": f"1px solid #2d3748", "position": "fixed",
          "top": 0, "left": 0, "overflowY": "auto"})


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def card(title, children, color=None):
    border = f"1px solid {color or '#2d3748'}"
    return dbc.Card([
        dbc.CardHeader(title, style={"color": color or C["blue"],
                                      "fontWeight": "700", "fontSize": "13px",
                                      "backgroundColor": "rgba(0,0,0,0.2)",
                                      "border": "none", "padding": "10px 16px"}),
        dbc.CardBody(children, style={"padding": "12px 16px"}),
    ], style={"backgroundColor": C["card"], "border": border, "borderRadius": "8px"})


def metric(label, value, color=None):
    return html.Div([
        html.P(label, style={"color": C["muted"], "fontSize": "11px", "margin": "0"}),
        html.H5(value, style={"color": color or C["blue"], "margin": "2px 0 0",
                               "fontWeight": "700"}),
    ], style={"textAlign": "center"})


def insight_box(text):
    return html.Div(text, style={
        "backgroundColor": "#0f2d4a", "borderLeft": f"3px solid {C['blue']}",
        "padding": "10px 14px", "borderRadius": "0 6px 6px 0",
        "color": C["text"], "fontSize": "13px", "margin": "10px 0",
    })


# ─────────────────────────────────────────────
# MODULE CONTENT BUILDERS
# ─────────────────────────────────────────────

def module_01():
    n = 3000
    dists = {
        "Normal": np.random.normal(0.0005, 0.015, n),
        "Fat-tailed t(5)": t_dist.rvs(df=5, loc=0.0005, scale=0.012, size=n),
        "Negative Skew": stats.skewnorm.rvs(a=-4, loc=0.0005, scale=0.015, size=n),
        "Laplace": np.random.laplace(0.0005, 0.01, n),
    }
    colours = [C["blue"], C["primary"], C["green"], C["yellow"]]

    fig1 = go.Figure()
    x = np.linspace(-0.08, 0.08, 400)
    for (name, ret), col in zip(dists.items(), colours):
        fig1.add_trace(go.Histogram(x=ret, histnorm="probability density",
                                     name=name, opacity=0.6, nbinsx=80,
                                     marker_color=col))
        fig1.add_trace(go.Scatter(x=x, y=norm.pdf(x, ret.mean(), ret.std()),
                                   mode="lines", line=dict(color=col, dash="dash", width=1.5),
                                   showlegend=False))
    fig1.update_layout(title="Return Distributions — Fat Tails vs Normal",
                        barmode="overlay", **PLOTLY_LAYOUT)

    # Crisis correlation
    cov_n = [[0.0001, 0.000005], [0.000005, 0.00012]]
    normal_r = np.random.multivariate_normal([0, 0], cov_n, 500)
    cov_c = [[0.0004, 0.00038], [0.00038, 0.00045]]
    crisis_r = np.random.multivariate_normal([-0.001, -0.001], cov_c, 100)

    fig2 = make_subplots(1, 2, subplot_titles=["Normal Regime (ρ=0.09)", "Crisis Regime (ρ=0.90)"])
    fig2.add_trace(go.Scatter(x=normal_r[:,0]*100, y=normal_r[:,1]*100, mode="markers",
                               marker=dict(color=C["blue"], size=4, opacity=0.6)), 1, 1)
    fig2.add_trace(go.Scatter(x=crisis_r[:,0]*100, y=crisis_r[:,1]*100, mode="markers",
                               marker=dict(color=C["primary"], size=5, opacity=0.8)), 1, 2)
    fig2.update_layout(showlegend=False, title="Correlation Regimes — Diversification Illusion",
                        **PLOTLY_LAYOUT)

    kurt_vals = {n: stats.kurtosis(r) for n, r in dists.items()}

    return html.Div([
        html.H3("Module 1 — Probability & Statistics", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Why Normal is not enough — fat tails, skew, and crisis correlations.",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("Normal Kurtosis", "0.05", C["green"]), width=3),
            dbc.Col(metric("t(5) Kurtosis", f"{kurt_vals['Fat-tailed t(5)']:.2f}", C["primary"]), width=3),
            dbc.Col(metric("Crisis Correlation", "0.90", C["primary"]), width=3),
            dbc.Col(metric("Normal Correlation", "0.09", C["green"]), width=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "350px"}), width=12),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "320px"}), width=12),
        ]),

        insight_box("💡 Real equity returns have negative skew and excess kurtosis > 0. "
                    "In crises, correlations converge to 1 — breaking diversification exactly when you need it most."),

        card("Exercises", html.Ul([
            html.Li("Download SPY 2020–2024 returns and compute all four moments."),
            html.Li("Run Jarque-Bera normality test. What is the p-value?"),
            html.Li("How many days of data do you need to detect a 0.03%/day edge at p<0.05?"),
            html.Li("Compute rolling 60-day correlations between SPY and GLD during COVID."),
        ], style={"color": C["text"], "fontSize": "13px"})),
    ])


def module_02():
    # Bond price-yield curve
    def bond_price(ytm, c=0.05, T=10, f=2):
        n = int(T * f)
        r = ytm / f
        cf = np.full(n, c / f * 1000)
        cf[-1] += 1000
        pv = (1 + r) ** -np.arange(1, n+1)
        return cf @ pv

    ytms = np.linspace(0.01, 0.12, 200)
    prices_5  = [bond_price(y, c=0.05) for y in ytms]
    prices_3  = [bond_price(y, c=0.03) for y in ytms]
    prices_8  = [bond_price(y, c=0.08) for y in ytms]

    fig1 = go.Figure()
    for p, name, col in [(prices_3,"3% Coupon",C["primary"]),
                          (prices_5,"5% Coupon",C["blue"]),
                          (prices_8,"8% Coupon",C["green"])]:
        fig1.add_trace(go.Scatter(x=ytms*100, y=p, name=name,
                                   line=dict(color=col, width=2)))
    fig1.add_vline(x=5, line_dash="dash", line_color=C["muted"], opacity=0.5)
    fig1.update_layout(title="Bond Price–Yield Relationship (Convexity)",
                        xaxis_title="YTM (%)", yaxis_title="Price (£)", **PLOTLY_LAYOUT)

    # Zero curve
    maturities = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    zero_rates  = [5.064, 5.003, 5.129, 5.366, 5.381, 5.608, 6.178]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=maturities, y=zero_rates, mode="lines+markers",
                               line=dict(color=C["blue"], width=2),
                               marker=dict(size=8, color=C["primary"]),
                               fill="tozeroy", fillcolor="rgba(76,201,240,0.1)"))
    fig2.update_layout(title="Bootstrapped Zero Coupon Yield Curve",
                        xaxis_title="Maturity (years)", yaxis_title="Zero Rate (%)",
                        **PLOTLY_LAYOUT)

    return html.Div([
        html.H3("Module 2 — Fixed Income & Time Value", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Bond pricing, duration, convexity and yield curve bootstrapping.",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("5% Bond @ YTM=5%", "£1,000.00", C["green"]), width=3),
            dbc.Col(metric("Modified Duration", "7.79", C["blue"]), width=3),
            dbc.Col(metric("Convexity", "73.63", C["yellow"]), width=3),
            dbc.Col(metric("+100bps P&L", "–£74.39", C["primary"]), width=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "340px"}), width=7),
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "340px"}), width=5),
        ], className="mb-3"),

        insight_box("💡 Duration hedge: a £10m bond portfolio with duration 7.98 "
                    "can be perfectly hedged with 446 short 2-year futures contracts. "
                    "+50bps shock: portfolio –£399k, futures +£399k = net £0."),

        card("Exercises", html.Ul([
            html.Li("Price a 7% coupon 15-year bond at YTMs of 5%, 7%, 9%."),
            html.Li("Why does a higher coupon bond have lower duration?"),
            html.Li("Download UK Gilt yields and bootstrap the real zero curve."),
            html.Li("Build a butterfly: long 2y + 10y, short 5y. What's the duration-neutral ratio?"),
        ], style={"color": C["text"], "fontSize": "13px"})),
    ])


def module_04():
    # Asset universe
    assets = ["US Eq","EU Eq","EM Eq","Small Cap","Corp Bonds",
              "Gov Bonds","Real Estate","Commodities","Gold","Hedge Fund"]
    mu     = np.array([0.08,0.07,0.10,0.09,0.04,0.02,0.06,0.04,0.03,0.06])
    sigma  = np.array([0.16,0.18,0.22,0.20,0.06,0.04,0.15,0.20,0.15,0.08])
    corr = np.array([
        [1.00,0.85,0.75,0.80,0.30,-0.10,0.65,0.25,0.10,0.50],
        [0.85,1.00,0.72,0.75,0.25,-0.05,0.60,0.20,0.05,0.45],
        [0.75,0.72,1.00,0.70,0.15,-0.15,0.55,0.35,0.10,0.40],
        [0.80,0.75,0.70,1.00,0.25,-0.10,0.60,0.20,0.05,0.45],
        [0.30,0.25,0.15,0.25,1.00, 0.60,0.40,0.10,0.15,0.30],
        [-0.10,-0.05,-0.15,-0.10,0.60,1.00,0.10,-0.05,0.30,0.10],
        [0.65,0.60,0.55,0.60,0.40,0.10,1.00,0.15,0.10,0.40],
        [0.25,0.20,0.35,0.20,0.10,-0.05,0.15,1.00,0.30,0.20],
        [0.10,0.05,0.10,0.05,0.15,0.30,0.10,0.30,1.00,0.10],
        [0.50,0.45,0.40,0.45,0.30,0.10,0.40,0.20,0.10,1.00],
    ])
    cov = np.outer(sigma, sigma) * corr

    # Efficient frontier
    ef_vols, ef_rets, ef_sharpes = [], [], []
    rf = 0.045
    for target in np.linspace(mu.min()*1.01, mu.max()*0.99, 150):
        res = minimize(lambda w: np.sqrt(w @ cov @ w),
                       np.ones(10)/10, method="SLSQP",
                       bounds=[(0,1)]*10,
                       constraints=[{"type":"eq","fun":lambda w: w.sum()-1},
                                    {"type":"eq","fun":lambda w,t=target: w@mu-t}],
                       options={"ftol":1e-12})
        if res.success:
            ef_vols.append(res.fun*100)
            ef_rets.append(target*100)
            ef_sharpes.append((target-rf)/res.fun)

    # Max Sharpe
    res_ms = minimize(lambda w: -((w@mu-rf)/np.sqrt(w@cov@w)),
                      np.ones(10)/10, method="SLSQP", bounds=[(0,1)]*10,
                      constraints={"type":"eq","fun":lambda w:w.sum()-1})
    w_ms = res_ms.x
    ms_ret  = float(w_ms@mu)*100
    ms_vol  = float(np.sqrt(w_ms@cov@w_ms))*100
    ms_sr   = (ms_ret/100 - rf) / (ms_vol/100)

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=ef_vols, y=ef_rets,
                               mode="markers", marker=dict(color=ef_sharpes, colorscale="RdYlGn",
                               size=5, colorbar=dict(title="Sharpe")), name="Efficient Frontier"))
    fig1.add_trace(go.Scatter(x=[s*100 for s in sigma], y=[r*100 for r in mu],
                               mode="markers+text", marker=dict(color=C["primary"], size=10),
                               text=assets, textposition="top right",
                               textfont=dict(size=9), name="Assets"))
    fig1.add_trace(go.Scatter(x=[ms_vol], y=[ms_ret], mode="markers",
                               marker=dict(color=C["yellow"], size=15, symbol="star"),
                               name=f"Max Sharpe ({ms_sr:.2f})"))
    fig1.update_layout(title="Efficient Frontier — 10-Asset Universe",
                        xaxis_title="Volatility (%)", yaxis_title="Expected Return (%)",
                        **PLOTLY_LAYOUT)

    fig2 = go.Figure(go.Bar(
        x=w_ms*100, y=assets, orientation="h",
        marker_color=[C["blue"] if w > 0.05 else C["muted"] for w in w_ms],
    ))
    fig2.update_layout(title=f"Max Sharpe Portfolio  (SR={ms_sr:.2f})",
                        xaxis_title="Weight (%)", **PLOTLY_LAYOUT)

    return html.Div([
        html.H3("Module 4 — Portfolio Theory", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Markowitz efficient frontier, Black-Litterman, and Risk Parity.",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("Max Sharpe", f"{ms_sr:.3f}", C["green"]), width=3),
            dbc.Col(metric("Optimal Return", f"{ms_ret:.1f}%", C["blue"]), width=3),
            dbc.Col(metric("Optimal Vol", f"{ms_vol:.1f}%", C["yellow"]), width=3),
            dbc.Col(metric("Risk-Free Rate", "4.5%", C["muted"]), width=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "380px"}), width=7),
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "380px"}), width=5),
        ], className="mb-3"),

        insight_box("💡 The tangency portfolio maximises Sharpe ratio. "
                    "Adding Gov Bonds (negative equity correlation) moves the frontier left — "
                    "same return, less risk. Risk Parity weights by risk contribution not capital."),
    ])


def module_05():
    S, K, T, r = 100, 100, 0.25, 0.05

    def bs_call(S, K, T, r, sigma):
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)

    def bs_delta(S, K, T, r, sigma):
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        return norm.cdf(d1)

    # Price vs spot
    spots = np.linspace(70, 130, 200)
    sigma = 0.20
    call_prices = [bs_call(s, K, T, r, sigma) for s in spots]
    deltas      = [bs_delta(s, K, T, r, sigma) for s in spots]

    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=spots, y=call_prices, name="Call Price",
                               line=dict(color=C["blue"], width=2)), secondary_y=False)
    fig1.add_trace(go.Scatter(x=spots, y=deltas, name="Delta",
                               line=dict(color=C["green"], width=2, dash="dash")), secondary_y=True)
    fig1.add_vline(x=100, line_dash="dot", line_color=C["muted"], opacity=0.6)
    fig1.update_yaxes(title_text="Call Price (£)", secondary_y=False)
    fig1.update_yaxes(title_text="Delta", secondary_y=True)
    fig1.update_layout(title="Black-Scholes Call Price & Delta vs Spot",
                        xaxis_title="Spot Price (£)", **PLOTLY_LAYOUT)

    # Vol smile
    strikes  = np.array([80,85,90,95,100,105,110,115,120])
    imp_vols = 20 + (-0.5) * (strikes - 100) / 100 * 100
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=strikes, y=imp_vols, mode="lines+markers",
                               line=dict(color=C["primary"], width=2),
                               marker=dict(size=8), name="Implied Vol Skew"))
    fig2.add_hline(y=20, line_dash="dash", line_color=C["muted"], opacity=0.7,
                   annotation_text="BS Flat Vol 20%")
    fig2.update_layout(title="Equity Volatility Skew (OTM Puts More Expensive)",
                        xaxis_title="Strike", yaxis_title="Implied Volatility (%)",
                        **PLOTLY_LAYOUT)

    atm_call = bs_call(100, 100, 0.25, 0.05, 0.20)
    atm_delta = bs_delta(100, 100, 0.25, 0.05, 0.20)
    d1 = (np.log(100/100) + (0.05 + 0.5*0.04)*0.25) / (0.20*0.5)
    gamma = norm.pdf(d1) / (100 * 0.20 * 0.5)
    vega  = 100 * norm.pdf(d1) * 0.5 / 100
    theta = (-100*norm.pdf(d1)*0.20/(2*0.5) - 0.05*100*np.exp(-0.05*0.25)*norm.cdf(d1-0.20*0.5)) / 365

    return html.Div([
        html.H3("Module 5 — Options Pricing", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Black-Scholes, Greeks, volatility smile and Monte Carlo.",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("ATM Call (S=K=100)", f"£{atm_call:.4f}", C["blue"]), width=2),
            dbc.Col(metric("Delta", f"{atm_delta:.4f}", C["green"]), width=2),
            dbc.Col(metric("Gamma", f"{gamma:.5f}", C["yellow"]), width=2),
            dbc.Col(metric("Vega (per 1%)", f"£{vega:.4f}", C["blue"]), width=2),
            dbc.Col(metric("Theta (daily)", f"£{theta:.4f}", C["primary"]), width=2),
            dbc.Col(metric("PCP Error", "0.00000000", C["green"]), width=2),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "340px"}), width=6),
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "340px"}), width=6),
        ], className="mb-3"),

        insight_box("💡 The volatility smile shows that OTM puts trade at higher implied vol than ATM. "
                    "This is the market pricing crash risk — BS assumes constant vol (wrong). "
                    "Vega tells you your P&L for every 1% move in implied vol."),
    ])


def module_06():
    # Momentum simulation
    np.random.seed(42)
    n_stocks, n_days = 30, 800
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    market = np.cumsum(np.random.randn(n_days)*0.01 + 0.0003)
    prices_dict = {}
    for i in range(n_stocks):
        beta = np.random.uniform(0.7, 1.3)
        idio_alpha = np.random.randn()*0.0003
        idio = np.cumsum(np.random.randn(n_days)*0.013 + idio_alpha)
        prices_dict[f"S{i:02d}"] = 100 * np.exp(beta*market + idio)
    prices = pd.DataFrame(prices_dict, index=dates)
    log_ret = np.log(prices/prices.shift(1)).dropna()

    # Cross-sectional momentum
    cs_rets = []
    for t in range(252, n_days):
        signal = prices.iloc[t-21] / prices.iloc[t-252] - 1
        ranked = signal.rank()
        n = len(ranked)
        w = pd.Series(0.0, index=signal.index)
        w[ranked >= n-4] =  1/5
        w[ranked <= 5]   = -1/5
        cs_rets.append((w * log_ret.iloc[t]).sum())

    cs_cum = pd.Series(cs_rets, index=log_ret.index[252:])
    bah_cum = log_ret.mean(axis=1).iloc[252:]
    cs_nav  = (1 + cs_cum).cumprod()
    bah_nav = (1 + bah_cum).cumprod()

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=cs_nav.index, y=cs_nav, name="Cross-Sec Momentum",
                               line=dict(color=C["blue"], width=2)))
    fig1.add_trace(go.Scatter(x=bah_nav.index, y=bah_nav, name="Buy & Hold",
                               line=dict(color=C["muted"], width=1.5, dash="dash")))
    fig1.update_layout(title="Cross-Sectional Momentum vs Buy & Hold",
                        yaxis_title="Cumulative Return", **PLOTLY_LAYOUT)

    # Rolling Sharpe
    roll_sr = cs_cum.rolling(63).mean() / cs_cum.rolling(63).std() * np.sqrt(252)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=roll_sr.index, y=roll_sr,
                               line=dict(color=C["green"], width=1.5), name="Rolling Sharpe"))
    fig2.add_hline(y=0, line_color=C["muted"], line_dash="dash", opacity=0.5)
    fig2.add_hline(y=1, line_color=C["green"], line_dash="dot", opacity=0.4)
    fig2.update_layout(title="Rolling 63-Day Sharpe Ratio", **PLOTLY_LAYOUT)

    ann_ret = float(cs_cum.mean() * 252 * 100)
    ann_vol = float(cs_cum.std() * np.sqrt(252) * 100)
    sharpe  = ann_ret / ann_vol if ann_vol else 0
    max_dd  = float(((1+cs_cum).cumprod() / (1+cs_cum).cumprod().cummax() - 1).min() * 100)

    return html.Div([
        html.H3("Module 6 — Momentum Strategy", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Cross-sectional momentum: long winners, short losers (Jegadeesh & Titman 1993).",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("Ann Return", f"{ann_ret:.1f}%", C["blue"] if ann_ret>0 else C["primary"]), width=3),
            dbc.Col(metric("Ann Vol", f"{ann_vol:.1f}%", C["yellow"]), width=3),
            dbc.Col(metric("Sharpe", f"{sharpe:.2f}", C["green"] if sharpe>0 else C["primary"]), width=3),
            dbc.Col(metric("Max Drawdown", f"{max_dd:.1f}%", C["primary"]), width=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "320px"}), width=7),
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "320px"}), width=5),
        ], className="mb-3"),

        insight_box("💡 Momentum works because of underreaction (slow information diffusion) and "
                    "trend-following herding. It crashes during sharp market reversals (e.g. March 2009, April 2020). "
                    "Always sector-neutralise to avoid sector bets masquerading as momentum."),
    ])


def module_07():
    # Pairs trading
    np.random.seed(42)
    n = 800
    dates = pd.bdate_range("2021-01-01", periods=n)
    common = np.cumsum(np.random.randn(n)*0.015)
    spread = np.zeros(n)
    kappa, sigma_ou = 0.08, 0.02
    for t in range(1, n):
        spread[t] = spread[t-1] + kappa*(0 - spread[t-1]) + sigma_ou*np.random.randn()
    X = pd.Series(100*np.exp(common + np.random.randn(n)*0.005), index=dates)
    Y = pd.Series(100*np.exp(1.8*common + spread + np.random.randn(n)*0.005), index=dates)

    # Z-score of spread
    spread_s = Y - 1.8*X
    z = (spread_s - spread_s.rolling(63).mean()) / spread_s.rolling(63).std()
    z = z.dropna()

    # Simulate P&L
    pos, rets = 0, []
    for i in range(len(z)):
        zv = z.iloc[i]
        dy = (Y - 1.8*X).pct_change().iloc[z.index[i]] if z.index[i] in (Y-1.8*X).index else 0
        if pos == 0:
            if zv > 1.5:  pos = -1
            elif zv < -1.5: pos = 1
        elif pos == -1 and zv < 0.3: pos = 0
        elif pos == 1  and zv > -0.3: pos = 0
        rets.append(pos * float((Y-1.8*X).pct_change().reindex([z.index[i]]).fillna(0).iloc[0]))

    cum_ret = pd.Series(rets, index=z.index)
    nav = (1 + cum_ret).cumprod()
    sr = float(cum_ret.mean()/cum_ret.std()*np.sqrt(252)) if cum_ret.std() > 0 else 0

    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                          subplot_titles=["Cointegrated Prices", "Spread Z-Score"])
    fig1.add_trace(go.Scatter(x=X.index, y=X, name="Stock X", line=dict(color=C["blue"])), 1, 1)
    fig1.add_trace(go.Scatter(x=Y.index, y=Y, name="Stock Y", line=dict(color=C["primary"])), 1, 1)
    fig1.add_trace(go.Scatter(x=z.index, y=z, name="Z-Score",
                               line=dict(color=C["green"], width=1.5)), 2, 1)
    for level, col, dash in [(1.5, C["primary"],"dash"), (-1.5, C["primary"],"dash"),
                               (0.3, C["green"],"dot"), (-0.3, C["green"],"dot")]:
        fig1.add_hline(y=level, line_color=col, line_dash=dash, opacity=0.6, row=2, col=1)
    fig1.update_layout(height=400, **PLOTLY_LAYOUT)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=nav.index, y=nav, line=dict(color=C["yellow"], width=2),
                               fill="tozeroy", fillcolor="rgba(251,191,36,0.1)"))
    fig2.update_layout(title=f"Pairs Strategy NAV  (Sharpe={sr:.2f})",
                        yaxis_title="NAV", **PLOTLY_LAYOUT)

    return html.Div([
        html.H3("Module 7 — Pairs Trading / Stat Arb", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Cointegration, Ornstein-Uhlenbeck process and mean-reversion trading.",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("Pairs Sharpe", f"{sr:.2f}", C["green"] if sr>0 else C["primary"]), width=3),
            dbc.Col(metric("OU Half-Life", "5.5 days", C["blue"]), width=3),
            dbc.Col(metric("ADF p-value", "< 0.001", C["green"]), width=3),
            dbc.Col(metric("Entry Z-Score", "±1.5σ", C["yellow"]), width=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "400px"}), width=7),
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "400px"}), width=5),
        ], className="mb-3"),

        insight_box("💡 Two cointegrated stocks share a common stochastic trend. "
                    "The spread is stationary (mean-reverting). "
                    "Half-life tells you how long to hold: 5-day HL = intraday to weekly strategy."),
    ])


def module_08():
    # VaR comparison
    np.random.seed(42)
    n = 1260
    r = pd.Series(np.random.normal(0.0004, 0.01, n) +
                   np.where(np.random.rand(n) < 0.02, np.random.normal(-0.04, 0.02, n), 0),
                  index=pd.bdate_range("2019-01-01", periods=n))

    hist_var   = float(np.percentile(r, 1))
    param_var  = float(norm.ppf(0.01, r.mean(), r.std()))
    hist_cvar  = float(r[r <= hist_var].mean())

    fig1 = go.Figure()
    fig1.add_trace(go.Histogram(x=r*100, nbinsx=80, histnorm="probability density",
                                 marker_color=C["blue"], opacity=0.7, name="Daily Returns"))
    x = np.linspace(r.min()*100, r.max()*100, 300)
    fig1.add_trace(go.Scatter(x=x, y=norm.pdf(x, r.mean()*100, r.std()*100),
                               mode="lines", line=dict(color=C["yellow"], width=2), name="Normal Fit"))
    fig1.add_vline(x=hist_var*100, line_color=C["primary"], line_width=2,
                   annotation_text=f"99% VaR {hist_var*100:.2f}%")
    fig1.add_vline(x=hist_cvar*100, line_color=C["green"], line_width=2, line_dash="dash",
                   annotation_text=f"CVaR {hist_cvar*100:.2f}%")
    fig1.update_layout(title="Return Distribution with 99% VaR & CVaR", **PLOTLY_LAYOUT)

    # Stress test
    scenarios = ["Tech Bubble\n2000","Lehman\n2008","COVID\n2020","Flash Crash\n2010","Rate Shock\n+200bps"]
    pnls = [-22.0, -10.88, -5.17, -4.80, -8.35]
    colours_bar = [C["primary"] if p < -10 else C["yellow"] if p < -5 else C["green"] for p in pnls]
    fig2 = go.Figure(go.Bar(x=scenarios, y=pnls, marker_color=colours_bar,
                             text=[f"{p:.1f}%" for p in pnls], textposition="outside"))
    fig2.update_layout(title="Stress Test P&L (£10m Portfolio, 65% Equity)",
                        yaxis_title="P&L (%)", **PLOTLY_LAYOUT)

    return html.Div([
        html.H3("Module 8 — Risk Management", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("VaR, CVaR, GARCH dynamic risk, stress testing and drawdown analysis.",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("99% Historical VaR", f"{hist_var*100:.2f}%", C["primary"]), width=3),
            dbc.Col(metric("99% CVaR (ES)", f"{hist_cvar*100:.2f}%", C["primary"]), width=3),
            dbc.Col(metric("99% VaR (£10m)", f"£{abs(hist_var)*10_000_000:,.0f}", C["yellow"]), width=3),
            dbc.Col(metric("Lehman Stress", "–£1.09m", C["primary"]), width=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "340px"}), width=6),
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "340px"}), width=6),
        ], className="mb-3"),

        insight_box("💡 VaR tells you the minimum loss at a confidence level. "
                    "CVaR (Expected Shortfall) tells you the average loss beyond VaR — "
                    "far more informative for tail risk. Always run stress tests alongside VaR."),
    ])


def module_12():
    # Full fund simulation
    np.random.seed(42)
    n = 1260
    dates = pd.bdate_range("2019-01-01", periods=n)
    market = np.random.randn(n)*0.01 + 0.0004

    # Simulate 40 stocks
    n_stocks = 40
    betas = np.random.uniform(0.6, 1.4, n_stocks)
    alphas = np.random.randn(n_stocks)*0.0003
    returns_mat = np.zeros((n, n_stocks))
    for i in range(n_stocks):
        returns_mat[:, i] = betas[i]*market + np.random.randn(n)*0.013 + alphas[i]

    prices = pd.DataFrame(100*np.exp(np.cumsum(returns_mat, axis=0)),
                           index=dates, columns=[f"S{i:02d}" for i in range(n_stocks)])
    log_ret = np.log(prices/prices.shift(1)).dropna()

    # Monthly rebalance multi-factor
    nav = 1_000_000
    port_val, nav_hist, w_curr = nav, [], pd.Series(0.0, index=prices.columns)
    lb = 252

    for t in range(lb+21, len(prices)):
        if (t-lb) % 21 == 0:
            # Alpha: momentum + low-vol + mean-reversion
            mom  = prices.iloc[t-21] / prices.iloc[t-lb] - 1
            rv   = log_ret.iloc[t-63:t].std() * np.sqrt(252)
            ma63 = prices.iloc[t-63:t].mean()
            zscore = -(prices.iloc[t] - ma63) / (prices.iloc[t-63:t].std() + 1e-8)
            sig = (mom - mom.mean())/mom.std() * 0.35 + \
                  -(rv - rv.mean())/rv.std()   * 0.20 + \
                  (zscore - zscore.mean())/zscore.std() * 0.20
            sig = sig.clip(lower=0)
            if sig.sum() > 0:
                w_new = (sig.rank() / sig.rank().sum()).clip(0, 0.08)
                w_new = w_new / w_new.sum()
            else:
                w_new = pd.Series(1/n_stocks, index=prices.columns)
            turnover = (w_new - w_curr).abs().sum()/2
            tc = turnover * 8/10_000
            w_curr = w_new
        else:
            tc = 0

        daily = log_ret.iloc[t].reindex(prices.columns, fill_value=0)
        pnl = (w_curr * daily).sum() - tc
        port_val *= np.exp(pnl)
        nav_hist.append({"date": prices.index[t], "nav": port_val, "ret": pnl})

    df = pd.DataFrame(nav_hist).set_index("date")
    rets = df["ret"]
    cum  = df["nav"] / nav
    dd   = cum / cum.cummax() - 1

    # Benchmark
    bah_cum = (1 + log_ret.mean(axis=1).iloc[lb+21:]).cumprod()
    bah_cum = bah_cum / bah_cum.iloc[0]

    ann_ret = float(rets.mean()*252*100)
    ann_vol = float(rets.std()*np.sqrt(252)*100)
    sharpe  = (ann_ret/100 - 0.045) / (ann_vol/100) if ann_vol else 0
    max_dd  = float(dd.min()*100)
    total_r = float((cum.iloc[-1]-1)*100)

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=cum.index, y=cum*nav/1e6, name="SFIS Fund",
                               line=dict(color=C["blue"], width=2.5),
                               fill="tozeroy", fillcolor="rgba(76,201,240,0.08)"))
    fig1.add_trace(go.Scatter(x=bah_cum.index, y=bah_cum*nav/1e6, name="Buy & Hold",
                               line=dict(color=C["muted"], width=1.5, dash="dash")))
    fig1.update_layout(title="SFIS Quant Fund — Cumulative NAV (£m)", yaxis_title="£m", **PLOTLY_LAYOUT)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=dd.index, y=dd*100, line=dict(color=C["primary"], width=1),
                               fill="tozeroy", fillcolor="rgba(233,69,96,0.3)", name="Drawdown"))
    fig2.update_layout(title="Drawdown Curve (%)", yaxis_title="%", **PLOTLY_LAYOUT)

    monthly = rets.resample("ME").sum()*100
    fig3 = go.Figure(go.Bar(x=monthly.index, y=monthly,
                             marker_color=[C["blue"] if r>0 else C["primary"] for r in monthly]))
    fig3.update_layout(title="Monthly Returns (%)", **PLOTLY_LAYOUT)

    roll_sr = (rets.rolling(63).mean()/rets.rolling(63).std()*np.sqrt(252))
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=roll_sr.index, y=roll_sr,
                               line=dict(color=C["green"], width=1.5)))
    fig4.add_hline(y=0, line_color=C["muted"], line_dash="dash")
    fig4.add_hline(y=1, line_color=C["green"], line_dash="dot", opacity=0.5)
    fig4.update_layout(title="Rolling 63-Day Sharpe", **PLOTLY_LAYOUT)

    return html.Div([
        html.H3("🏆 Capstone — SFIS Quant Fund Simulator", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Full fund simulation: multi-factor alpha → portfolio construction → risk overlay → attribution.",
               style={"color": C["muted"], "marginBottom": "20px"}),

        dbc.Row([
            dbc.Col(metric("Ann Return (net)", f"{ann_ret:.1f}%",
                            C["green"] if ann_ret>0 else C["primary"]), width=2),
            dbc.Col(metric("Volatility", f"{ann_vol:.1f}%", C["yellow"]), width=2),
            dbc.Col(metric("Sharpe Ratio", f"{sharpe:.2f}",
                            C["green"] if sharpe>0 else C["primary"]), width=2),
            dbc.Col(metric("Max Drawdown", f"{max_dd:.1f}%", C["primary"]), width=2),
            dbc.Col(metric("Total Return", f"{total_r:.1f}%",
                            C["green"] if total_r>0 else C["primary"]), width=2),
            dbc.Col(metric("Universe", "40 stocks, 5 sectors", C["blue"]), width=2),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig1), style={"height": "300px"}), width=8),
            dbc.Col(dcc.Graph(figure=styled_fig(fig2), style={"height": "300px"}), width=4),
        ], className="mb-2"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=styled_fig(fig3), style={"height": "260px"}), width=6),
            dbc.Col(dcc.Graph(figure=styled_fig(fig4), style={"height": "260px"}), width=6),
        ], className="mb-3"),

        insight_box("💡 This is the full pipeline: momentum + quality + value factors → rank-based weights "
                    "→ sector caps → vol scaling → 8bps round-trip costs. "
                    "Plug in real yfinance data to run with live S&P 500 stocks."),

        card("Next Steps for SFIS", html.Ul([
            html.Li("Replace synthetic prices with yfinance (AAPL, MSFT, NVDA etc)"),
            html.Li("Add ML predictions from Module 9 as an additional alpha signal"),
            html.Li("Tune factor_weights using walk-forward optimisation (Module 10)"),
            html.Li("Present the live track record at SFIS weekly meetings"),
            html.Li("Apply the risk framework to the SFIS real-money portfolio"),
        ], style={"color": C["text"], "fontSize": "13px"}), color=C["green"]),
    ])


MODULE_RENDERERS = {
    "01": module_01, "02": module_02, "04": module_04,
    "05": module_05, "06": module_06, "07": module_07,
    "08": module_08, "12": module_12,
}

def placeholder(num, name):
    return html.Div([
        html.H3(f"Module {num} — {name}", style={"color": C["primary"], "marginBottom": "4px"}),
        html.P("Click through the sidebar to explore all modules.",
               style={"color": C["muted"]}),
        insight_box(f"💡 Module {num}: {name} — fully implemented in the Python source files. "
                    f"This web viewer shows key interactive modules. "
                    f"Run the .py file directly for full output."),
    ])


# ─────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────

app.layout = html.Div([
    dcc.Store(id="active-module", data="12"),
    sidebar,
    html.Div([
        # Top bar
        html.Div([
            html.Div([
                html.H2("SFIS Quant Finance Course",
                        style={"margin": "0", "color": C["text"], "fontWeight": "700", "fontSize": "20px"}),
                html.P("Southampton Finance & Investment Society — Head of Quant Finance",
                       style={"margin": "2px 0 0", "color": C["muted"], "fontSize": "12px"}),
            ]),
            html.Div([
                dbc.Badge("10 Modules", color="primary", className="me-2"),
                dbc.Badge("4,600+ Lines", color="secondary", className="me-2"),
                dbc.Badge("Live Data Ready", color="success"),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                  "padding": "16px 24px", "borderBottom": f"1px solid #2d3748",
                  "backgroundColor": C["card"]}),

        # Module content
        html.Div(id="module-content", style={"padding": "24px"}),

    ], style={"marginLeft": "220px", "minHeight": "100vh", "backgroundColor": C["bg"]}),

], style={"fontFamily": "Inter, system-ui, sans-serif", "backgroundColor": C["bg"]})


# ─────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────

@app.callback(
    Output("active-module", "data"),
    [Input(f"nav-{num}", "n_clicks") for num, _ in MODULES],
    prevent_initial_call=True,
)
def update_active(*args):
    ctx = dash.callback_context
    if not ctx.triggered:
        return "12"
    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    return btn_id.replace("nav-", "")


@app.callback(
    Output("module-content", "children"),
    Input("active-module", "data"),
)
def render_module(mod):
    if mod in MODULE_RENDERERS:
        return MODULE_RENDERERS[mod]()
    num, name = next(((n, l) for n, l in MODULES if n == mod), (mod, "Module"))
    return placeholder(num, name)


@app.callback(
    [Output(f"nav-{num}", "style") for num, _ in MODULES],
    Input("active-module", "data"),
)
def highlight_nav(active):
    styles = []
    for num, _ in MODULES:
        if num == active:
            styles.append({"width":"100%","textAlign":"left","color":C["blue"],
                            "padding":"8px 20px","display":"flex","gap":"10px",
                            "alignItems":"center","borderRadius":"0","border":"none",
                            "backgroundColor":"rgba(76,201,240,0.1)",
                            "borderLeft":f"3px solid {C['blue']}"})
        else:
            styles.append({"width":"100%","textAlign":"left","color":C["text"],
                            "padding":"8px 20px","display":"flex","gap":"10px",
                            "alignItems":"center","borderRadius":"0","border":"none"})
    return styles


if __name__ == "__main__":
    print("SFIS Quant Course — starting on http://localhost:8050")
    app.run(debug=False, host="0.0.0.0", port=8050)
