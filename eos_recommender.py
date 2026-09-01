"""
EOS Recommendation page for SENLAB_NH3DB.

NH3 + X 이성분계에 대해, EOS/BIP 평가 워크플로(문헌 VLE 기반 국소 kij 회귀)의
결과 JSON(eos_recommendations/*.json)을 읽어 조건(T, P)에 맞는 EOS 추천을
보여주는 페이지입니다.

- 평가 자체는 이 앱에서 수행하지 않습니다. Aspen TDE .bkp → EOS/BIP 에이전트
  (Claude cowork + Thermopack) → JSON 커밋 순서로 오프라인에서 생성됩니다.
- JSON 스키마와 생성 방법은 eos_recommendations/README.md 참고.
"""

import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RECO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eos_recommendations")

MIXTURES = {
    "1. $NH_3 + N_2$ 혼합물": ("nh3_n2.json", "NH₃ + N₂"),
    "2. $NH_3 + H_2O$ 혼합물": ("nh3_h2o.json", "NH₃ + H₂O"),
    "3. $NH_3 + H_2$ 혼합물": ("nh3_h2.json", "NH₃ + H₂"),
    "4. $NH_3 + CH_4$ 혼합물": ("nh3_ch4.json", "NH₃ + CH₄"),
}

ACCENT = "#2563EB"   # fitted x-AARD bars (validated: lightness/chroma/contrast pass)
INK = "#374151"      # base x-AARD tick markers (annotation ink, not a series color)
GRID = "#E5E7EB"


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


def _render_ranking_chart(ranking, metric_label="x-AARD"):
    """Horizontal bars: final AARD per EOS (bar) + default-BIP AARD (tick)."""
    rows = [r for r in ranking if not np.isnan(_effective_aard(r))]
    if not rows:
        return
    rows = sorted(rows, key=_effective_aard, reverse=True)  # best ends up on top

    names = [r["eos"] for r in rows]
    final = [100.0 * _effective_aard(r) for r in rows]
    base = [100.0 * r["x_aard_base"] if r.get("x_aard_base") is not None else np.nan
            for r in rows]

    # Axis span: when default-BIP errors dwarf the fitted ones, clip the axis so the bars stay
    # readable, and note the off-scale base values as text at the right edge.
    base_max = np.nanmax(base) if not np.all(np.isnan(base)) else 0.0
    final_max = np.nanmax(final)
    if base_max > 8 * final_max:
        upper = final_max * 1.6
    else:
        upper = max(final_max, base_max) * 1.25
    clipped = [not np.isnan(bv) and bv > upper for bv in base]
    base_plot = [min(bv, upper * 0.985) if not np.isnan(bv) else bv for bv in base]

    fig, ax = plt.subplots(figsize=(5.6, 0.55 * len(rows) + 1.6))
    y = np.arange(len(rows))

    ax.barh(y, final, height=0.55, color=ACCENT, zorder=3,
            label=f"Final {metric_label} (fitted BIP)")
    tick_x = [bv if not c else np.nan for bv, c in zip(base_plot, clipped)]
    ax.scatter(tick_x, y, marker="|", s=220, color=INK, linewidths=2.2, zorder=4,
               label=f"Base {metric_label} (default BIP)")

    for yi, value, base_value, c in zip(y, final, base_plot, clipped):
        # Anchor the label right of both the bar end and the (visible) base tick.
        label_x = value if (np.isnan(base_value) or c) else max(value, base_value)
        ax.annotate(f"{value:.1f}%", xy=(label_x, yi), xytext=(7, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK)
        if c:  # off-scale default-BIP error, noted as text
            ax.annotate(f"base {base[list(y).index(yi)]:.0f}% →", xy=(upper * 0.985, yi), xytext=(-4, 0),
                        textcoords="offset points", va="center", ha="right", fontsize=7.5, color=INK)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel(f"{metric_label} (%)  —  lower is better", fontsize=9)
    ax.tick_params(axis="x", labelsize=9)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.set_xlim(0, upper + 1e-9)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


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
    st.write("**EOS Recommendation (Binary Mixtures)**을 선택하셨네요.")
    st.markdown("#### Data 6: EOS Recommendation for NH₃ Binary Mixtures", unsafe_allow_html=True)

    st.markdown(
        "암모니아 이성분 혼합물에 대해, **문헌 VLE 실측 데이터(Aspen TDE)** 를 기준으로 "
        "후보 상태방정식(EOS)들을 평가하고 이성분 상호작용 파라미터(kij)를 회귀한 결과로부터 "
        "**입력 조건(T, P)에 적합한 EOS와 kij 값을 추천**해 드려요."
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
            3. **EOS 평가·회귀** — Thermopack으로 후보 EOS별 ① 기본 kij 계산(base) →
               ② 선택 샘플만으로 EOS당 단일 kij 회귀 → ③ 재계산(fit)을 수행하고,
               액상 조성 오차 **x-AARD**로 순위를 매깁니다. 기상 y는 회귀에 사용하지
               않으며, train/validation 분리로 과적합을 점검합니다.
            4. **결과 등재** — 조건 밴드별 추천 순위·kij·유효범위·경고를
               `eos_recommendations/*.json`으로 커밋하면 이 페이지에 반영됩니다.
            """
        )

    st.divider()

    mixture_choice = st.radio("원하시는 혼합물을 선택해주세요:", list(MIXTURES.keys()))
    filename, display_name = MIXTURES[mixture_choice]
    reco = _load_recommendation(filename)

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
    if source.get("provenance"):
        meta_bits.append(source["provenance"])
    if source.get("n_datasets"):
        meta_bits.append(f"문헌 데이터셋 {source['n_datasets']}개")
    if source.get("n_points"):
        meta_bits.append(f"실측점 {source['n_points']}개")
    if reco.get("generated"):
        meta_bits.append(f"평가일 {reco['generated']}")
    if meta_bits:
        st.caption(" · ".join(meta_bits))

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
        st.success(
            f"입력 조건이 검증 범위 안에 있어요 — 평가 밴드 **{band_label}** "
            f"(T {t_lo:g}–{t_hi:g} K, P {p_lo:g}–{p_hi:g} bar)의 결과를 보여드릴게요."
        )
    else:
        st.warning(
            f"⚠️ 입력 조건이 검증된 범위 밖이에요. 가장 가까운 평가 밴드 **{band_label}** "
            f"(T {t_lo:g}–{t_hi:g} K, P {p_lo:g}–{p_hi:g} bar)의 결과를 보여드리지만, "
            "이 조건에서는 **외삽**이므로 오차가 표기값보다 커질 수 있어요."
        )

    ranking = band.get("ranking", [])
    if not ranking:
        st.error("이 밴드에는 아직 순위 정보가 없어요.")
        return

    # ------------------------------------------------------------- top pick
    st.markdown("### 2. 추천 결과")
    top = sorted(ranking, key=lambda r: (r.get("rank") is None, r.get("rank", 999)))[0]
    bip_value = top.get("bip_fitted") if top.get("use_fitted") else top.get("bip_default")
    bip_label = top.get("bip_name", "kij")

    col1, col2, col3 = st.columns(3)
    col1.metric("추천 EOS (1위)", top.get("eos", "—"))
    col2.metric(
        f"{bip_label} (권장값)",
        f"{bip_value:.4f}" if bip_value is not None else "기본값",
        help="use_fitted가 참이면 회귀값, 아니면 기본값이에요.",
    )
    aard = _effective_aard(top)
    col3.metric(
        f"예상 {metric_label}",
        f"{100.0 * aard:.1f}%" if not np.isnan(aard) else "—",
        help="검증 케이스에서의 액상 조성 평균 상대오차예요.",
    )

    if top.get("note"):
        st.caption(f"비고: {top['note']}")

    # -------------------------------------------------------------- ranking
    st.markdown("### 3. EOS별 상세 비교")
    table = pd.DataFrame(
        [
            {
                "순위": r.get("rank"),
                "EOS": r.get("eos"),
                "BIP": r.get("bip_name", "kij"),
                "기본값": r.get("bip_default"),
                "회귀값": r.get("bip_fitted"),
                "회귀값 사용": "O" if r.get("use_fitted") else "X",
                f"{metric_label} (기본, %)": None if r.get("x_aard_base") is None else round(100.0 * r["x_aard_base"], 2),
                f"{metric_label} (회귀, %)": None if r.get("x_aard_fit") is None else round(100.0 * r["x_aard_fit"], 2),
                "검증 개선율 (%)": r.get("validation_improvement_pct"),
                "비고": r.get("note", ""),
            }
            for r in sorted(ranking, key=lambda r: (r.get("rank") is None, r.get("rank", 999)))
        ]
    )
    st.dataframe(table, hide_index=True)

    _render_ranking_chart(ranking, metric_label)

    # ------------------------------------------------------------- warnings
    warnings = list(band.get("warnings", []))
    for case in band.get("cases", []):
        status = case.get("interp_status", "")
        if status and status != "INTERP":
            warnings.append(
                f"케이스 (T={case.get('T_K')} K, P={case.get('P_bar')} bar): {status}"
            )
    if warnings:
        st.markdown("### 4. 주의사항")
        for w in warnings:
            st.warning(w)

    excluded = reco.get("excluded_eos", [])
    if excluded:
        with st.expander("이 계에서 제외된 EOS 확인하기"):
            for e in excluded:
                st.markdown(f"- **{e.get('eos')}** — {e.get('reason', '')}")

    if reco.get("method"):
        st.caption(f"평가 방법: {reco['method']}")
