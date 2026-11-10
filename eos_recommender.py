"""
EOS Recommendation page for SENLAB_NH3DB.

Reads the result JSON files of the EOS/BIP evaluation workflow (local kij regression on literature VLE,
eos_recommendations/*.json) for the NH3 + X binaries and shows the EOS recommended for a condition (T, P).

- The evaluation itself is not run in the app: Aspen TDE .bkp -> EOS/BIP agent (Claude cowork + Thermopack /
  in-house PR-BM etc.) -> JSON commit, all offline.
- JSON schema and generation notes: eos_recommendations/README.md.
- v4: Aspen Plus / HYSYS method mapping, simulator-usable pick, Aspen input card (PRKBV-form kij),
  PR-BM/HV rows, NH3+H2O recommended model and composition note, Plotly chart (theme-linked).
- v6: English UI.
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
    "1. $NH_3 + N_2$ — nitrogen": ("nh3_n2.json", "NH₃ + N₂ (nitrogen)"),
    "2. $NH_3 + H_2O$ — water": ("nh3_h2o.json", "NH₃ + H₂O (water)"),
    "3. $NH_3 + H_2$ — hydrogen": ("nh3_h2.json", "NH₃ + H₂ (hydrogen)"),
    "4. $NH_3 + CH_4$ — methane": ("nh3_ch4.json", "NH₃ + CH₄ (methane)"),
}

# Ranking EOS -> simulator property-method mapping.
#   tier "direct": selectable in Aspen Plus with the same equations and the same kij convention
#   tier "cond"  : the name exists but parameter sets / alpha options differ -> approximate, re-check
#   tier "none"  : not available in commercial simulators -> accuracy-ceiling reference only
ASPEN_MAP = {
    "PR":      {"aspen": "PENG-ROB", "param": "PRKBV", "hysys": "Peng-Robinson*", "tier": "direct"},
    "PR-BM":   {"aspen": "PR-BM", "param": "PRKBV", "hysys": "—", "tier": "direct"},
    "SRK":     {"aspen": "RK-SOAVE", "param": "RKSKBV", "hysys": "SRK", "tier": "direct"},
    "RKS-BM":  {"aspen": "RKS-BM (= VLE of the SRK method)", "param": "RKSKBV", "hysys": "SRK*", "tier": "direct"},
    "RK-ASPEN": {"aspen": "RK-ASPEN", "param": "RKAKA0 / RKAKB0", "hysys": "—", "tier": "direct"},
    "SR-POLAR": {"aspen": "SR-POLAR", "param": "SRKKA0 / SRLIJ0", "hysys": "—", "tier": "direct"},
    "NRTL-RK": {"aspen": "NRTL-RK (activity-coefficient model)", "param": "NRTL", "hysys": "NRTL (different τ form)*", "tier": "direct"},
    "tcPR":    {"aspen": "PENG-ROB + Twu α / volume-translation options*", "param": "PRKBV", "hysys": "PR-Twu*", "tier": "cond"},
    "PC-SAFT": {"aspen": "PC-SAFT*", "param": "PCSKIJ", "hysys": "—", "tier": "cond"},
    "CPA":     {"aspen": "CPA (check V12+)*", "param": "—", "hysys": "CPA*", "tier": "cond"},
    "PR (HV-NRTL)": {"aspen": "— (see the PRWS / PRMHV2 family)", "param": "—", "hysys": "—", "tier": "none"},
}
_NO_MAP = {"aspen": "—", "param": "—", "hysys": "—", "tier": "none"}
TIER_LABEL = {"direct": "direct", "cond": "approximate (re-check)", "none": "reference only"}


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
        return f"{value:.4f} (default)"
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
        x=bar_x, y=names, orientation="h", name=f"{metric_label} with the recommended setting",
        text=bar_text, textposition=bar_pos, cliponaxis=False, customdata=final,
        hovertemplate="%{y}: %{customdata:.2f}%<extra></extra>",
        marker_color="#1e3a8a",
    )
    tick_x = [bv if (not np.isnan(bv) and bv <= upper) else np.nan for bv in base]
    if not np.all(np.isnan(tick_x)):
        fig.add_scatter(
            x=tick_x, y=names, mode="markers", name=f"{metric_label} with the default BIP",
            marker=dict(symbol="line-ns-open", size=18, line=dict(width=2.5, color="#b45309")),
            hovertemplate="%{y} default: %{x:.1f}%<extra></extra>",
        )
    for name, bv, fv in zip(names, base, final):
        if not np.isnan(bv) and bv > upper and fv <= upper:
            fig.add_annotation(x=upper * 0.985, y=name, text=f"default {bv:.0f}% →", showarrow=False,
                               xanchor="right", font=dict(size=10), opacity=0.8)

    fig.update_layout(
        height=max(280, 34 * len(rows) + 130),
        margin=dict(l=10, r=70, t=10, b=10),
        xaxis=dict(title=f"{metric_label} (%) — lower is better", range=[0, upper * 1.12], zeroline=False),
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
        f"Aspen Plus method : {m['aspen']}",
        f"Parameter form    : Parameters → Binary Interaction → {m['param']}-1   ({solvent} / {solute})",
    ]
    if pick["eos"] == "NRTL-RK" and pick.get("bip_params"):
        p = pick["bip_params"]
        lines[-1] = "Parameter form    : Parameters → Binary Interaction → NRTL-1   (component i = NH3 (AMMONIA), j = H2O (WATER))"
        lines.append(f"Band constants    : AIJ = 0, AJI = 0, BIJ = {p['b12_K']:+.0f}, BJI = {p['b21_K']:+.0f}, CIJ = {p['alpha']:g}   "
                     f"(τij = BIJ/T, T {t_lo:g}–{t_hi:g} K)   — prefer Aspen's built-in ENRTL-RK parameters when available")
    elif kij is not None:
        lines.append(f"Band constant     : kaij = {kij:.4f}   (T {t_lo:g}–{t_hi:g} K, P {p_lo:g}–{p_hi:g} bar)   ← safest choice")
    elif pick.get("bip_params") and pick.get("use_fitted"):
        vals = ", ".join(f"{k} = {v:+.4f}" for k, v in pick["bip_params"].items())
        lines.append(f"Band constants    : {vals}   (T {t_lo:g}–{t_hi:g} K, P {p_lo:g}–{p_hi:g} bar)")
    if fit and fit.get("n_bands", 0) >= 3:
        lo, hi = fit["T_range_K"]
        lines.append(
            f"All-band T form   : kaij = {fit['kaij']:.4f}, kbij = {fit['kbij']:.6f}, kcij = {fit['kcij']:.2f}"
            f"   (kij = kaij + kbij·T + kcij/T, valid {lo:g}–{hi:g} K only; reproduces the band values within {fit['max_abs_dev']:.3f})"
        )
    if m["hysys"] not in ("—", ""):
        approx = " (the HYSYS version is a modified model — approximate)" if m["hysys"].endswith("*") else ""
        lines.append(f"HYSYS             : {m['hysys'].rstrip('*')} package → enter kij = {kij:.4f} under Binary Coeffs{approx}" if kij is not None
                     else f"HYSYS             : {m['hysys'].rstrip('*')}{approx}")
    else:
        lines.append("HYSYS             : no corresponding property package")
    lines.append(f"Expected accuracy : {metric_label} {100.0 * _effective_aard(pick):.1f}% (against the literature data of this band)")
    st.code("\n".join(lines), language="text")


def _render_pending(display_name):
    st.info(
        f"**The {display_name} system has not been evaluated yet.** Produce the results as below and commit "
        "them; this page then shows them automatically."
    )
    st.markdown(
        """
        1. Register both components in **Aspen Plus**, retrieve the **NIST TDE Binary VLE** data and save it as `.bkp`
        2. In **Claude cowork**, attach the `.bkp` and the evaluation workbook and run "analyse according to the EOS agent
           instructions" (specify the T, P cases of interest)
        3. Save the results in the `eos_recommendations/<system>.json` schema and commit them to this repository
           (schema: see `eos_recommendations/README.md`)
        """
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render_eos_page():
    st.markdown("#### Data 6: EOS Recommendation for NH₃ Binary Mixtures", unsafe_allow_html=True)

    st.markdown(
        "For each ammonia binary mixture, candidate equations of state (EOS) are evaluated against **literature VLE "
        "measurements (Aspen TDE)** and the binary interaction parameter (kij) is regressed. From those results this page "
        "recommends **the EOS and kij suited to your condition (T, P)** and **the property method and kij to enter directly "
        "in Aspen Plus / HYSYS**."
    )

    with st.expander("How the evaluation works"):
        st.markdown(
            """
            The recommendations for each system are generated offline by the following workflow.

            1. **Literature data** — the measured VLE points of the binary (with sources) are extracted from the NIST TDE
               inside Aspen Plus as a `.bkp` file.
            2. **Local sampling** — the measurements bracketing the condition of interest (T\\*, P\\*) are selected by rule
               (|ΔT| ≤ 10 °C, 0.3P\\* ≤ P ≤ 3P\\*, T·P bracketing). When the condition cannot be bracketed, an
               extrapolation warning is attached to the result.
            3. **EOS evaluation and regression** — for every candidate EOS (Thermopack plus in-house Aspen variants)
               ① the default kij is evaluated (base) → ② a single kij per EOS is regressed on the selected sample →
               ③ the cases are recomputed (fit), and the models are ranked by the liquid-composition error **x-AARD**
               (bubble-pressure AARD for the fully miscible system). Vapour compositions y are not used in the regression,
               and a train/validation split guards against over-fitting.
            4. **Simulator mapping** — every EOS is mapped to its Aspen Plus / HYSYS property-method name
               (direct / approximate / reference only) and kij is also provided in the Aspen input form
               (kaij + kbij·T + kcij/T). Models that commercial simulators lack are kept as an "accuracy ceiling".
            5. **Publication** — the ranking, kij, validity range and warnings of each condition band are committed as
               `eos_recommendations/*.json`, which this page reads.
            """
        )

    st.divider()

    mixture_choice = st.radio("Select a mixture:", list(MIXTURES.keys()))
    filename, display_name = MIXTURES[mixture_choice]
    reco = _load_recommendation(filename)
    sys_key = filename.replace(".json", "")

    st.markdown(f"### EOS recommendation for {display_name}", unsafe_allow_html=True)

    if reco is None or reco.get("status") == "pending":
        _render_pending(display_name)
        return

    if reco.get("status") == "example":
        st.warning(
            "⚠️ **Example data.** These are placeholder values that only illustrate the layout, not real "
            "evaluation results. Real values appear once the evaluated JSON replaces this file."
        )

    source = reco.get("source", {})
    meta_bits = []
    if source.get("n_datasets"):
        meta_bits.append(f"{source['n_datasets']} literature data sets")
    if source.get("n_points"):
        meta_bits.append(f"{source['n_points']} measured points")
    if reco.get("generated"):
        meta_bits.append(f"evaluated {reco['generated']}")
    if meta_bits:
        st.caption(" · ".join(meta_bits))
    if source.get("provenance") or reco.get("method"):
        with st.expander("Data sources and evaluation method"):
            if source.get("provenance"):
                st.markdown(f"**Sources**: {source['provenance']}")
            if reco.get("method"):
                st.markdown(f"**Method**: {reco['method']}")

    metric_label = reco.get("metric_label", "x-AARD")

    bands = reco.get("condition_bands", [])
    if not bands:
        _render_pending(display_name)
        return

    # ------------------------------------------------------------------ inputs
    st.markdown("### 1. Condition of interest")
    t_default = float(0.5 * (bands[0]["T_K"][0] + bands[0]["T_K"][1]))
    p_default = float(0.5 * (bands[0]["P_bar"][0] + bands[0]["P_bar"][1]))

    col_t, col_p = st.columns(2)
    with col_t:
        user_t = st.number_input("Temperature (K):", min_value=150.0,
                                 max_value=700.0, value=round(t_default, 1), step=5.0)
    with col_p:
        user_p = st.number_input("Pressure (bar):", min_value=0.1,
                                 max_value=500.0, value=round(p_default, 1), step=1.0)

    band, inside = _find_band(bands, user_t, user_p)

    band_label = band.get("label") or band.get("band_id", "")
    t_lo, t_hi = band["T_K"]
    p_lo, p_hi = band["P_bar"]
    if inside:
        st.success(f"✅ Inside the validated range · **{band_label}**")
    else:
        st.warning(f"⚠️ Outside the validated range — showing the nearest band, **{band_label}**, for reference (extrapolation)")
    st.caption(f"Validated range of this band: T {t_lo:g}–{t_hi:g} K · P {p_lo:g}–{p_hi:g} bar")

    ranking = band.get("ranking", [])
    if not ranking:
        st.error("This band has no ranking yet.")
        return

    # ------------------------------------------------------------- top picks
    st.markdown("### 2. Recommendation")
    rec_model = reco.get("recommended_model")
    if rec_model:
        st.info(f"**Recommended model for design-grade calculations: {rec_model.get('name', '')}** — {rec_model.get('reason', '')} "
                "The EOS ranking below is the fallback for cases where an EOS must be used.")

    top = _sorted(ranking)[0]
    direct_rows = [r for r in ranking if _mapping(r["eos"])["tier"] == "direct" and not np.isnan(_effective_aard(r))
                   and "search bound" not in (r.get("note") or "")]
    sim_pick = min(direct_rows, key=_effective_aard) if direct_rows else None
    same_pick = sim_pick is not None and sim_pick["eos"] == top["eos"]

    def _cards(entry, title):
        c1, c2, c3 = st.columns(3)
        c1.metric(title, entry.get("eos", "—"))
        c2.metric(f"{entry.get('bip_name', 'kij')} (recommended)", _bip_text(entry),
                  help="The regressed value when 'regressed used' is O, otherwise the default value.")
        aard = _effective_aard(entry)
        c3.metric(f"Expected {metric_label}", f"{100.0 * aard:.1f}%" if not np.isnan(aard) else "—",
                  help="Mean relative deviation from the literature measurements of this band.")
        if entry.get("note"):
            st.caption(f"Note: {entry['note']}")

    if same_pick:
        _cards(top, "Recommended EOS (rank 1 · directly usable in Aspen)")
    else:
        _cards(top, "Recommended EOS (rank 1 · overall)")
        m_top = _mapping(top["eos"])
        if sim_pick is not None:
            st.caption(f"↑ The overall rank 1, **{top['eos']}**, maps to commercial simulators only as "
                       f"'{TIER_LABEL[m_top['tier']]}', so treat it as the accuracy ceiling. The best model you can select "
                       "directly in Aspen Plus / HYSYS is below.")
            _cards(sim_pick, "Best directly usable in Aspen")
        else:
            st.caption("No EOS with a direct Aspen Plus counterpart is available in this band.")

    if sim_pick is not None:
        with st.expander("Aspen Plus / HYSYS input card — copy and paste", expanded=True):
            _aspen_card(reco, band, sim_pick, metric_label)
            st.caption("Pure-component constants (Tc, Pc, ω) differ slightly between thermopack and the Aspen databank, so results "
                       "may differ in the last digits. Flash 2–3 in-band conditions in Aspen and compare the solubility once.")

    # -------------------------------------------------------------- ranking
    st.markdown("### 3. Model-by-model comparison")
    sim_only = st.toggle("Show only models selectable in Aspen Plus / HYSYS",
                         value=False, key=f"simonly_{sys_key}")
    shown = [r for r in _sorted(ranking) if (not sim_only) or _mapping(r["eos"])["tier"] in ("direct", "cond")]
    table = pd.DataFrame(
        [
            {
                "Rank": r.get("rank"),
                "EOS": r.get("eos"),
                "Aspen Plus": _mapping(r["eos"])["aspen"],
                "HYSYS": _mapping(r["eos"])["hysys"],
                "BIP": r.get("bip_name", "kij"),
                "Default": "" if r.get("bip_default") is None else f"{r['bip_default']:.4g}",
                "Regressed": r.get("bip_display") if r.get("bip_display") else ("" if r.get("bip_fitted") is None else f"{r['bip_fitted']:.4f}"),
                "Regressed used": "O" if r.get("use_fitted") else "X",
                f"{metric_label} (default, %)": None if r.get("x_aard_base") is None else round(100.0 * r["x_aard_base"], 2),
                f"{metric_label} (regressed, %)": None if r.get("x_aard_fit") is None else round(100.0 * r["x_aard_fit"], 2),
                "Validation improvement (%)": r.get("validation_improvement_pct"),
                "Note": r.get("note", ""),
            }
            for r in shown
        ]
    )
    st.dataframe(table, hide_index=True)
    st.caption("* in the Aspen Plus / HYSYS columns = the name exists but parameter sets or α options differ (approximate, re-check). "
               "— = not available in commercial simulators (accuracy-ceiling reference).")

    _render_ranking_chart(shown, metric_label, key=f"eos_chart_{sys_key}_{band.get('band_id', '')}_{int(sim_only)}")

    # ------------------------------------------------------------- warnings
    warnings = list(band.get("warnings", []))
    comp_note = reco.get("composition_note")
    if warnings or comp_note:
        st.markdown("### 4. Notes and warnings")
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
        with st.expander("Evaluation cases and extrapolation details"):
            for w in extra:
                st.markdown(f"- {w}")
            if case_lines:
                st.markdown("**Case status**")
                st.markdown("\n".join(case_lines))

    fits = reco.get("aspen_kij_T") or {}
    if fits:
        with st.expander("kij temperature form (Aspen PRKBV form) — all EOS"):
            st.markdown("kij = kaij + kbij·T + kcij/T (T in K). An interpolation through the recommended band values — use it only inside the stated temperature range.")
            st.dataframe(pd.DataFrame([
                {"EOS": e, "kaij": round(v["kaij"], 5), "kbij": round(v["kbij"], 7), "kcij": round(v["kcij"], 3),
                 "T range (K)": f"{v['T_range_K'][0]:g}–{v['T_range_K'][1]:g}", "Bands": v["n_bands"],
                 "Max. deviation from band values": round(v["max_abs_dev"], 4),
                 "Band values": ", ".join(f"{b['T_K']:g} K: {b['kij']:+.4f}" for b in v.get("band_values", []))}
                for e, v in fits.items()
            ]), hide_index=True)

    excluded = reco.get("excluded_eos", [])
    if excluded:
        with st.expander("EOS excluded for this system"):
            for e in excluded:
                st.markdown(f"- **{e.get('eos')}** — {e.get('reason', '')}")

    if reco.get("method"):
        st.caption(f"Evaluation method: {reco['method']}")
