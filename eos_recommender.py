"""
EOS Recommendation page for SENLAB_NH3DB.

NH3 + X 이성분계에 대해, EOS/BIP 평가 워크플로(문헌 VLE 기반 국소 kij 회귀)의
결과 JSON(eos_recommendations/*.json)을 읽어 조건(T, P)에 맞는 EOS 추천을
보여주는 페이지입니다.

- 평가 자체는 이 앱에서 수행하지 않습니다. Aspen TDE .bkp → EOS/BIP 에이전트
  (Claude cowork + Thermopack / 자체 구현 PR-BM) → JSON 커밋 순서로 오프라인에서 생성됩니다.
- JSON 스키마와 생성 방법은 eos_recommendations/README.md 참고.
- v4: Aspen Plus / HYSYS 물성법 매핑, 시뮬레이터용 1위, Aspen 입력 카드(PRKBV 형식 kij),
  PR-BM·HV 행, NH3+H2O 권고 모델·조성별 정확도 안내, Plotly(테마 연동) 그래프.
"""

import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RECO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eos_recommendations")

MIXTURES = {
    "1. $NH_3 + N_2$ 혼합물 — 질소": ("nh3_n2.json", "NH₃ + N₂ (질소)"),
    "2. $NH_3 + H_2O$ 혼합물 — 물": ("nh3_h2o.json", "NH₃ + H₂O (물)"),
    "3. $NH_3 + H_2$ 혼합물 — 수소": ("nh3_h2.json", "NH₃ + H₂ (수소)"),
    "4. $NH_3 + CH_4$ 혼합물 — 메탄": ("nh3_ch4.json", "NH₃ + CH₄ (메탄)"),
}

# 순위표 EOS → 시뮬레이터 물성법 매핑.
#   tier "direct": Aspen Plus에서 같은 수식·같은 kij 규약으로 바로 선택 가능
#   tier "cond"  : 이름은 있으나 파라미터 세트·α 옵션이 달라 재확인 필요(근사)
#   tier "none"  : 상용 시뮬레이터에 없음 — 정확도 상한 참고용
ASPEN_MAP = {
    "PR":      {"aspen": "PENG-ROB", "param": "PRKBV", "hysys": "Peng-Robinson*", "tier": "direct"},
    "PR-BM":   {"aspen": "PR-BM", "param": "PRKBV", "hysys": "—", "tier": "direct"},
    "SRK":     {"aspen": "RK-SOAVE", "param": "RKSKBV", "hysys": "SRK", "tier": "direct"},
    "RKS-BM":  {"aspen": "RKS-BM (= SRK 물성법의 VLE)", "param": "RKSKBV", "hysys": "SRK*", "tier": "direct"},
    "RK-ASPEN": {"aspen": "RK-ASPEN", "param": "RKAKA0 / RKAKB0", "hysys": "—", "tier": "direct"},
    "SR-POLAR": {"aspen": "SR-POLAR", "param": "SRKKA0 / SRLIJ0", "hysys": "—", "tier": "direct"},
    "NRTL-RK": {"aspen": "NRTL-RK (활성계수 모델)", "param": "NRTL", "hysys": "NRTL (τ 형식 다름)*", "tier": "direct"},
    "tcPR":    {"aspen": "PENG-ROB + Twu α·부피보정 옵션*", "param": "PRKBV", "hysys": "PR-Twu*", "tier": "cond"},
    "PC-SAFT": {"aspen": "PC-SAFT*", "param": "PCSKIJ", "hysys": "—", "tier": "cond"},
    "CPA":     {"aspen": "CPA (V12+ 확인)*", "param": "—", "hysys": "CPA*", "tier": "cond"},
    "PR (HV-NRTL)": {"aspen": "— (PRWS·PRMHV2 계열 참고)", "param": "—", "hysys": "—", "tier": "none"},
}
_NO_MAP = {"aspen": "—", "param": "—", "hysys": "—", "tier": "none"}
TIER_LABEL = {"direct": "직접", "cond": "근사·재확인", "none": "참고용"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_recommendation(filename):
    """Load a recommendation JSON. Returns dict or None if absent/broken."""
    path = os.path.join(RECO_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _find_band(bands, temp_k, p_bar):
    """Return (band, inside) — the band containing (T, P), else the nearest band."""
    if not bands:
        return None, False
    for band in bands:
        t_lo, t_hi = band["T_K"]
        p_lo, p_hi = band["P_bar"]
        if t_lo <= temp_k <= t_hi and p_lo <= p_bar <= p_hi:
            return band, True

    def distance(band):
        t_c = 0.5 * (band["T_K"][0] + band["T_K"][1])
        p_c = 0.5 * (band["P_bar"][0] + band["P_bar"][1])
        t_span = max(band["T_K"][1] - band["T_K"][0], 1e-6)
        p_span = max(band["P_bar"][1] - band["P_bar"][0], 1e-6)
        return abs(temp_k - t_c) / t_span + abs(p_bar - p_c) / p_span

    return min(bands, key=distance), False


def _effective_aard(entry):
    """The deviation the recommendation actually carries (fitted if used, else base)."""
    if entry.get("use_fitted") and entry.get("x_aard_fit") is not None:
        return entry["x_aard_fit"]
    if entry.get("x_aard_base") is not None:
        return entry["x_aard_base"]
    return np.nan


def _effective_bip(entry):
    """Numeric BIP the recommendation carries, or None (e.g. 2-parameter rows)."""
    if entry.get("use_fitted") and isinstance(entry.get("bip_fitted"), (int, float)):
        return entry["bip_fitted"]
    if isinstance(entry.get("bip_default"), (int, float)):
        return entry["bip_default"]
    return None


def _bip_text(entry):
    value = _effective_bip(entry)
    if entry.get("use_fitted") and entry.get("bip_display"):
        return entry["bip_display"]
    if entry.get("use_fitted") and isinstance(entry.get("bip_fitted"), (int, float)):
        return f"{value:.4f}"
    if entry.get("bip_display"):
        return entry["bip_display"]
    if value is not None:
        return f"{value:.4f} (기본값)"
    return "—"


def _mapping(eos):
    return ASPEN_MAP.get(eos, _NO_MAP)


def _sorted(ranking):
    return sorted(ranking, key=lambda r: (r.get("rank") is None, r.get("rank", 999)))


def _render_ranking_chart(ranking, metric_label="x-AARD", key="eos_chart"):
    """Horizontal bars: final AARD per EOS (bar) + default-BIP AARD (tick). Plotly, app-theme colors."""
    rows = [r for r in ranking if not np.isnan(_effective_aard(r))]
    if not rows:
        return
    rows = sorted(rows, key=_effective_aard, reverse=True)  # best ends up on top

    names = [r["eos"] for r in rows]
    final = [100.0 * _effective_aard(r) for r in rows]
    base = [100.0 * r["x_aard_base"] if r.get("x_aard_base") is not None else np.nan for r in rows]

    # Axis span: anchor on the recommended-setting errors (median-based so one base-only outlier
    # cannot squeeze every bar), keep default-BIP ticks when they fit, and clip the rest with notes.
    final_arr = np.array(final)
    med = float(np.median(final_arr))
    upper = min(1.35 * float(final_arr.max()), max(4.0 * med, 1.35 * float(final_arr.min())))
    base_vis_max = float(np.nanmax(base)) if not np.all(np.isnan(base)) else 0.0
    if 0.0 < base_vis_max <= 2.5 * upper:
        upper = max(upper, base_vis_max * 1.08)
    upper = max(upper, 1e-6)

    bar_x, bar_text, bar_pos = [], [], []
    for v in final:
        if v > upper:
            bar_x.append(upper * 0.985); bar_text.append(f"{v:.1f}% →"); bar_pos.append("inside")
        else:
            bar_x.append(v); bar_text.append(f"{v:.1f}%"); bar_pos.append("outside")

    fig = go.Figure()
    fig.add_bar(
        x=bar_x, y=names, orientation="h", name=f"추천 설정의 {metric_label}",
        text=bar_text, textposition=bar_pos, cliponaxis=False, customdata=final,
        hovertemplate="%{y}: %{customdata:.2f}%<extra></extra>",
        marker_color="#1e3a8a",
    )
    tick_x = [bv if (not np.isnan(bv) and bv <= upper) else np.nan for bv in base]
    if not np.all(np.isnan(tick_x)):
        fig.add_scatter(
            x=tick_x, y=names, mode="markers", name=f"기본 BIP의 {metric_label}",
            marker=dict(symbol="line-ns-open", size=18, line=dict(width=2.5, color="#b45309")),
            hovertemplate="%{y} 기본값: %{x:.1f}%<extra></extra>",
        )
    for name, bv, fv in zip(names, base, final):
        if not np.isnan(bv) and bv > upper and fv <= upper:
            fig.add_annotation(x=upper * 0.985, y=name, text=f"기본 {bv:.0f}% →", showarrow=False,
                               xanchor="right", font=dict(size=10), opacity=0.8)

    fig.update_layout(
        height=max(280, 34 * len(rows) + 130),
        margin=dict(l=10, r=70, t=10, b=10),
        xaxis=dict(title=f"{metric_label} (%) — 낮을수록 좋음", range=[0, upper * 1.12], zeroline=False),
        yaxis=dict(title=None),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        bargap=0.35,
    )
    st.plotly_chart(fig, width="stretch", key=key)


def _aspen_card(reco, band, pick, metric_label):
    """Copy-ready Aspen Plus / HYSYS input block for the simulator-usable pick."""
    m = _mapping(pick["eos"])
    solvent, solute = reco.get("solvent", "NH3"), reco.get("solute", "X")
    kij = _effective_bip(pick)
    t_lo, t_hi = band["T_K"]
    p_lo, p_hi = band["P_bar"]
    fit = (reco.get("aspen_kij_T") or {}).get(pick["eos"])
    lines = [
        f"Aspen Plus 물성법 : {m['aspen']}",
        f"파라미터 입력란   : Parameters → Binary Interaction → {m['param']}-1   ({solvent} / {solute})",
    ]
    if pick["eos"] == "NRTL-RK" and pick.get("bip_params"):
        p = pick["bip_params"]
        lines[-1] = "파라미터 입력란   : Parameters → Binary Interaction → NRTL-1   (성분 i = NH3(AMMONIA), j = H2O(WATER) 순서)"
        lines.append(f"이 대역 상수      : AIJ = 0, AJI = 0, BIJ = {p['b12_K']:+.0f}, BJI = {p['b21_K']:+.0f}, CIJ = {p['alpha']:g}   "
                     f"(τij = BIJ/T, T {t_lo:g}–{t_hi:g} K)   — Aspen 내장 ENRTL-RK 파라미터가 있으면 그쪽이 우선")
    elif kij is not None:
        lines.append(f"이 대역 상수      : kaij = {kij:.4f}   (T {t_lo:g}–{t_hi:g} K, P {p_lo:g}–{p_hi:g} bar)   ← 가장 안전")
    elif pick.get("bip_params") and pick.get("use_fitted"):
        vals = ", ".join(f"{k} = {v:+.4f}" for k, v in pick["bip_params"].items())
        lines.append(f"이 대역 상수      : {vals}   (T {t_lo:g}–{t_hi:g} K, P {p_lo:g}–{p_hi:g} bar)")
    if fit and fit.get("n_bands", 0) >= 3:
        lo, hi = fit["T_range_K"]
        lines.append(
            f"전 대역 온도식    : kaij = {fit['kaij']:.4f}, kbij = {fit['kbij']:.6f}, kcij = {fit['kcij']:.2f}"
            f"   (kij = kaij + kbij·T + kcij/T, {lo:g}–{hi:g} K 안에서만; 밴드값 재현 오차 ≤ {fit['max_abs_dev']:.3f})"
        )
    if m["hysys"] not in ("—", ""):
        approx = " (HYSYS판은 자체 수정 모델이라 근사)" if m["hysys"].endswith("*") else ""
        lines.append(f"HYSYS            : {m['hysys'].rstrip('*')} 패키지 → Binary Coeffs에 kij = {kij:.4f} 입력{approx}" if kij is not None
                     else f"HYSYS            : {m['hysys'].rstrip('*')}{approx}")
    else:
        lines.append("HYSYS            : 해당 물성법 없음")
    lines.append(f"기대 정확도       : {metric_label} {100.0 * _effective_aard(pick):.1f}% (이 대역 문헌 실측 기준)")
    st.code("\n".join(lines), language="text")


def _render_pending(display_name):
    st.info(
        f"**{display_name} 계는 아직 평가 전이에요.** 아래 순서로 결과를 만들어 "
        "커밋하면 이 페이지에 자동으로 표시됩니다."
    )
    st.markdown(
        """
        1. **Aspen Plus**에서 두 물질을 등록하고 **NIST TDE Binary VLE** 데이터를 조회한 뒤 `.bkp`로 저장
        2. **Claude cowork**에서 `.bkp` + 평가 워크북을 첨부하고 "EOS agent 지침에 따라 분석" 실행
           (관심 조건 T, P 케이스를 함께 지정)
        3. 산출된 결과를 `eos_recommendations/<계이름>.json` 스키마로 저장해 이 저장소에 커밋
           (스키마: `eos_recommendations/README.md` 참고)
        """
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render_eos_page():
    st.markdown("#### Data 6: EOS Recommendation for NH₃ Binary Mixtures", unsafe_allow_html=True)

    st.markdown(
        "암모니아 이성분 혼합물에 대해, **문헌 VLE 실측 데이터(Aspen TDE)** 를 기준으로 "
        "후보 상태방정식(EOS)들을 평가하고 이성분 상호작용 파라미터(kij)를 회귀한 결과로부터 "
        "**입력 조건(T, P)에 적합한 EOS와 kij 값**, 그리고 **Aspen Plus/HYSYS에 바로 넣을 물성법·kij**를 추천해 드려요."
    )

    with st.expander("평가 방법이 궁금하다면 클릭하세요."):
        st.markdown(
            """
            각 계의 추천 결과는 아래 워크플로(오프라인)로 생성됩니다.

            1. **문헌 데이터 확보** — Aspen Plus의 NIST TDE에서 해당 이성분계의 문헌 VLE
               실측점(출처 포함)을 `.bkp`로 추출합니다.
            2. **국소 샘플 선택** — 관심 조건 (T\\*, P\\*)를 감싸는 실측 9점을 규칙
               (|ΔT| ≤ 10 °C, 0.3P\\* ≤ P ≤ 3P\\*, T·P bracketing)으로 선택합니다.
               감싸지 못하면 외삽 경고가 결과에 표시됩니다.
            3. **EOS 평가·회귀** — Thermopack(및 자체 구현 PR-BM)으로 후보 EOS별 ① 기본 kij 계산(base) →
               ② 선택 샘플만으로 EOS당 단일 kij 회귀 → ③ 재계산(fit)을 수행하고,
               액상 조성 오차 **x-AARD**(전조성 혼화계는 기포압 AARD)로 순위를 매깁니다. 기상 y는 회귀에
               사용하지 않으며, train/validation 분리로 과적합을 점검합니다.
            4. **시뮬레이터 매핑** — 각 EOS를 Aspen Plus/HYSYS 물성법 이름에 대응시키고(직접 / 근사 / 참고용),
               kij를 Aspen 입력 형식(kaij + kbij·T + kcij/T)으로도 제공합니다. 상용 시뮬레이터에 없는 모델은
               "정확도 상한" 참고용으로 남겨 둡니다.
            5. **결과 등재** — 조건 밴드별 추천 순위·kij·유효범위·경고를
               `eos_recommendations/*.json`으로 커밋하면 이 페이지에 반영됩니다.
            """
        )

    st.divider()

    mixture_choice = st.radio("원하시는 혼합물을 선택해주세요:", list(MIXTURES.keys()))
    filename, display_name = MIXTURES[mixture_choice]
    reco = _load_recommendation(filename)
    sys_key = filename.replace(".json", "")

    st.markdown(f"### {display_name} 혼합물의 EOS 추천", unsafe_allow_html=True)

    if reco is None or reco.get("status") == "pending":
        _render_pending(display_name)
        return

    if reco.get("status") == "example":
        st.warning(
            "⚠️ **예시 데이터입니다.** 화면 구성을 보여드리기 위한 자리표시자 값이며 "
            "실제 평가 결과가 아니에요. 실제 값은 평가 완료 후 JSON 교체 시 반영됩니다."
        )

    source = reco.get("source", {})
    meta_bits = []
    if source.get("n_datasets"):
        meta_bits.append(f"문헌 데이터셋 {source['n_datasets']}개")
    if source.get("n_points"):
        meta_bits.append(f"실측점 {source['n_points']}개")
    if reco.get("generated"):
        meta_bits.append(f"평가일 {reco['generated']}")
    if meta_bits:
        st.caption(" · ".join(meta_bits))
    if source.get("provenance") or reco.get("method"):
        with st.expander("데이터 출처·평가 방법 상세"):
            if source.get("provenance"):
                st.markdown(f"**출처**: {source['provenance']}")
            if reco.get("method"):
                st.markdown(f"**방법**: {reco['method']}")

    metric_label = reco.get("metric_label", "x-AARD")

    bands = reco.get("condition_bands", [])
    if not bands:
        _render_pending(display_name)
        return

    # ------------------------------------------------------------------ inputs
    st.markdown("### 1. 관심 조건 입력")
    t_default = float(0.5 * (bands[0]["T_K"][0] + bands[0]["T_K"][1]))
    p_default = float(0.5 * (bands[0]["P_bar"][0] + bands[0]["P_bar"][1]))

    col_t, col_p = st.columns(2)
    with col_t:
        user_t = st.number_input("온도를 입력해주세요 (K):", min_value=150.0,
                                 max_value=700.0, value=round(t_default, 1), step=5.0)
    with col_p:
        user_p = st.number_input("압력을 입력해주세요 (bar):", min_value=0.1,
                                 max_value=500.0, value=round(p_default, 1), step=1.0)

    band, inside = _find_band(bands, user_t, user_p)

    band_label = band.get("label") or band.get("band_id", "")
    t_lo, t_hi = band["T_K"]
    p_lo, p_hi = band["P_bar"]
    if inside:
        st.success(f"✅ 검증 범위 안 · **{band_label}** 기준")
    else:
        st.warning(f"⚠️ 검증 범위 밖 — 가장 가까운 **{band_label}** 결과를 참고로 보여드려요 (외삽 주의)")
    st.caption(f"이 밴드의 검증 범위: T {t_lo:g}–{t_hi:g} K · P {p_lo:g}–{p_hi:g} bar")

    ranking = band.get("ranking", [])
    if not ranking:
        st.error("이 밴드에는 아직 순위 정보가 없어요.")
        return

    # ------------------------------------------------------------- top picks
    st.markdown("### 2. 추천 결과")
    rec_model = reco.get("recommended_model")
    if rec_model:
        st.info(f"**정밀 계산 권장 모델: {rec_model.get('name', '')}** — {rec_model.get('reason', '')} "
                "아래 EOS 순위는 'EOS를 꼭 써야 할 때'의 차선책이에요.")

    top = _sorted(ranking)[0]
    direct_rows = [r for r in ranking if _mapping(r["eos"])["tier"] == "direct" and not np.isnan(_effective_aard(r))
                   and "탐색 경계" not in (r.get("note") or "")]
    sim_pick = min(direct_rows, key=_effective_aard) if direct_rows else None
    same_pick = sim_pick is not None and sim_pick["eos"] == top["eos"]

    def _cards(entry, title):
        c1, c2, c3 = st.columns(3)
        c1.metric(title, entry.get("eos", "—"))
        c2.metric(f"{entry.get('bip_name', 'kij')} (권장값)", _bip_text(entry),
                  help="회귀값 사용(O)이면 회귀값, 아니면 기본값이에요.")
        aard = _effective_aard(entry)
        c3.metric(f"예상 {metric_label}", f"{100.0 * aard:.1f}%" if not np.isnan(aard) else "—",
                  help="이 대역 문헌 실측점에 대한 평균 상대오차예요.")
        if entry.get("note"):
            st.caption(f"비고: {entry['note']}")

    if same_pick:
        _cards(top, "추천 EOS (1위 · Aspen 직접 사용 가능)")
    else:
        _cards(top, "추천 EOS (1위 · 전체)")
        m_top = _mapping(top["eos"])
        if sim_pick is not None:
            st.caption(f"↑ 전체 1위 **{top['eos']}** 는 상용 시뮬레이터 대응이 '{TIER_LABEL[m_top['tier']]}'이라 "
                       "정확도 상한 참고용이에요. Aspen Plus/HYSYS에서 바로 쓸 수 있는 1위는 아래입니다.")
            _cards(sim_pick, "Aspen에서 바로 쓰는 1위")
        else:
            st.caption("이 대역에는 Aspen Plus에 직접 대응되는 EOS 결과가 없어요.")

    if sim_pick is not None:
        with st.expander("Aspen Plus / HYSYS 입력 카드 — 복사해서 붙여넣기", expanded=True):
            _aspen_card(reco, band, sim_pick, metric_label)
            st.caption("물성상수(Tc·Pc·ω)가 thermopack과 Aspen 데이터뱅크 사이에 미세하게 달라 결과가 소수점 수준으로 "
                       "차이날 수 있어요. Aspen에서 대역 안 조건 2~3점을 플래시해 용해도를 한 번 대조해 보시길 권합니다.")

    # -------------------------------------------------------------- ranking
    st.markdown("### 3. EOS별 상세 비교")
    sim_only = st.toggle("시뮬레이터(Aspen Plus/HYSYS)에서 고를 수 있는 모델만 보기",
                         value=False, key=f"simonly_{sys_key}")
    shown = [r for r in _sorted(ranking) if (not sim_only) or _mapping(r["eos"])["tier"] in ("direct", "cond")]
    table = pd.DataFrame(
        [
            {
                "순위": r.get("rank"),
                "EOS": r.get("eos"),
                "Aspen Plus": _mapping(r["eos"])["aspen"],
                "HYSYS": _mapping(r["eos"])["hysys"],
                "BIP": r.get("bip_name", "kij"),
                "기본값": "" if r.get("bip_default") is None else f"{r['bip_default']:.4g}",
                "회귀값": r.get("bip_display") if r.get("bip_display") else ("" if r.get("bip_fitted") is None else f"{r['bip_fitted']:.4f}"),
                "회귀값 사용": "O" if r.get("use_fitted") else "X",
                f"{metric_label} (기본, %)": None if r.get("x_aard_base") is None else round(100.0 * r["x_aard_base"], 2),
                f"{metric_label} (회귀, %)": None if r.get("x_aard_fit") is None else round(100.0 * r["x_aard_fit"], 2),
                "검증 개선율 (%)": r.get("validation_improvement_pct"),
                "비고": r.get("note", ""),
            }
            for r in shown
        ]
    )
    st.dataframe(table, hide_index=True)
    st.caption("Aspen Plus/HYSYS 열의 * 표시 = 이름은 있으나 파라미터 세트·α 옵션이 달라 근사·재확인 필요. "
               "— = 상용 시뮬레이터에 없음(정확도 상한 참고용).")

    _render_ranking_chart(shown, metric_label, key=f"eos_chart_{sys_key}_{band.get('band_id', '')}_{int(sim_only)}")

    # ------------------------------------------------------------- warnings
    warnings = list(band.get("warnings", []))
    comp_note = reco.get("composition_note")
    if warnings or comp_note:
        st.markdown("### 4. 주의사항")
        if comp_note:
            st.info(comp_note)
        for w in warnings[:3]:
            st.warning(w)
        extra = warnings[3:]
    else:
        extra = []
    case_lines = [f"- (T={c.get('T_K')} K, P={c.get('P_bar')} bar): {c.get('interp_status','')}"
                  for c in band.get("cases", []) if c.get("interp_status")]
    if extra or case_lines:
        with st.expander("평가 케이스·외삽 상세 보기"):
            for w in extra:
                st.markdown(f"- {w}")
            if case_lines:
                st.markdown("**평가 케이스 상태**")
                st.markdown("\n".join(case_lines))

    fits = reco.get("aspen_kij_T") or {}
    if fits:
        with st.expander("kij 온도식 (Aspen PRKBV 형식) — 전 EOS"):
            st.markdown("kij = kaij + kbij·T + kcij/T (T in K). 밴드별 권장 kij를 잇는 보간식이며, 표시된 온도 범위 안에서만 쓰세요.")
            st.dataframe(pd.DataFrame([
                {"EOS": e, "kaij": round(v["kaij"], 5), "kbij": round(v["kbij"], 7), "kcij": round(v["kcij"], 3),
                 "T 범위 (K)": f"{v['T_range_K'][0]:g}–{v['T_range_K'][1]:g}", "밴드 수": v["n_bands"],
                 "밴드값 재현 오차": round(v["max_abs_dev"], 4),
                 "밴드값": ", ".join(f"{b['T_K']:g} K: {b['kij']:+.4f}" for b in v.get("band_values", []))}
                for e, v in fits.items()
            ]), hide_index=True)

    excluded = reco.get("excluded_eos", [])
    if excluded:
        with st.expander("이 계에서 제외된 EOS 확인하기"):
            for e in excluded:
                st.markdown(f"- **{e.get('eos')}** — {e.get('reason', '')}")

    if reco.get("method"):
        st.caption(f"평가 방법: {reco['method']}")
