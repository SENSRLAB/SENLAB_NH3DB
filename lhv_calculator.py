# -*- coding: utf-8 -*-
"""
Ammonia–hydrogen fuel-blend heating value (LHV) and density calculator
- Fuel state: vapour / liquid
  · vapour: NH3 vapour + H2 gas mixture -> LHV and density as a function of composition and temperature
  · liquid: pure liquid NH3 (H2 is liquid only below -240 C, so an H2 fraction is meaningless in storage)
- Output: standard LHV (headline) + density / effective LHV / volumetric energy + CSV download

Data: NIST pure-component properties (nh3_h2_blend_data.csv, -50 to 130 C)
Call render_lhv_page() from app.py.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np

# ============================================================
# 1) Constants
# ============================================================
LHV_NH3_STD = 18.6      # MJ/kg
LHV_H2_STD  = 120.0     # MJ/kg
H_REF_NH3   = 1629.0    # kJ/kg  (NH3 saturated-vapour enthalpy at 25 C)
H_REF_H2    = 3931.5    # kJ/kg  (H2 enthalpy at 25 C)
M_NH3       = 17.031    # g/mol
M_H2        = 2.016     # g/mol

# ============================================================
# 2) Data
# ============================================================
_HERE = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data(path=None):
    if path is None:
        path = os.path.join(_HERE, "nh3_h2_blend_data.csv")
    return pd.read_csv(path)

def _interp(df, T, col):
    return float(np.interp(T, df["T_C"], df[col]))

# ============================================================
# 3) Calculation
# ============================================================
def compute_blend(df, w_H2, T, x):
    """
    w_H2 : hydrogen mass fraction (0-1)
    T    : temperature (C)
    x    : 0 = liquid state (pure NH3 basis), 1 = vapour mixture
    """
    w_NH3 = 1.0 - w_H2
    rho_liq = _interp(df, T, "rho_liq_NH3")
    rho_vap = _interp(df, T, "rho_vap_NH3")
    h_liq   = _interp(df, T, "h_liq_NH3")
    h_vap   = _interp(df, T, "h_vap_NH3")
    rho_H2  = _interp(df, T, "rho_H2")
    h_H2    = _interp(df, T, "h_H2_kJkg")
    P_sat   = _interp(df, T, "P_sat_bar")

    # NH3 state (x=0 liquid, x=1 vapour)
    v_NH3   = (1 - x) / rho_liq + x / rho_vap
    rho_NH3 = 1.0 / v_NH3
    h_NH3   = (1 - x) * h_liq + x * h_vap

    lhv_std = w_H2 * LHV_H2_STD + w_NH3 * LHV_NH3_STD

    lhv_eff_NH3 = LHV_NH3_STD + (h_NH3 - H_REF_NH3) / 1000.0
    lhv_eff_H2  = LHV_H2_STD  + (h_H2  - H_REF_H2)  / 1000.0
    lhv_eff     = w_H2 * lhv_eff_H2 + w_NH3 * lhv_eff_NH3

    if w_H2 <= 0:
        rho_mix = rho_NH3
    elif w_NH3 <= 0:
        rho_mix = rho_H2
    else:
        rho_mix = 1.0 / (w_H2 / rho_H2 + w_NH3 / rho_NH3)

    vol_energy = lhv_std * rho_mix / 1000.0  # MJ/L

    return {"lhv_std": lhv_std, "lhv_eff": lhv_eff,
            "rho_mix": rho_mix, "vol_energy": vol_energy, "P_sat": P_sat}

# ============================================================
# Helpers
# ============================================================
def _slider_input(label, lo, hi, default, step, key):
    """Slider and number input kept in sync."""
    sk, nk = f"{key}__s", f"{key}__n"
    if sk not in st.session_state:
        st.session_state[sk] = default
        st.session_state[nk] = default

    def _from_s():
        st.session_state[nk] = st.session_state[sk]

    def _from_n():
        st.session_state[sk] = st.session_state[nk]

    st.markdown(f"**{label}**")
    c1, c2 = st.columns([3, 1])
    c1.slider(label, lo, hi, step=step, key=sk,
              on_change=_from_s, label_visibility="collapsed")
    c2.number_input(label, lo, hi, step=step, key=nk,
                    on_change=_from_n, label_visibility="collapsed")
    return st.session_state[sk]

def _temp_input():
    t_unit = st.radio("Temperature unit", ["°C", "K"], horizontal=True)
    if t_unit == "°C":
        return _slider_input("Temperature (°C)", -50.0, 130.0, 25.0, 1.0, "t_c")
    return _slider_input("Temperature (K)", 223.15, 403.15, 298.15, 1.0, "t_k") - 273.15

def _mole_to_mass(y_H2):
    den = y_H2 * M_H2 + (1 - y_H2) * M_NH3
    return (y_H2 * M_H2) / den if den > 0 else 0.0

def _mass_to_mole(w_H2):
    den = w_H2 / M_H2 + (1 - w_H2) / M_NH3
    return (w_H2 / M_H2) / den if den > 0 else 0.0

def _styled_axes(fig, x_title, y1_title, y1_color, y2_title, y2_color, title):
    """Common Plotly styling (black axes, legend below)."""
    axis_common = dict(showline=True, linecolor="black", linewidth=1.5,
                       ticks="outside", tickcolor="black",
                       tickfont=dict(size=14, color="black"))
    fig.update_xaxes(title_text=x_title, title_font=dict(size=16, color="black"),
                     showgrid=True, gridcolor="#ECECEC", **axis_common)
    fig.update_yaxes(title_text=y1_title, title_font=dict(size=16, color=y1_color),
                     showgrid=True, gridcolor="#ECECEC", secondary_y=False, **axis_common)
    fig.update_yaxes(title_text=y2_title, title_font=dict(size=16, color=y2_color),
                     showgrid=False, secondary_y=True, **axis_common)
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="black"), x=0.02, xanchor="left"),
        hovermode="x unified",
        height=480, margin=dict(l=10, r=10, t=55, b=85),
        font=dict(size=14, color="black"), plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="top", y=-0.22,
                    xanchor="center", x=0.5, font=dict(size=13, color="black")),
    )
    return fig

# ============================================================
# 4) Page UI
# ============================================================
def render_lhv_page():
    # 18 px base font on this page
    st.markdown("<style>html { font-size: 18px; }</style>", unsafe_allow_html=True)

    st.markdown("## NH₃–H₂ Fuel-Blend Heating Value Calculator")
    st.caption("Choose the fuel state, then enter the hydrogen fraction and temperature to get the heating value and density.")

    df = load_data()

    # ----- fuel state -----
    mode = st.radio("Fuel state", ["Vapour (combustion)", "Liquid (storage)"],
                    horizontal=True, index=0,
                    help="An NH₃–H₂ gas mixture at the burner; liquid ammonia in storage.")
    is_gas = mode.startswith("Vapour")

    if is_gas:
        # composition
        basis = st.radio("Hydrogen fraction basis", ["mass fraction", "mole fraction"], horizontal=True)
        frac_pct = _slider_input(f"Hydrogen fraction ({basis}, %)", 0.0, 100.0, 0.0, 0.1, "h2")
        frac = frac_pct / 100.0
        if basis == "mole fraction":
            w_H2 = _mole_to_mass(frac)
            conv = f"→ mass fraction H₂ {w_H2*100:.1f}% / NH₃ {(1-w_H2)*100:.1f}%"
        else:
            w_H2 = frac
            y = _mass_to_mole(w_H2)
            conv = f"→ mole fraction H₂ {y*100:.1f}% / NH₃ {(1-y)*100:.1f}%"
        st.caption(f"Ammonia {basis}: **{100-frac_pct:.1f}%**   ·   {conv}")
        T = _temp_input()
        x = 1.0  # vapour mixture
    else:  # liquid (storage)
        st.info("In the liquid state only **pure ammonia** is present.\n\n"
                "Hydrogen's critical temperature is −240 °C, so it cannot be liquid anywhere in this range (−50 to 130 °C); "
                "**the H₂ fraction is therefore not considered.**")
        w_H2 = 0.0
        T = _temp_input()
        x = 0.0  # pure liquid NH3

    # ----- calculation -----
    r = compute_blend(df, w_H2, T, x)

    # ----- output -----
    st.markdown("### Results")
    st.caption("Key figures — LHV per mass · energy per volume")
    k1, k2 = st.columns(2)
    k1.metric("Standard LHV (per mass)", f"{r['lhv_std']:.2f} MJ/kg",
              help="Energy released by burning 1 kg of fuel. Fixed by the composition, independent of temperature.")
    k2.metric("Volumetric energy", f"{r['vol_energy']:.3f} MJ/L",
              help="Energy per unit volume: standard LHV × density.")

    st.caption("Secondary figures")
    s1, s2 = st.columns(2)
    s1.metric("Density", f"{r['rho_mix']:.2f} kg/m³")
    s2.metric("Effective LHV", f"{r['lhv_eff']:.2f} MJ/kg",
              help="Standard LHV corrected for the fuel temperature and state (reference: vapour at 25 °C).")

    if is_gas:
        st.caption(
            f"Input summary — vapour · H₂ (mass) {w_H2*100:.1f}% / NH₃ {(1-w_H2)*100:.1f}% · "
            f"{T:.1f} °C · (NH₃ saturation pressure ≈ {r['P_sat']:.2f} bar)"
        )
    else:
        st.caption(f"Input summary — liquid storage · pure NH₃ · {T:.1f} °C · "
                   f"(saturation pressure ≈ {r['P_sat']:.2f} bar)")

    # ----- CSV download -----
    rows = [
        ("Fuel state", "vapour (combustion)" if is_gas else "liquid (storage)"),
        ("H2 mass fraction (%)", f"{w_H2*100:.2f}"),
        ("NH3 mass fraction (%)", f"{(1-w_H2)*100:.2f}"),
        ("Temperature (C)", f"{T:.1f}"),
        ("Standard LHV (MJ/kg)", f"{r['lhv_std']:.3f}"),
        ("Effective LHV (MJ/kg)", f"{r['lhv_eff']:.3f}"),
        ("Density (kg/m3)", f"{r['rho_mix']:.4f}"),
        ("Volumetric energy (MJ/L)", f"{r['vol_energy']:.4f}"),
        ("NH3 saturation pressure (bar)", f"{r['P_sat']:.3f}"),
    ]
    csv_str = "item,value\n" + "\n".join(f"{k},{v}" for k, v in rows)
    st.download_button("⬇ Download results (CSV)", data=csv_str.encode("utf-8-sig"),
                       file_name="nh3_h2_lhv_result.csv", mime="text/csv")

    # ----- assumptions and sources -----
    with st.expander("Method · assumptions · data sources"):
        st.markdown(
            """
**Fuel state**
- **Vapour (combustion)**: a gas mixture of NH₃ vapour and H₂ — the blended fuel as it reaches the burner. The density is the ideal-mixture gas density **at the NH₃ saturation pressure of each temperature**; at another operating pressure the gas density scales with pressure.
- **Liquid (storage)**: pure liquid ammonia. Hydrogen cannot be liquid in this temperature range (critical temperature −240 °C) and liquid and gas do not mix into one phase, so **the stored state is pure NH₃**.

**Standard LHV** — mass-weighted average of the component LHVs (H₂ 120, NH₃ 18.6 MJ/kg). Depends on the composition only, not on temperature or state.

**Effective LHV** — the standard value corrected for the fuel temperature and state (enthalpy), referenced to vapour at 25 °C.

**Density / volumetric energy** — ideal mixing for the gas (volume additivity); volumetric energy = standard LHV × density.

**Data source** — NIST Thermophysical Properties of Fluid Systems (NIST Chemistry WebBook); pure components (NH₃, H₂) interpolated linearly in temperature.

**Validity and caveats** — −50 to 130 °C. Accuracy degrades near the critical point (about 132 °C). The real NH₃–H₂ phase equilibrium (VLE) and pressure dependence are simplified.
            """
        )

    # ----- charts -----
    if is_gas:
        with st.expander("📈 Effect of the hydrogen fraction (zoom and hover for values)"):
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            fr = np.linspace(0, 1, 101)
            lhv_list = [compute_blend(df, w, T, 1.0)["lhv_std"] for w in fr]
            vol_list = [compute_blend(df, w, T, 1.0)["vol_energy"] for w in fr]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=fr*100, y=lhv_list, name="Standard LHV",
                          line=dict(color="#3B9DD6", width=2),
                          hovertemplate="H2 %{x:.0f}% → %{y:.2f} MJ/kg<extra></extra>"),
                          secondary_y=False)
            fig.add_trace(go.Scatter(x=fr*100, y=vol_list, name="Volumetric energy",
                          line=dict(color="#E08A3C", width=2, dash="dash"),
                          hovertemplate="H2 %{x:.0f}% → %{y:.3f} MJ/L<extra></extra>"),
                          secondary_y=True)
            _styled_axes(fig, "H2 mass fraction (%)",
                         "Standard LHV (MJ/kg)", "#3B9DD6",
                         "Volumetric energy (MJ/L)", "#E08A3C",
                         f"Vapour · {T:.0f} °C")
            st.plotly_chart(fig, width="stretch", config={"scrollZoom": True})
            st.caption("More H₂ raises the LHV per mass but lowers the energy per volume (lighter fuel) — a trade-off.")
    else:
        with st.expander("📈 Liquid NH₃ versus temperature (zoom and hover for values)"):
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            ts = np.linspace(-50, 130, 91)
            rho_list = [compute_blend(df, 0.0, t, 0.0)["rho_mix"] for t in ts]
            vol_list = [compute_blend(df, 0.0, t, 0.0)["vol_energy"] for t in ts]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=ts, y=rho_list, name="Density",
                          line=dict(color="#3B9DD6", width=2),
                          hovertemplate="%{x:.0f}°C → %{y:.1f} kg/m³<extra></extra>"),
                          secondary_y=False)
            fig.add_trace(go.Scatter(x=ts, y=vol_list, name="Volumetric energy",
                          line=dict(color="#E08A3C", width=2, dash="dash"),
                          hovertemplate="%{x:.0f}°C → %{y:.2f} MJ/L<extra></extra>"),
                          secondary_y=True)
            _styled_axes(fig, "Temperature (°C)",
                         "Density (kg/m³)", "#3B9DD6",
                         "Volumetric energy (MJ/L)", "#E08A3C",
                         "Liquid NH₃ (storage)")
            st.plotly_chart(fig, width="stretch", config={"scrollZoom": True})
            st.caption("A warmer storage temperature expands the liquid NH₃, lowering its density and volumetric energy.")


# stand-alone run
if __name__ == "__main__":
    st.set_page_config(page_title="Fuel-blend LHV calculator", layout="centered")
    render_lhv_page()
