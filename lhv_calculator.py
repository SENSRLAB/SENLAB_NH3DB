# -*- coding: utf-8 -*-
"""
암모니아·수소 혼소 연료 발열량(LHV) 계산기
- 입력: H2 비율(질량/몰분율), 온도(°C/K), 연료 상태(액체/기체/vapor fraction)
- 출력: 표준 LHV(헤드라인) + 밀도 / 유효 LHV / 부피당 에너지 + 결과 CSV 다운로드

데이터: NIST 순물질 물성 (nh3_h2_blend_data.csv, -50~130°C)
※ 기존 app.py에 붙이려면 render_lhv_page() 를 호출하면 됩니다.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np

# ============================================================
# 1) 상수 (검증 완료 / H2 기준 3400→3931.5 수정 반영)
# ============================================================
LHV_NH3_STD = 18.6      # MJ/kg  암모니아 표준 LHV
LHV_H2_STD  = 120.0     # MJ/kg  수소 표준 LHV
H_REF_NH3   = 1629.0    # kJ/kg  NH3 25°C 포화증기 엔탈피 (유효 LHV 기준점)
H_REF_H2    = 3931.5    # kJ/kg  H2  25°C 엔탈피        (유효 LHV 기준점)
M_NH3       = 17.031    # g/mol
M_H2        = 2.016     # g/mol

# ============================================================
# 2) 데이터 로드 (한 번만 읽고 캐시)
# ============================================================
_HERE = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data(path=None):
    if path is None:
        path = os.path.join(_HERE, "nh3_h2_blend_data.csv")
    return pd.read_csv(path)

def _interp(df, T, col):
    """온도 T에서 해당 물성을 선형보간."""
    return float(np.interp(T, df["T_C"], df[col]))

# ============================================================
# 3) 계산 함수
# ============================================================
def compute_blend(df, w_H2, T, x):
    """
    w_H2 : 수소 질량분율 (0~1)
    T    : 온도 (°C)
    x    : 암모니아 vapor fraction (0=액체, 1=기체)
    """
    w_NH3 = 1.0 - w_H2

    rho_liq = _interp(df, T, "rho_liq_NH3")
    rho_vap = _interp(df, T, "rho_vap_NH3")
    h_liq   = _interp(df, T, "h_liq_NH3")
    h_vap   = _interp(df, T, "h_vap_NH3")
    rho_H2  = _interp(df, T, "rho_H2")
    h_H2    = _interp(df, T, "h_H2_kJkg")
    P_sat   = _interp(df, T, "P_sat_bar")

    # 암모니아 2상 (지렛대 법칙: 비체적 가산)
    v_NH3   = (1 - x) / rho_liq + x / rho_vap
    rho_NH3 = 1.0 / v_NH3
    h_NH3   = (1 - x) * h_liq + x * h_vap

    # 표준 LHV (조성만, 질량가중)
    lhv_std = w_H2 * LHV_H2_STD + w_NH3 * LHV_NH3_STD

    # 유효 LHV (상태 보정)
    lhv_eff_NH3 = LHV_NH3_STD + (h_NH3 - H_REF_NH3) / 1000.0
    lhv_eff_H2  = LHV_H2_STD  + (h_H2  - H_REF_H2)  / 1000.0
    lhv_eff     = w_H2 * lhv_eff_H2 + w_NH3 * lhv_eff_NH3

    # 혼합 밀도 (이상혼합: 부피 가산)
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
    """슬라이더 + 숫자입력을 한 쌍으로 묶어 동기화 (둘 중 아무거나 조정 가능)."""
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

def _mole_to_mass(y_H2):
    den = y_H2 * M_H2 + (1 - y_H2) * M_NH3
    return (y_H2 * M_H2) / den if den > 0 else 0.0

def _mass_to_mole(w_H2):
    den = w_H2 / M_H2 + (1 - w_H2) / M_NH3
    return (w_H2 / M_H2) / den if den > 0 else 0.0

# ============================================================
# 4) 페이지 UI
# ============================================================
def render_lhv_page():
    st.markdown("## 암모니아·수소 혼소 연료 발열량 계산기")
    st.caption("수소 비율과 온도·상태를 입력하면 발열량과 밀도를 계산합니다.")

    df = load_data()

    # ----- 입력: 수소 비율 (질량/몰분율) -----
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

    # ----- 입력: 온도 (°C/K) -----
    t_unit = st.radio("온도 단위", ["°C", "K"], horizontal=True)
    if t_unit == "°C":
        T = _slider_input("온도 (°C)", -50.0, 130.0, 25.0, 1.0, "t_c")
    else:
        T_k = _slider_input("온도 (K)", 223.15, 403.15, 298.15, 1.0, "t_k")
        T = T_k - 273.15

    # ----- 입력: 연료 상태 -----
    state = st.radio("연료 상태", ["액체", "기체", "직접 입력"],
                     horizontal=True, index=0,
                     help="대부분 액체(저장) 또는 기체(연소 직전). 0=액체, 1=기체.")
    if state == "액체":
        x = 0.0
    elif state == "기체":
        x = 1.0
    else:
        x = _slider_input("vapor fraction (0=액체, 1=기체)", 0.0, 1.0, 0.5, 0.01, "x")

    # ----- 계산 -----
    r = compute_blend(df, w_H2, T, x)

    # ----- 출력 -----
    st.markdown("### 결과")
    st.metric("표준 LHV (저위발열량)", f"{r['lhv_std']:.2f} MJ/kg")
    m1, m2, m3 = st.columns(3)
    m1.metric("밀도", f"{r['rho_mix']:.2f} kg/m³")
    m2.metric("유효 LHV", f"{r['lhv_eff']:.2f} MJ/kg")
    m3.metric("부피당 에너지", f"{r['vol_energy']:.2f} MJ/L")
    st.caption(
        f"입력 요약 — H₂(질량) {w_H2*100:.1f}% / NH₃ {(1-w_H2)*100:.1f}% · "
        f"{T:.1f} °C · {state} · (NH₃ 포화압력 ≈ {r['P_sat']:.2f} bar)"
    )

    # ----- 결과 CSV 다운로드 -----
    rows = [
        ("수소 질량분율 (%)", f"{w_H2*100:.2f}"),
        ("암모니아 질량분율 (%)", f"{(1-w_H2)*100:.2f}"),
        ("수소 몰분율 (%)", f"{_mass_to_mole(w_H2)*100:.2f}"),
        ("온도 (C)", f"{T:.1f}"),
        ("vapor fraction", f"{x:.2f}"),
        ("표준 LHV (MJ/kg)", f"{r['lhv_std']:.3f}"),
        ("유효 LHV (MJ/kg)", f"{r['lhv_eff']:.3f}"),
        ("밀도 (kg/m3)", f"{r['rho_mix']:.3f}"),
        ("부피당 에너지 (MJ/L)", f"{r['vol_energy']:.3f}"),
        ("NH3 포화압력 (bar)", f"{r['P_sat']:.3f}"),
    ]
    csv_str = "항목,값\n" + "\n".join(f"{k},{v}" for k, v in rows)
    st.download_button("⬇ 결과 CSV 다운로드",
                       data=csv_str.encode("utf-8-sig"),
                       file_name="nh3_h2_lhv_result.csv",
                       mime="text/csv")

    # ----- 계산 방법 · 가정 · 출처 -----
    with st.expander("계산 방법 · 가정 · 데이터 출처"):
        st.markdown(
            """
**표준 LHV** — 성분 LHV의 질량가중 평균. H₂ = 120 MJ/kg (문헌 표준값 ≈ 119.96), NH₃ = 18.6 MJ/kg. 조성만으로 정해지며 온도·상태와 무관합니다.

**유효 LHV** — 표준값에 연료의 온도·상태(엔탈피)를 보정한 값. **25 °C 기체 상태를 기준점**으로 하여, 차갑거나 액체인 연료를 데우고 기화시키는 에너지를 반영합니다. 기준 엔탈피: NH₃ 1629 kJ/kg, H₂ 3931.5 kJ/kg (모두 25 °C 기준).

**밀도** — 이상혼합(부피 가산): 1/ρ = w(H₂)/ρ(H₂) + w(NH₃)/ρ(NH₃). 암모니아 2상은 지렛대 법칙(비체적 가산)으로 계산하며, H₂ 밀도는 NH₃ 포화압력 기준입니다.

**부피당 에너지** — 표준 LHV × 밀도.

**데이터 출처** — NIST Thermophysical Properties of Fluid Systems (NIST Chemistry WebBook). 순물질(NH₃, H₂) 물성을 온도별로 선형보간하여 사용.

**유효 범위 · 주의** — −50 ~ 130 °C. 암모니아 임계점(약 132 °C) 근처에서는 정확도가 낮아질 수 있습니다. 실제 NH₃–H₂ 혼합물의 상평형(VLE)은 반영하지 않으며, 암모니아의 vapor fraction은 독립 입력값으로 다룹니다.
            """
        )

    # ----- (보너스) 인터랙티브 그래프 -----
    with st.expander("📈 수소 비율에 따른 변화 보기 (마우스로 확대·값 확인)"):
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        state_en = {"액체": "liquid", "기체": "gas", "직접 입력": "custom"}.get(state, state)
        fracs = np.linspace(0, 1, 101)
        lhv_list = [compute_blend(df, w, T, x)["lhv_std"] for w in fracs]
        vol_list = [compute_blend(df, w, T, x)["vol_energy"] for w in fracs]

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(x=fracs * 100, y=lhv_list, name="Standard LHV",
                       line=dict(color="#3B9DD6", width=2),
                       hovertemplate="H2 %{x:.0f}% → LHV %{y:.2f} MJ/kg<extra></extra>"),
            secondary_y=False)
        fig.add_trace(
            go.Scatter(x=fracs * 100, y=vol_list, name="Volumetric energy",
                       line=dict(color="#E08A3C", width=2, dash="dash"),
                       hovertemplate="H2 %{x:.0f}% → %{y:.2f} MJ/L<extra></extra>"),
            secondary_y=True)
        fig.update_xaxes(title_text="H2 mass fraction (%)",
                         title_font=dict(size=16), tickfont=dict(size=14))
        fig.update_yaxes(title_text="Standard LHV (MJ/kg)", color="#3B9DD6",
                         title_font=dict(size=16), tickfont=dict(size=14), secondary_y=False)
        fig.update_yaxes(title_text="Volumetric energy (MJ/L)", color="#E08A3C",
                         title_font=dict(size=16), tickfont=dict(size=14), secondary_y=True)
        fig.update_layout(
            title=f"T = {T:.0f} °C, {state_en}",
            hovermode="x unified",
            height=460, margin=dict(l=10, r=10, t=40, b=10),
            font=dict(size=14),
            legend=dict(
                orientation="v",                  # 세로 → 두 줄로 표시
                yanchor="bottom", y=0.03,          # 그래프 안쪽 하단
                xanchor="right", x=0.98,           # 그래프 안쪽 우측
                bgcolor="rgba(255,255,255,0.75)",  # 반투명 배경 (선 위에서도 보이게)
                bordercolor="#CCCCCC", borderwidth=1,
                font=dict(size=12),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
        st.caption("드래그로 영역 확대 · 마우스 휠로 줌 · 더블클릭으로 원래대로 · 선 위에 올리면 값 표시.")


# 단독 실행용
if __name__ == "__main__":
    st.set_page_config(page_title="혼소 연료 LHV 계산기", layout="centered")
    render_lhv_page()
