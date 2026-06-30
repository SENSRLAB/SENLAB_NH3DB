# -*- coding: utf-8 -*-
"""
암모니아·수소 혼소 연료 발열량(LHV)·밀도 계산기
- 연료 상태: 기체(연소) / 액체(저장)
  · 기체(연소): NH3 증기 + H2 기체 혼합물 → 조성·온도에 따른 LHV·밀도
  · 액체(저장): 순수 액체 NH3 (H2는 -240°C 이하에서만 액체라 저장 시 H2 비율 무의미)
- 출력: 표준 LHV(헤드라인) + 밀도 / 유효 LHV / 부피당 에너지 + CSV 다운로드

데이터: NIST 순물질 물성 (nh3_h2_blend_data.csv, -50~130°C)
※ app.py에서 render_lhv_page() 를 호출하면 됩니다.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np

# ============================================================
# 1) 상수
# ============================================================
LHV_NH3_STD = 18.6      # MJ/kg
LHV_H2_STD  = 120.0     # MJ/kg
H_REF_NH3   = 1629.0    # kJ/kg  (NH3 25°C 포화증기 엔탈피)
H_REF_H2    = 3931.5    # kJ/kg  (H2 25°C 엔탈피)
M_NH3       = 17.031    # g/mol
M_H2        = 2.016     # g/mol

# ============================================================
# 2) 데이터
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
# 3) 계산
# ============================================================
def compute_blend(df, w_H2, T, x):
    """
    w_H2 : 수소 질량분율 (0~1)
    T    : 온도 (°C)
    x    : 0 = 액체상태(순수 NH3 기준), 1 = 기체 혼합물
    """
    w_NH3 = 1.0 - w_H2
    rho_liq = _interp(df, T, "rho_liq_NH3")
    rho_vap = _interp(df, T, "rho_vap_NH3")
    h_liq   = _interp(df, T, "h_liq_NH3")
    h_vap   = _interp(df, T, "h_vap_NH3")
    rho_H2  = _interp(df, T, "rho_H2")
    h_H2    = _interp(df, T, "h_H2_kJkg")
    P_sat   = _interp(df, T, "P_sat_bar")

    # NH3 상태 (x=0 액체, x=1 증기)
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
# 보조 함수
# ============================================================
def _slider_input(label, lo, hi, default, step, key):
    """슬라이더 + 숫자입력 동기화."""
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
    t_unit = st.radio("온도 단위", ["°C", "K"], horizontal=True)
    if t_unit == "°C":
        return _slider_input("온도 (°C)", -50.0, 130.0, 25.0, 1.0, "t_c")
    return _slider_input("온도 (K)", 223.15, 403.15, 298.15, 1.0, "t_k") - 273.15

def _mole_to_mass(y_H2):
    den = y_H2 * M_H2 + (1 - y_H2) * M_NH3
    return (y_H2 * M_H2) / den if den > 0 else 0.0

def _mass_to_mole(w_H2):
    den = w_H2 / M_H2 + (1 - w_H2) / M_NH3
    return (w_H2 / M_H2) / den if den > 0 else 0.0

def _styled_axes(fig, x_title, y1_title, y1_color, y2_title, y2_color, title):
    """Plotly 공통 스타일 (검은 축·아래 범례)."""
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
# 4) 페이지 UI
# ============================================================
def render_lhv_page():
    st.markdown("## 암모니아·수소 혼소 연료 발열량 계산기")
    st.caption("연료 상태를 고르고 수소 비율·온도를 입력하면 발열량과 밀도를 계산합니다.")

    df = load_data()

    # ----- 연료 상태 토글 -----
    mode = st.radio("연료 상태", ["기체 (연소)", "액체 (저장)"],
                    horizontal=True, index=0,
                    help="연소 시엔 NH₃·H₂ 기체 혼합물, 저장 시엔 액체 암모니아입니다.")

    if mode == "기체 (연소)":
        # 조성
        basis = st.radio("수소 비율 입력 기준", ["질량분율", "몰분율"], horizontal=True)
        frac_pct = _slider_input(f"수소 비율 ({basis}, %)", 0.0, 100.0, 0.0, 0.1, "h2")
        frac = frac_pct / 100.0
        if basis == "몰분율":
            w_H2 = _mole_to_mass(frac)
            conv = f"→ 질량분율 H₂ {w_H2*100:.1f}% / NH₃ {(1-w_H2)*100:.1f}%"
        else:
            w_H2 = frac
            y = _mass_to_mole(w_H2)
            conv = f"→ 몰분율 H₂ {y*100:.1f}% / NH₃ {(1-y)*100:.1f}%"
        st.caption(f"암모니아 {basis}: **{100-frac_pct:.1f}%**   ·   {conv}")
        T = _temp_input()
        x = 1.0  # 기체 혼합물
    else:  # 액체 (저장)
        st.info("저장 탱크엔 **순수 액체 암모니아**만 들어갑니다. 수소는 임계온도가 −240 °C라 "
                "이 온도 범위에서 액체로 존재할 수 없어, **액체 저장 시 H₂ 비율은 의미가 없습니다.**")
        w_H2 = 0.0
        T = _temp_input()
        x = 0.0  # 순수 액체 NH3

    # ----- 계산 -----
    r = compute_blend(df, w_H2, T, x)

    # ----- 출력 -----
    st.markdown("### 결과")
    st.metric("표준 LHV (저위발열량)", f"{r['lhv_std']:.2f} MJ/kg",
              help="성분 LHV의 질량가중 평균. 조성에만 의존하며 온도·상태와 무관합니다.")
    m1, m2, m3 = st.columns(3)
    m1.metric("밀도", f"{r['rho_mix']:.2f} kg/m³")
    m2.metric("유효 LHV", f"{r['lhv_eff']:.2f} MJ/kg",
              help="표준값에 온도·상태를 보정한 값 (25 °C 기체 기준).")
    m3.metric("부피당 에너지", f"{r['vol_energy']:.3f} MJ/L",
              help="표준 LHV × 밀도.")

    if mode == "기체 (연소)":
        st.caption(
            f"입력 요약 — 기체 · H₂(질량) {w_H2*100:.1f}% / NH₃ {(1-w_H2)*100:.1f}% · "
            f"{T:.1f} °C · (NH₃ 포화압력 ≈ {r['P_sat']:.2f} bar)"
        )
    else:
        st.caption(f"입력 요약 — 액체 저장 · 순수 NH₃ · {T:.1f} °C · "
                   f"(포화압력 ≈ {r['P_sat']:.2f} bar)")

    # ----- 결과 CSV 다운로드 -----
    rows = [
        ("연료 상태", "기체(연소)" if mode == "기체 (연소)" else "액체(저장)"),
        ("수소 질량분율 (%)", f"{w_H2*100:.2f}"),
        ("암모니아 질량분율 (%)", f"{(1-w_H2)*100:.2f}"),
        ("온도 (C)", f"{T:.1f}"),
        ("표준 LHV (MJ/kg)", f"{r['lhv_std']:.3f}"),
        ("유효 LHV (MJ/kg)", f"{r['lhv_eff']:.3f}"),
        ("밀도 (kg/m3)", f"{r['rho_mix']:.4f}"),
        ("부피당 에너지 (MJ/L)", f"{r['vol_energy']:.4f}"),
        ("NH3 포화압력 (bar)", f"{r['P_sat']:.3f}"),
    ]
    csv_str = "항목,값\n" + "\n".join(f"{k},{v}" for k, v in rows)
    st.download_button("⬇ 결과 CSV 다운로드", data=csv_str.encode("utf-8-sig"),
                       file_name="nh3_h2_lhv_result.csv", mime="text/csv")

    # ----- 가정 · 출처 -----
    with st.expander("계산 방법 · 가정 · 데이터 출처"):
        st.markdown(
            """
**연료 상태**
- **기체(연소)**: NH₃ 증기 + H₂가 섞인 기체 혼합물. 실제 버너로 가는 혼소 연료 상태입니다. 밀도는 각 온도의 **NH₃ 포화압력 기준** 기체 혼합 밀도(이상혼합)이며, 운전 압력이 다르면 기체 밀도는 압력에 비례해 달라집니다.
- **액체(저장)**: 순수 액체 암모니아. 수소는 임계온도(−240 °C) 때문에 이 온도 범위에서 액체가 될 수 없고, 액체와 기체는 한 상으로 섞이지 않으므로 **저장 상태는 순수 NH₃**입니다.

**표준 LHV** — 성분 LHV의 질량가중 평균 (H₂ 120, NH₃ 18.6 MJ/kg). 조성에만 의존하며 온도·상태와 무관합니다.

**유효 LHV** — 표준값에 연료의 온도·상태(엔탈피)를 보정 (25 °C 기체 기준).

**밀도 / 부피당 에너지** — 기체는 이상혼합(부피 가산), 부피당 에너지 = 표준 LHV × 밀도.

**데이터 출처** — NIST Thermophysical Properties of Fluid Systems (NIST Chemistry WebBook). 순물질(NH₃, H₂)을 온도별 선형보간.

**유효 범위 · 주의** — −50 ~ 130 °C. 임계점(약 132 °C) 근처는 정확도 저하 가능. 실제 NH₃–H₂ 혼합물의 상평형(VLE)·압력 의존성은 단순화되어 있습니다.
            """
        )

    # ----- 그래프 -----
    if mode == "기체 (연소)":
        with st.expander("📈 수소 비율에 따른 변화 (마우스로 확대·값 확인)"):
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            fr = np.linspace(0, 1, 101)
            lhv_list = [compute_blend(df, w, T, 1.0)["lhv_std"] for w in fr]
            vol_list = [compute_blend(df, w, T, 1.0)["vol_energy"] for w in fr]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=fr*100, y=lhv_list, name="표준 LHV",
                          line=dict(color="#3B9DD6", width=2),
                          hovertemplate="H2 %{x:.0f}% → %{y:.2f} MJ/kg<extra></extra>"),
                          secondary_y=False)
            fig.add_trace(go.Scatter(x=fr*100, y=vol_list, name="부피당 에너지",
                          line=dict(color="#E08A3C", width=2, dash="dash"),
                          hovertemplate="H2 %{x:.0f}% → %{y:.3f} MJ/L<extra></extra>"),
                          secondary_y=True)
            _styled_axes(fig, "H2 mass fraction (%)",
                         "Standard LHV (MJ/kg)", "#3B9DD6",
                         "Volumetric energy (MJ/L)", "#E08A3C",
                         f"기체 · {T:.0f} °C")
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
            st.caption("H₂↑ → 질량당 LHV↑, 하지만 가벼워져 부피당 에너지↓ (트레이드오프).")
    else:
        with st.expander("📈 온도에 따른 액체 NH₃ 변화 (마우스로 확대·값 확인)"):
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            ts = np.linspace(-50, 130, 91)
            rho_list = [compute_blend(df, 0.0, t, 0.0)["rho_mix"] for t in ts]
            vol_list = [compute_blend(df, 0.0, t, 0.0)["vol_energy"] for t in ts]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=ts, y=rho_list, name="밀도",
                          line=dict(color="#3B9DD6", width=2),
                          hovertemplate="%{x:.0f}°C → %{y:.1f} kg/m³<extra></extra>"),
                          secondary_y=False)
            fig.add_trace(go.Scatter(x=ts, y=vol_list, name="부피당 에너지",
                          line=dict(color="#E08A3C", width=2, dash="dash"),
                          hovertemplate="%{x:.0f}°C → %{y:.2f} MJ/L<extra></extra>"),
                          secondary_y=True)
            _styled_axes(fig, "Temperature (°C)",
                         "Density (kg/m³)", "#3B9DD6",
                         "Volumetric energy (MJ/L)", "#E08A3C",
                         "액체 NH₃ (저장)")
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
            st.caption("저장 온도가 오르면 액체 NH₃가 팽창해 밀도·부피에너지가 감소.")


# 단독 실행용
if __name__ == "__main__":
    st.set_page_config(page_title="혼소 연료 LHV 계산기", layout="centered")
    render_lhv_page()
