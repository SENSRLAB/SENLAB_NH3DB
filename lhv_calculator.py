# -*- coding: utf-8 -*-
"""
암모니아·수소 혼소 연료 발열량(LHV) 계산기
- 입력: H₂ 질량분율, 온도, 연료 상태(액체/기체/vapor fraction)
- 출력: 표준 LHV(헤드라인) + 밀도 / 유효 LHV / 부피당 에너지

데이터: NIST 순물질 물성 (nh3_h2_blend_data.csv, -50~130°C)
※ 기존 app.py에 한 페이지로 붙이려면 아래 render_lhv_page() 함수를 호출하면 됩니다.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# 1) 상수 (검증 완료 / H₂ 기준 3400→3931.5 수정 반영)
# ============================================================
LHV_NH3_STD = 18.6      # MJ/kg  암모니아 표준 LHV
LHV_H2_STD  = 120.0     # MJ/kg  수소 표준 LHV
H_REF_NH3   = 1629.0    # kJ/kg  NH₃ 25°C 포화증기 엔탈피 (유효 LHV 기준점)
H_REF_H2    = 3931.5    # kJ/kg  H₂  25°C 엔탈피        (유효 LHV 기준점, 수정값)

# ============================================================
# 2) 데이터 로드 (한 번만 읽고 캐시)
# ============================================================
_HERE = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data(path=None):
    # CSV가 이 파일과 같은 폴더에 있으면 경로 걱정 없이 읽힘
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

    # --- 온도에서 순물질 물성 보간 ---
    rho_liq = _interp(df, T, "rho_liq_NH3")   # NH₃ 포화액 밀도
    rho_vap = _interp(df, T, "rho_vap_NH3")   # NH₃ 포화증기 밀도
    h_liq   = _interp(df, T, "h_liq_NH3")     # NH₃ 포화액 엔탈피 [kJ/kg]
    h_vap   = _interp(df, T, "h_vap_NH3")     # NH₃ 포화증기 엔탈피 [kJ/kg]
    rho_H2  = _interp(df, T, "rho_H2")        # H₂ 밀도 (NH₃ 포화압력에서)
    h_H2    = _interp(df, T, "h_H2_kJkg")     # H₂ 엔탈피 [kJ/kg]
    P_sat   = _interp(df, T, "P_sat_bar")     # NH₃ 포화압력 [bar]

    # --- 암모니아 2상 상태 (지렛대 법칙: 비체적이 가산) ---
    v_NH3   = (1 - x) / rho_liq + x / rho_vap      # 혼합 비체적
    rho_NH3 = 1.0 / v_NH3                          # 암모니아 밀도
    h_NH3   = (1 - x) * h_liq + x * h_vap          # 암모니아 엔탈피

    # --- 표준 LHV (조성만, 질량가중) — 헤드라인 ---
    lhv_std = w_H2 * LHV_H2_STD + w_NH3 * LHV_NH3_STD

    # --- 유효 LHV (상태 보정) ---
    lhv_eff_NH3 = LHV_NH3_STD + (h_NH3 - H_REF_NH3) / 1000.0
    lhv_eff_H2  = LHV_H2_STD  + (h_H2  - H_REF_H2)  / 1000.0
    lhv_eff     = w_H2 * lhv_eff_H2 + w_NH3 * lhv_eff_NH3

    # --- 혼합 밀도 (이상혼합: 부피 가산) ---
    if w_H2 <= 0:
        rho_mix = rho_NH3
    elif w_NH3 <= 0:
        rho_mix = rho_H2
    else:
        rho_mix = 1.0 / (w_H2 / rho_H2 + w_NH3 / rho_NH3)

    # --- 부피당 에너지 [MJ/L] = LHV[MJ/kg] × 밀도[kg/m³] / 1000 ---
    vol_energy = lhv_std * rho_mix / 1000.0

    return {
        "lhv_std": lhv_std, "lhv_eff": lhv_eff,
        "rho_mix": rho_mix, "vol_energy": vol_energy, "P_sat": P_sat,
    }

# ============================================================
# 4) 페이지 UI
# ============================================================
def render_lhv_page():
    st.markdown("## ⛽ 암모니아·수소 혼소 연료 발열량 계산기")
    st.caption("수소 비율과 온도·상태를 입력하면 발열량과 밀도를 계산합니다.")

    df = load_data()

    # ---- 입력 ----
    c1, c2 = st.columns(2)
    with c1:
        w_H2_pct = st.slider("수소 비율 (H₂ 질량분율, %)", 0, 100, 0, 1)
        w_H2 = w_H2_pct / 100.0
        st.caption(f"→ 암모니아 비율: **{100 - w_H2_pct}%**")
    with c2:
        T = st.slider("온도 (°C)", -50, 130, 25, 1)

    state = st.radio("연료 상태", ["액체", "기체", "직접 입력"],
                     horizontal=True, index=0,
                     help="대부분 액체(저장) 또는 기체(연소 직전)입니다. 0=액체, 1=기체.")
    if state == "액체":
        x = 0.0
    elif state == "기체":
        x = 1.0
    else:
        x = st.slider("vapor fraction (0 = 액체, 1 = 기체)", 0.0, 1.0, 0.5, 0.01)

    # ---- 계산 ----
    r = compute_blend(df, w_H2, T, x)

    # ---- 출력: 헤드라인 ----
    st.markdown("### 결과")
    st.metric("표준 LHV (저위발열량)", f"{r['lhv_std']:.2f} MJ/kg")

    # ---- 출력: 보조 3개 ----
    m1, m2, m3 = st.columns(3)
    m1.metric("밀도", f"{r['rho_mix']:.2f} kg/m³")
    m2.metric("유효 LHV", f"{r['lhv_eff']:.2f} MJ/kg")
    m3.metric("부피당 에너지", f"{r['vol_energy']:.2f} MJ/L")

    st.caption(
        f"입력 요약 — H₂ {w_H2_pct}% / NH₃ {100 - w_H2_pct}% · {T} °C · {state} "
        f"· (NH₃ 포화압력 ≈ {r['P_sat']:.2f} bar)"
    )

    # ---- 가정 설명 ----
    with st.expander("계산 방법 / 가정"):
        st.markdown(
            """
- **표준 LHV** = 성분 LHV의 질량가중 평균 (H₂ 120, NH₃ 18.6 MJ/kg). 조성만으로 정해지며 온도·상태와 무관합니다.
- **유효 LHV** = 표준값에 연료의 온도·상태를 보정한 값 (25 °C 기체 기준). 차갑거나 액체인 연료를 데우고 기화시키는 에너지를 반영합니다.
- **밀도** = 이상혼합(부피 가산) 가정. 암모니아 2상은 지렛대 법칙으로 계산.
- **부피당 에너지** = 표준 LHV × 밀도.
- **데이터 출처**: NIST 순물질 물성. **유효 범위**: −50 ~ 130 °C.
            """
        )

    # ---- (보너스) 수소 비율에 따른 경향 그래프 (인터랙티브: hover·확대) ----
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
                       line=dict(color="#1f3a5f", width=2),
                       hovertemplate="H2 %{x:.0f}% → LHV %{y:.2f} MJ/kg<extra></extra>"),
            secondary_y=False)
        fig.add_trace(
            go.Scatter(x=fracs * 100, y=vol_list, name="Volumetric energy",
                       line=dict(color="#c0792e", width=2, dash="dash"),
                       hovertemplate="H2 %{x:.0f}% → %{y:.2f} MJ/L<extra></extra>"),
            secondary_y=True)
        fig.update_xaxes(title_text="H2 mass fraction (%)")
        fig.update_yaxes(title_text="Standard LHV (MJ/kg)", color="#1f3a5f", secondary_y=False)
        fig.update_yaxes(title_text="Volumetric energy (MJ/L)", color="#c0792e", secondary_y=True)
        fig.update_layout(
            title=f"T = {T} °C, {state_en}",
            hovermode="x unified",
            height=400, margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        # scrollZoom=True → 마우스 휠로 줌 / 드래그 → 영역 확대 / 더블클릭 → 리셋
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
        st.caption("드래그로 영역 확대 · 마우스 휠로 줌 · 더블클릭으로 원래대로 · 선 위에 올리면 값 표시.")


# 단독 실행용
if __name__ == "__main__":
    st.set_page_config(page_title="혼소 연료 LHV 계산기", page_icon="⛽", layout="centered")
    render_lhv_page()
