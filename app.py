# -*- coding: utf-8 -*-
"""
SENLAB · Ammonia Properties Database
Thermophysical Properties of Ammonia Systems
"""
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.interpolate import RectBivariateSpline, griddata
from scipy.optimize import brentq

from lhv_calculator import render_lhv_page
from eos_recommender import render_eos_page

HERE = os.path.dirname(os.path.abspath(__file__))
ACCENT = "#c2410c"  # 그래프에서 '입력 조건'을 표시하는 색 (라이트 테마용 진한 주황)
PRIMARY = "#1e3a8a"  # 그래프 기본 선·막대 색 (남색; 흰 배경용)
LINE_SCALE = "Viridis"  # 등압·등온선 색 척도 (흰 배경에서 노란 구간을 피하려고 0–0.85만 사용)

# =====================================================================
# 페이지 설정
# =====================================================================
st.set_page_config(
    page_title="Ammonia Properties DB · SENLAB",
    page_icon=":material/science:",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "SENLAB · Sustainable Energy Network Lab. (Seoul National University)",
    },
)

# =====================================================================
# Data 1: 순수 NH3 증기압 (K, MPa)
# =====================================================================
TEXT_VP = """
| 240 | 0.1014 |
| 240 | 0.1041 |
| 241 | 0.1076 |
| 241 | 0.1103 |
| 242 | 0.1131 |
| 243 | 0.1165 |
| 243 | 0.1193 |
| 244 | 0.1227 |
| 244 | 0.1262 |
| 245 | 0.1296 |
| 245 | 0.1331 |
| 246 | 0.1365 |
| 246 | 0.1400 |
| 247 | 0.1441 |
| 248 | 0.1475 |
| 248 | 0.1517 |
| 249 | 0.1558 |
| 249 | 0.1600 |
| 250 | 0.1634 |
| 250 | 0.1682 |
| 251 | 0.1724 |
| 251 | 0.1765 |
| 252 | 0.1813 |
| 253 | 0.1855 |
| 253 | 0.1903 |
| 254 | 0.1951 |
| 254 | 0.1999 |
| 255 | 0.2048 |
| 255 | 0.2096 |
| 256 | 0.2151 |
| 256 | 0.2199 |
| 257 | 0.2255 |
| 258 | 0.2310 |
| 258 | 0.2365 |
| 259 | 0.2420 |
| 259 | 0.2475 |
| 260 | 0.2537 |
| 260 | 0.2592 |
| 261 | 0.2654 |
| 261 | 0.2717 |
| 262 | 0.2779 |
| 263 | 0.2841 |
| 263 | 0.2910 |
| 264 | 0.2972 |
| 264 | 0.3041 |
| 265 | 0.3110 |
| 265 | 0.3178 |
| 266 | 0.3254 |
| 266 | 0.3323 |
| 267 | 0.3399 |
| 268 | 0.3475 |
| 268 | 0.3551 |
| 269 | 0.3627 |
| 269 | 0.3702 |
| 270 | 0.3785 |
| 270 | 0.3868 |
| 271 | 0.3951 |
| 271 | 0.4033 |
| 272 | 0.4116 |
| 278 | 0.5054 |
| 283 | 0.6150 |
| 289 | 0.7419 |
| 294 | 0.8880 |
| 298 | 0.9860 |
| 298 | 1.00 |
| 299 | 1.02 |
| 299 | 1.04 |
| 300 | 1.05 |
| 300 | 1.07 |
| 301 | 1.09 |
| 301 | 1.11 |
| 302 | 1.13 |
| 303 | 1.15 |
| 303 | 1.17 |
| 304 | 1.19 |
| 304 | 1.21 |
| 305 | 1.23 |
| 305 | 1.25 |
| 306 | 1.27 |
| 306 | 1.29 |
| 307 | 1.31 |
| 308 | 1.33 |
| 308 | 1.35 |
| 309 | 1.37 |
| 309 | 1.39 |
| 310 | 1.42 |
| 310 | 1.44 |
| 311 | 1.46 |
| 311 | 1.48 |
| 312 | 1.51 |
| 313 | 1.53 |
| 313 | 1.55 |
| 314 | 1.58 |
| 314 | 1.60 |
| 315 | 1.63 |
| 315 | 1.65 |
| 316 | 1.68 |
| 316 | 1.70 |
| 317 | 1.73 |
| 318 | 1.75 |
| 318 | 1.78 |
| 319 | 1.81 |
| 319 | 1.84 |
| 320 | 1.86 |
| 320 | 1.89 |
| 321 | 1.92 |
| 321 | 1.95 |
| 322 | 1.97 |
| 330 | 2.42 |
| 350 | 3.87 |
| 370 | 5.88 |
| 390 | 8.60 |
| 400 | 10.3 |
| 405 | 11.3 |
"""

# =====================================================================
# Data 2: NH3 밀도 vs 온도 (°C, g/L)
# =====================================================================
TEXT_DENSITY = """
| -35 | 0.8843 |
| -10 | 0.7938 |
| 0 | 0.7625 |
| 10 | 0.7336 |
| 20 | 0.7069 |
| 30 | 0.6822 |
| 40 | 0.6593 |
| 50 | 0.6380 |
| 75 | 0.5909 |
| 100 | 0.5509 |
| 125 | 0.5162 |
| 150 | 0.4858 |
| 175 | 0.4586 |
| 200 | 0.4341 |
| 250 | 0.3917 |
| 300 | 0.3573 |
| 350 | 0.3295 |
| 400 | 0.3058 |
"""


def _parse(text):
    rows = []
    for line in text.strip().splitlines():
        a, b = line.strip("| ").split(" | ")
        rows.append((float(a), float(b)))
    return pd.DataFrame(rows, columns=["x", "y"])


_vp = _parse(TEXT_VP).groupby("x", as_index=False)["y"].mean()
VP_T = _vp["x"].to_numpy()
VP_P = _vp["y"].to_numpy()
VP_T_MIN, VP_T_MAX = float(VP_T[0]), float(VP_T[-1])
VP_P_MIN, VP_P_MAX = float(VP_P[0]), float(VP_P[-1])

_den = _parse(TEXT_DENSITY)
DEN_T = (_den["x"] + 273.15).to_numpy()
DEN_RHO = _den["y"].to_numpy()
DEN_T_MIN, DEN_T_MAX = float(DEN_T[0]), float(DEN_T[-1])


def p_sat(T):
    return float(np.interp(T, VP_T, VP_P))


def t_sat(P):
    return float(np.interp(P, VP_P, VP_T))


def rho_nh3(T_K):
    return float(np.interp(T_K, DEN_T, DEN_RHO))


# =====================================================================
# Data 3: Shomate (NIST)
# =====================================================================
SH_A, SH_B, SH_C, SH_D, SH_E, SH_F, SH_G, SH_H = (
    19.99563, 49.77119, -15.37599, 1.921168, 0.189174, -53.30667, 203.8591, -45.89806,
)


def shomate(T):
    t = np.asarray(T, dtype=float) / 1000.0
    Cp = SH_A + SH_B * t + SH_C * t**2 + SH_D * t**3 + SH_E / t**2
    dH = SH_A * t + SH_B * t**2 / 2 + SH_C * t**3 / 3 + SH_D * t**4 / 4 - SH_E / t + SH_F - SH_H
    S = SH_A * np.log(t) + SH_B * t + SH_C * t**2 / 2 + SH_D * t**3 / 3 - SH_E / (2 * t**2) + SH_G
    return Cp, dH, S


SHOMATE_MD = r"""
**Shomate 방정식** ($t = T/1000$)

$$C_p^{o} = A + Bt + Ct^{2} + Dt^{3} + \frac{E}{t^{2}}$$

$$H^{o} - H^{o}_{298.15} = At + \frac{Bt^{2}}{2} + \frac{Ct^{3}}{3} + \frac{Dt^{4}}{4} - \frac{E}{t} + F - H$$

$$S^{o} = A\ln t + Bt + \frac{Ct^{2}}{2} + \frac{Dt^{3}}{3} - \frac{E}{2t^{2}} + G$$

| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| 19.99563 | 49.77119 | −15.37599 | 1.921168 | 0.189174 | −53.30667 | 203.8591 | −45.89806 |

출처: [NIST Chemistry WebBook](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7664417&Mask=1&Type=JANAFG&Table=on#ref-1) · Data last reviewed June 1977
"""

# =====================================================================
# Data 4: 이성분 혼합물 설정
# =====================================================================
MIX_CFG = {
    "NH₃ + H₂": dict(
        file="nh3+h2_modified.csv", sym="H_2", mw=2.016,
        dew_method="cubic", bubble_method="cubic",
        T_range=(277.6, 394.2), ylim=(279.9, 400.1), zoom_x=(0.95, 1.0),
        T_default=330.0, x_default=0.7,
        ref=("Phase Behavior in the Hydrogen-Ammonia System (Reamer et al.)",
             "https://doi.org/10.1021/je60002a012"),
    ),
    "NH₃ + N₂": dict(
        file="nh3+n2.csv", sym="N_2", mw=28.014,
        dew_method="linear", bubble_method="cubic",
        T_range=(277.6, 394.2), ylim=(279.9, 400.1), zoom_x=(0.85, 1.0),
        T_default=330.0, x_default=0.7,
        ref=("Phase Behavior in the Nitrogen-Ammonia System (Reamer et al.)",
             "https://pubs.acs.org/doi/pdf/10.1021/je60004a005"),
    ),
    "NH₃ + CH₄": dict(
        file="nh3+ch4.csv", sym="CH_4", mw=16.04,
        dew_method="linear", bubble_method="cubic",
        T_range=(273.15, 373.15), ylim=(273.15, 373.15), zoom_x=(0.0, 1.0),
        T_default=320.0, x_default=0.4,
        ref=("P, V, T, x values of the gas-liquid phase equilibria in the binary system methane-ammonia at high pressures (Lentz et al.)",
             "https://www.sciencedirect.com/science/article/pii/0378381294870195"),
    ),
}

CONVERSION_MD = r"""
문헌은 NH₃ **몰분율** 기준이므로 아래 식으로 **질량분율**로 환산했습니다.

$$x_{NH_3} = 1 - x_{__SYM__}$$

$$w_{NH_3} = \frac{x_{NH_3}\, MW_{NH_3}}{x_{__SYM__}\, MW_{__SYM__} + x_{NH_3}\, MW_{NH_3}}$$

- $MW_{NH_3}$ = 17.031 g/mol · $MW_{__SYM__}$ = __MW__ g/mol
"""


@st.cache_data(show_spinner=False)
def load_binary(file, mw_partner):
    df = pd.read_csv(os.path.join(HERE, file))
    mw_nh3 = 17.031
    df["T_Kel"] = round((df["T_F"] - 32) * (5 / 9) + 273.15, 3)
    df["P_MPa"] = round(df["P_psi"] * 0.00689476, 3)
    df["DewP_NH3"] = 1 - df["DewP"]
    df["BubbleP_NH3"] = 1 - df["BubbleP"]
    df["DewP_NH3_mass"] = (df["DewP_NH3"] * mw_nh3) / (df["DewP"] * mw_partner + df["DewP_NH3"] * mw_nh3)
    df["BubbleP_NH3_mass"] = (df["BubbleP_NH3"] * mw_nh3) / (df["BubbleP"] * mw_partner + df["BubbleP_NH3"] * mw_nh3)
    return df


@st.cache_data(show_spinner="내삽 격자 계산 중…")
def binary_grid(file, mw_partner, dew_method, bubble_method, T_range):
    df = load_binary(file, mw_partner)
    T_axis = np.linspace(T_range[0], T_range[1], 1000)
    x_axis = np.linspace(0.0, 1.0, 1000)
    X, TT = np.meshgrid(x_axis, T_axis)
    dew = griddata((df["T_Kel"], df["DewP_NH3_mass"]), df["P_MPa"], (TT, X), method=dew_method)
    bub = griddata((df["T_Kel"], df["BubbleP_NH3_mass"]), df["P_MPa"], (TT, X), method=bubble_method)
    return T_axis, x_axis, dew, bub


@st.cache_data(show_spinner=False)
def load_h2o():
    bubble = pd.read_csv(os.path.join(HERE, "NH3+H2O_bubbleline.csv"), index_col=0) + 273.15
    dew = pd.read_csv(os.path.join(HERE, "NH3+H2O_dewline.csv"), index_col=0) + 273.15
    return bubble, dew


# =====================================================================
# 공통 UI 헬퍼
# =====================================================================
def panels():
    """왼쪽 입력/결과 · 오른쪽 그래프 (주식 앱과 같은 배치)"""
    return st.columns([1, 2.3], gap="medium")


def _fmt(v, unit, nd=2):
    return "—" if v is None or np.isnan(v) else f"{v:.{nd}f} {unit}"


def line_chart(x, y, x_title, y_title, point=None, name="문헌값", mode="lines+markers", height=420):
    fig = go.Figure()
    fig.add_scatter(x=x, y=y, mode=mode, name=name, marker=dict(size=7, color=PRIMARY), line=dict(width=2.5, color=PRIMARY))
    if point is not None and not np.isnan(point[1]):
        fig.add_scatter(
            x=[point[0]], y=[point[1]], mode="markers", name="입력 조건",
            marker=dict(size=14, symbol="diamond", color=ACCENT, line=dict(width=1.5, color="white")),
        )
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=x_title, yaxis_title=y_title, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def _nearest_T(col, P, T_axis):
    d = np.abs(col - P)
    return np.nan if np.all(np.isnan(d)) else float(T_axis[np.nanargmin(d)])


# =====================================================================
# 페이지 1: 증기압
# =====================================================================
def page_vapor_pressure():
    left, right = panels()
    with left.container(border=True):
        st.markdown("**조건 입력**")
        known = st.radio("알고 있는 값", ["온도", "압력"], horizontal=True, key="vp_known")
        if known == "온도":
            T = st.number_input("온도 (K)", VP_T_MIN, VP_T_MAX, 300.0, step=1.0, format="%.1f", key="vp_T")
            P = p_sat(T)
        else:
            P = st.number_input("압력 (MPa)", VP_P_MIN, VP_P_MAX, 1.0, step=0.05, format="%.4f", key="vp_P")
            T = t_sat(P)
        st.caption(f"유효 범위 {VP_T_MIN:.0f}–{VP_T_MAX:.0f} K · {VP_P_MIN:.3f}–{VP_P_MAX:.1f} MPa · 문헌값 선형 보간")
    with left.container(border=True):
        m1, m2 = st.columns(2)
        m1.metric("온도", f"{T:.1f} K")
        m2.metric("포화 증기압", f"{P:.4f} MPa")
    with right.container(border=True, height="stretch"):
        fig = line_chart(VP_T, VP_P, "Temperature (K)", "Pressure (MPa)", point=(T, P))
        st.plotly_chart(fig, width="stretch", key="vp_chart")


# =====================================================================
# 페이지 2: 밀도
# =====================================================================
def page_density():
    left, right = panels()
    with left.container(border=True):
        st.markdown("**조건 입력**")
        unit = st.radio("온도 단위", ["K", "°C"], horizontal=True, key="den_unit")
        if unit == "K":
            T_K = st.number_input("온도 (K)", DEN_T_MIN, DEN_T_MAX, 298.15, step=1.0, format="%.2f", key="den_TK")
        else:
            T_C = st.number_input("온도 (°C)", DEN_T_MIN - 273.15, DEN_T_MAX - 273.15, 25.0, step=1.0, format="%.1f", key="den_TC")
            T_K = T_C + 273.15
        rho = rho_nh3(T_K)
        st.caption(f"유효 범위 {DEN_T_MIN - 273.15:.0f}–{DEN_T_MAX - 273.15:.0f} °C · 문헌값 선형 보간")
    with left.container(border=True):
        m1, m2 = st.columns(2)
        m1.metric("온도", f"{T_K:.2f} K")
        m2.metric("밀도", f"{rho:.4f} g/L")
    with right.container(border=True, height="stretch"):
        fig = line_chart(DEN_T, DEN_RHO, "Temperature (K)", "Density (g/L)", point=(T_K, rho))
        st.plotly_chart(fig, width="stretch", key="den_chart")


# =====================================================================
# 페이지 3: 비열 (Shomate)
# =====================================================================
def page_specific_heat():
    left, right = panels()
    with left.container(border=True):
        st.markdown("**조건 입력**")
        T = st.number_input("온도 (K)", 200.0, 1400.0, 300.0, step=10.0, format="%.0f", key="sh_T")
        st.caption("Shomate 방정식 (NIST) · 200–1400 K")
    Cp, dH, S = shomate(T)
    with left.container(border=True):
        m1, m2, m3 = st.columns(3)
        m1.metric("Cp° (J/mol·K)", f"{Cp:.2f}")
        m2.metric("ΔH (kJ/mol)", f"{dH:.2f}", help="H° − H°(298.15 K)")
        m3.metric("S° (J/mol·K)", f"{S:.2f}")
    with right.container(border=True, height="stretch"):
        T_range = np.arange(200, 1401, 1)
        Cp_v, dH_v, S_v = shomate(T_range)
        tabs = st.tabs(["Cp°", "ΔH", "S°"])
        series = [
            ("Cp", Cp_v, Cp, "Cp° (J/mol·K)"),
            ("dH", dH_v, dH, "ΔH = H° − H°₂₉₈ (kJ/mol)"),
            ("S", S_v, S, "S° (J/mol·K)"),
        ]
        for tab, (key, ys, yv, ylabel) in zip(tabs, series):
            with tab:
                fig = line_chart(T_range, ys, "Temperature (K)", ylabel, point=(T, yv), name=ylabel, mode="lines", height=380)
                fig.add_vline(x=T, line_dash="dot", line_color=ACCENT, opacity=0.6)
                fig.add_hline(y=yv, line_dash="dot", line_color=ACCENT, opacity=0.6)
                st.plotly_chart(fig, width="stretch", key=f"sh_chart_{key}")
    with st.expander("Shomate 방정식 · 계수 · 출처", icon=":material/functions:"):
        st.markdown(SHOMATE_MD)


# =====================================================================
# 페이지 4: 이슬점 · 거품점
# =====================================================================
def page_pure_nh3():
    left, right = panels()
    with left.container(border=True):
        st.markdown("**조건 입력**")
        known = st.radio("알고 있는 값", ["압력", "온도"], horizontal=True, key="pure_known")
        if known == "압력":
            P = st.number_input("압력 (MPa)", VP_P_MIN, VP_P_MAX, 1.0, step=0.05, format="%.4f", key="pure_P")
            T = t_sat(P)
            result = [("이슬점 온도", f"{T:.2f} K"), ("거품점 온도", f"{T:.2f} K")]
        else:
            T = st.number_input("온도 (K)", VP_T_MIN, VP_T_MAX, 300.0, step=1.0, format="%.1f", key="pure_T")
            P = p_sat(T)
            result = [("이슬점 압력", f"{P:.4f} MPa"), ("거품점 압력", f"{P:.4f} MPa")]
        st.caption("순수 물질은 거품점과 이슬점이 같습니다 (증기압 곡선).")
    with left.container(border=True):
        m1, m2 = st.columns(2)
        m1.metric(*result[0])
        m2.metric(*result[1])
    with right.container(border=True, height="stretch"):
        fig = line_chart(VP_T, VP_P, "Temperature (K)", "Pressure (MPa)", point=(T, P))
        st.plotly_chart(fig, width="stretch", key="pure_chart")


def page_nh3_h2o():
    bubble, dew = load_h2o()
    x = bubble.index.values.astype(float)
    p_b = bubble.columns.values.astype(float)
    p_d = dew.columns.values.astype(float)
    sp_b = RectBivariateSpline(x, p_b, bubble.values)
    sp_d = RectBivariateSpline(x, p_d, dew.values)

    def pressure_at(T, xn, spline):
        try:
            return float(brentq(lambda P: spline(xn, P, grid=False) - T, 0.0, 10.0))
        except ValueError:
            return np.nan

    st.caption("출처: [Development of thermo-physical properties of aqua ammonia for Kalina cycle system (Ganesh et al.)](https://doi.org/10.1504/IJMPT.2017.084955)")
    left, right = panels()
    with left.container(border=True):
        st.markdown("**조건 입력**")
        known = st.radio("알고 있는 값", ["온도", "압력"], horizontal=True, key="h2o_known")
        xn = st.number_input("NH₃ 질량분율 (0–1)", 0.0, 1.0, 0.5, step=0.01, format="%.2f", key="h2o_x")
        if known == "온도":
            T = st.number_input("온도 (K)", 220.0, 560.0, 300.0, step=1.0, format="%.1f", key="h2o_T")
            P_b, P_d = pressure_at(T, xn, sp_b), pressure_at(T, xn, sp_d)
            result = [("거품점 압력", _fmt(P_b, "MPa")), ("이슬점 압력", _fmt(P_d, "MPa"))]
            marks = [(xn, T)]
        else:
            P = st.number_input("압력 (MPa)", 0.0, 10.0, 1.0, step=0.1, format="%.2f", key="h2o_P")
            T_b = float(sp_b(xn, P, grid=False))
            T_d = float(sp_d(xn, P, grid=False))
            result = [("거품점 온도", _fmt(T_b, "K")), ("이슬점 온도", _fmt(T_d, "K"))]
            marks = [(xn, T_b), (xn, T_d)]
        st.caption("유효 범위 220–560 K · 0–10 MPa · 2차원 스플라인 보간")
    with left.container(border=True):
        m1, m2 = st.columns(2)
        m1.metric(*result[0])
        m2.metric(*result[1])
        if any(v == "—" for _, v in result):
            st.warning("이 조건에서는 문헌 데이터 범위를 벗어나 값을 찾을 수 없어요.")
    with right.container(border=True, height="stretch"):
        n = max(len(p_b), len(p_d), 2)
        colors = px.colors.sample_colorscale(LINE_SCALE, [0.85 * i / max(n - 1, 1) for i in range(n)])
        fig = go.Figure()
        for i, col in enumerate(bubble.columns):
            fig.add_scatter(x=x, y=bubble[col], mode="lines", name=f"{float(col):g} MPa",
                            legendgroup=str(col), line=dict(color=colors[i], width=2))
        for i, col in enumerate(dew.columns):
            fig.add_scatter(x=x, y=dew[col], mode="lines", name=f"{float(col):g} MPa (dew)",
                            legendgroup=str(col), showlegend=False,
                            line=dict(color=colors[i], width=2, dash="dot"))
        pts = [(a, b) for a, b in marks if not np.isnan(b)]
        if pts:
            fig.add_scatter(x=[a for a, _ in pts], y=[b for _, b in pts], mode="markers", name="입력 조건",
                            marker=dict(size=14, symbol="diamond", color=ACCENT, line=dict(width=1.5, color="white")))
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis_title="NH₃ mass fraction", yaxis_title="Temperature (K)",
                          legend=dict(title="Pressure", orientation="v"))
        st.plotly_chart(fig, width="stretch", key="h2o_chart")
        st.caption("실선 = 거품점 · 점선 = 이슬점")


def page_binary(name, cfg):
    df = load_binary(cfg["file"], cfg["mw"])
    T_axis, x_axis, dew_grid, bub_grid = binary_grid(
        cfg["file"], cfg["mw"], cfg["dew_method"], cfg["bubble_method"], cfg["T_range"]
    )
    st.caption(f"출처: [{cfg['ref'][0]}]({cfg['ref'][1]}) · 몰분율 → 질량분율 환산 · 1000×1000 격자 내삽")

    # ---- 상단: 입력 · 결과 · 문헌 P-x 그래프
    left, right = panels()
    with left.container(border=True):
        st.markdown("**조건 입력**")
        known = st.radio("알고 있는 값", ["온도", "압력"], horizontal=True, key=f"bin_known_{cfg['file']}")
        x_nh3 = st.number_input("NH₃ 질량분율 (0–1)", 0.0, 1.0, cfg["x_default"], step=0.01, format="%.2f", key=f"bin_x_{cfg['file']}")
        xi = int(np.abs(x_axis - x_nh3).argmin())
        if known == "온도":
            T = st.number_input("온도 (K)", float(T_axis[0]), float(T_axis[-1]), cfg["T_default"], step=1.0, format="%.1f", key=f"bin_T_{cfg['file']}")
            ti = int(np.abs(T_axis - T).argmin())
            p_dew, p_bub = float(dew_grid[ti, xi]), float(bub_grid[ti, xi])
            result = [("이슬점 압력", _fmt(p_dew, "MPa")), ("거품점 압력", _fmt(p_bub, "MPa"))]
            marks = [(x_nh3, T)]
        else:
            P = st.number_input("압력 (MPa)", 0.0, 40.0, 10.0, step=0.5, format="%.2f", key=f"bin_P_{cfg['file']}")
            T_dew = _nearest_T(dew_grid[:, xi], P, T_axis)
            T_bub = _nearest_T(bub_grid[:, xi], P, T_axis)
            result = [("이슬점 온도", _fmt(T_dew, "K")), ("거품점 온도", _fmt(T_bub, "K"))]
            marks = [(x_nh3, T_dew), (x_nh3, T_bub)]
        st.caption(f"유효 범위 {T_axis[0]:.1f}–{T_axis[-1]:.1f} K · 격자에서 가장 가까운 값")
    with left.container(border=True):
        m1, m2 = st.columns(2)
        m1.metric(*result[0])
        m2.metric(*result[1])
        if any(v == "—" for _, v in result):
            st.warning("이 조건에서는 문헌 데이터 범위를 벗어나 값을 찾을 수 없어요.")
    with right.container(border=True, height="stretch"):
        temps = sorted(df["T_Kel"].unique())
        n = max(len(temps), 2)
        colors = px.colors.sample_colorscale(LINE_SCALE, [0.85 * i / max(n - 1, 1) for i in range(n)])
        fig = go.Figure()
        for c, t in zip(colors, temps):
            d = df[df["T_Kel"] == t]
            fig.add_scatter(x=d["DewP_NH3_mass"], y=d["P_MPa"], mode="markers", name=f"{t:.1f} K",
                            legendgroup=str(t), marker=dict(symbol="circle", size=8, color=c))
            fig.add_scatter(x=d["BubbleP_NH3_mass"], y=d["P_MPa"], mode="markers", name=f"{t:.1f} K (bubble)",
                            legendgroup=str(t), showlegend=False, marker=dict(symbol="diamond", size=8, color=c))
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis_title="NH₃ mass fraction", yaxis_title="Pressure (MPa)",
                          xaxis=dict(range=[0, 1]), legend=dict(title="Temperature"))
        st.plotly_chart(fig, width="stretch", key=f"bin_px_{cfg['file']}")
        st.caption("● 이슬점 · ◆ 거품점 (문헌 실측값)")

    # ---- 하단: 내삽 히트맵
    with st.container(border=True):
        st.markdown(f"**{name} · 내삽 상평형도** (색 = 압력, MPa)")
        step = 5  # 표시용 다운샘플 (계산 격자는 1000×1000 그대로)
        fig = make_subplots(rows=1, cols=2, subplot_titles=("P_dew", "P_bubble"), horizontal_spacing=0.1)
        fig.add_trace(go.Heatmap(z=dew_grid[::step, ::step], x=x_axis[::step], y=T_axis[::step], coloraxis="coloraxis",
                                 hovertemplate="x=%{x:.3f}<br>T=%{y:.1f} K<br>P=%{z:.2f} MPa<extra>dew</extra>"), row=1, col=1)
        fig.add_trace(go.Heatmap(z=bub_grid[::step, ::step], x=x_axis[::step], y=T_axis[::step], coloraxis="coloraxis",
                                 hovertemplate="x=%{x:.3f}<br>T=%{y:.1f} K<br>P=%{z:.2f} MPa<extra>bubble</extra>"), row=1, col=2)
        pts = [(a, b) for a, b in marks if not np.isnan(b)]
        for c_ in (1, 2):
            if pts:
                fig.add_trace(go.Scatter(x=[a for a, _ in pts], y=[b for _, b in pts], mode="markers", showlegend=(c_ == 1),
                                         name="입력 조건", marker=dict(size=13, symbol="diamond", color=ACCENT, line=dict(width=1.5, color="white"))),
                              row=1, col=c_)
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=40, b=10),
                          coloraxis=dict(colorscale="Plasma", cmin=0, cmax=40, colorbar=dict(title="P (MPa)")))
        fig.update_xaxes(title_text="NH₃ mass fraction", range=[0, 1], row=1, col=1)
        fig.update_xaxes(title_text="NH₃ mass fraction", range=list(cfg["zoom_x"]), row=1, col=2)
        fig.update_yaxes(title_text="Temperature (K)", range=list(cfg["ylim"]))
        st.plotly_chart(fig, width="stretch", key=f"bin_heat_{cfg['file']}")

    # ---- 부가 정보
    c1, c2 = st.columns(2)
    with c1:
        with st.expander("가공된 문헌 데이터 보기", icon=":material/table_chart:"):
            st.dataframe(df, hide_index=True, width="stretch")
    with c2:
        with st.expander("몰분율 → 질량분율 환산 과정", icon=":material/calculate:"):
            st.markdown(CONVERSION_MD.replace("__SYM__", cfg["sym"]).replace("__MW__", f"{cfg['mw']:g}"))
        key = cfg["file"]
        if st.button("내삽 격자 CSV 생성 (약 45 MB)", key=f"gen_{key}", icon=":material/dataset:"):
            X, TT = np.meshgrid(x_axis, T_axis)
            st.session_state[f"csv_{key}"] = pd.DataFrame(
                {"T_Kel": TT.ravel(), "x_nh3": X.ravel(), "DewP": dew_grid.ravel(), "BubbleP": bub_grid.ravel()}
            ).to_csv(index=False).encode("utf-8")
        if f"csv_{key}" in st.session_state:
            st.download_button("⬇ CSV 다운로드", st.session_state[f"csv_{key}"],
                               file_name=key.replace(".csv", "") + "_interpolated.csv", mime="text/csv", key=f"dl_{key}")


def page_dew_bubble():
    sub = st.segmented_control(
        "혼합물", ["순수 NH₃", "NH₃ + H₂O", "NH₃ + H₂", "NH₃ + N₂", "NH₃ + CH₄"],
        default="순수 NH₃", key="db_sub",
    )
    sub = sub or "순수 NH₃"
    if sub == "순수 NH₃":
        page_pure_nh3()
    elif sub == "NH₃ + H₂O":
        page_nh3_h2o()
    else:
        page_binary(sub, MIX_CFG[sub])


# =====================================================================
# 헤더 · 사이드바 · 라우팅
# =====================================================================
hl, hr = st.columns([6, 1], vertical_alignment="center")
with hl:
    st.title(":material/science: Thermophysical Properties of Ammonia Systems")
    st.caption("SENLAB · Sustainable Energy Network Lab. — 암모니아 및 혼합물(H₂O, H₂, N₂, CH₄)의 주요 물성을 문헌 데이터 기반으로 검색하고 시각화합니다.")
with hr:
    st.link_button("About Lab", "https://sensr.snu.ac.kr/", icon=":material/open_in_new:", width="stretch")

with st.expander("이 데이터베이스에 대해 · 사용 방법", icon=":material/info:"):
    a, b = st.columns(2)
    a.markdown("""
**What's included**
- 증기압 (Vapor Pressure) — 특정 온도에서 액체와 평형을 이루는 포화 증기의 압력
- 밀도 (Density) — 온도에 따른 단위 부피당 질량
- 비열 (Specific Heat) — Shomate 방정식 기반 Cp°, ΔH, S°
- 이슬점 / 거품점 (Dew / Bubble Point) — 순수 NH₃ 및 H₂O·H₂·N₂·CH₄ 이성분계
- NH₃·H₂ 혼소 연료 발열량 · EOS 추천
""")
    b.markdown("""
**How to use**
1. 아래에서 물성을 선택하고
2. 왼쪽 카드에 온도·압력·조성 조건을 입력하면
3. 값(카드)과 그래프(오른쪽)가 즉시 갱신됩니다. 그래프 위 ◆ 가 입력 조건입니다.
""")

with st.sidebar:
    st.markdown("""
### SENLAB
[Sustainable Energy Network Lab. Homepage](https://sensr.snu.ac.kr/)

### Contributors
- 고우진 (woojingo@snu.ac.kr)
- 민채림 (asd578300@snu.ac.kr)
- 정건우 (gw.jeong@snu.ac.kr)
- 강태현 (kang990925@pusan.ac.kr)

### Supervisor
- 서유택 (yutaek.seo@snu.ac.kr)
""")

PAGES = {
    "증기압": page_vapor_pressure,
    "밀도": page_density,
    "비열 (Shomate)": page_specific_heat,
    "이슬점 · 거품점": page_dew_bubble,
    "NH₃·H₂ 혼소 발열량": render_lhv_page,
    "EOS 추천 (이성분계)": render_eos_page,
}

st.caption("물성 선택")
prop = st.pills("물성", list(PAGES), default="증기압", label_visibility="collapsed", key="prop")
if prop is None:
    st.info("위에서 물성을 하나 선택하세요.", icon=":material/touch_app:")
    st.stop()

PAGES[prop]()
