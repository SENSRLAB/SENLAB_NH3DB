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
- v7: bilingual UI (English / Korean) via i18n.t(); JSON text fields have *_ko siblings read by i18n.pick().
"""

import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from i18n import pick, t
from i18n import radio as radio_i18n

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RECO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eos_recommendations")

# Stable mixture keys (used as radio values); the labels are i18n strings "eos.mix.<key>" / "eos.name.<key>".
MIXTURES = {
    "n2": "nh3_n2.json",
    "h2o": "nh3_h2o.json",
    "h2": "nh3_h2.json",
    "ch4": "nh3_ch4.json",
}

# Ranking EOS -> simulator property-method mapping.
#   tier "direct": selectable in Aspen Plus with the same equations and the same kij convention
#   tier "cond"  : the name exists but parameter sets / alpha options differ -> approximate, re-check
#   tier "none"  : not available in commercial simulators -> accuracy-ceiling reference only
ASPEN_MAP = {
    "PR":      {"aspen": "PENG-ROB", "param": "PRKBV", "hysys": "Peng-Robinson*", "tier": "direct"},
    "PR-BM":   {"aspen": "PR-BM", "param": "PRKBV", "hysys": "—", "tier": "direct"},
    "SRK":     {"aspen": "RK-SOAVE", "param": "RKSKBV", "hysys": "SRK", "tier": "direct"},
    "RKS-BM":  {"aspen": "@eos.map.rksbm", "param": "RKSKBV", "hysys": "SRK*", "tier": "direct"},
    "RK-ASPEN": {"aspen": "RK-ASPEN", "param": "RKAKA0 / RKAKB0", "hysys": "—", "tier": "direct"},
    "SR-POLAR": {"aspen": "SR-POLAR", "param": "SRKKA0 / SRLIJ0", "hysys": "—", "tier": "direct"},
    "NRTL-RK": {"aspen": "@eos.map.nrtl", "param": "NRTL", "hysys": "@eos.map.nrtl_hysys", "tier": "direct"},
    "tcPR":    {"aspen": "@eos.map.tcpr", "param": "PRKBV", "hysys": "PR-Twu*", "tier": "cond"},
    "PC-SAFT": {"aspen": "PC-SAFT*", "param": "PCSKIJ", "hysys": "—", "tier": "cond"},
    "CPA":     {"aspen": "@eos.map.cpa", "param": "—", "hysys": "CPA*", "tier": "cond"},
    "PR (HV-NRTL)": {"aspen": "@eos.map.hv", "param": "—", "hysys": "—", "tier": "none"},
}
_NO_MAP = {"aspen": "—", "param": "—", "hysys": "—", "tier": "none"}


def _tier_label(tier):
    return t("eos.tier." + tier)


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
        return t("eos.default_suffix", v=value)
    return "—"


def _mapping(eos):
    """Simulator mapping of an EOS with "@key" entries resolved to the current language."""
    m = ASPEN_MAP.get(eos, _NO_MAP)
    return {k: (t(v[1:]) if isinstance(v, str) and v.startswith("@") else v) for k, v in m.items()}


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
        x=bar_x, y=names, orientation="h", name=t("eos.chart.bar", metric=metric_label),
        text=bar_text, textposition=bar_pos, cliponaxis=False, customdata=final,
        hovertemplate="%{y}: %{customdata:.2f}%<extra></extra>",
        marker_color="#1e3a8a",
    )
    tick_x = [bv if (not np.isnan(bv) and bv <= upper) else np.nan for bv in base]
    if not np.all(np.isnan(tick_x)):
        fig.add_scatter(
            x=tick_x, y=names, mode="markers", name=t("eos.chart.tick", metric=metric_label),
            marker=dict(symbol="line-ns-open", size=18, line=dict(width=2.5, color="#b45309")),
            hovertemplate=t("eos.chart.tick_hover"),
        )
    for name, bv, fv in zip(names, base, final):
        if not np.isnan(bv) and bv > upper and fv <= upper:
            fig.add_annotation(x=upper * 0.985, y=name, text=t("eos.chart.off", v=bv), showarrow=False,
                               xanchor="right", font=dict(size=10), opacity=0.8)

    fig.update_layout(
        height=max(280, 34 * len(rows) + 130),
        margin=dict(l=10, r=70, t=10, b=10),
        xaxis=dict(title=t("eos.chart.xaxis", metric=metric_label), range=[0, upper * 1.12], zeroline=False),
        yaxis=dict(title=None),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        bargap=0.35,
    )
    st.plotly_chart(fig, width="stretch", key=key)


def _aspen_card(reco, band, pick_row, metric_label):
    """Copy-ready Aspen Plus / HYSYS input block for the simulator-usable pick."""
    m = _mapping(pick_row["eos"])
    solvent, solute = reco.get("solvent", "NH3"), reco.get("solute", "X")
    kij = _effective_bip(pick_row)
    t_lo, t_hi = band["T_K"]
    p_lo, p_hi = band["P_bar"]
    fit = (reco.get("aspen_kij_T") or {}).get(pick_row["eos"])
    rng = dict(tlo=t_lo, thi=t_hi, plo=p_lo, phi=p_hi)
    lines = [
        t("eos.card.l_method", v=m["aspen"]),
        t("eos.card.l_param", param=m["param"], a=solvent, b=solute),
    ]
    if pick_row["eos"] == "NRTL-RK" and pick_row.get("bip_params"):
        p = pick_row["bip_params"]
        lines[-1] = t("eos.card.l_param_nrtl")
        lines.append(t("eos.card.l_nrtl", b12=p["b12_K"], b21=p["b21_K"], alpha=p["alpha"], **rng))
    elif kij is not None:
        lines.append(t("eos.card.l_kij", kij=kij, **rng))
    elif pick_row.get("bip_params") and pick_row.get("use_fitted"):
        vals = ", ".join(f"{k} = {v:+.4f}" for k, v in pick_row["bip_params"].items())
        lines.append(t("eos.card.l_params", vals=vals, **rng))
    if fit and fit.get("n_bands", 0) >= 3:
        lo, hi = fit["T_range_K"]
        lines.append(t("eos.card.l_tform", ka=fit["kaij"], kb=fit["kbij"], kc=fit["kcij"], lo=lo, hi=hi, dev=fit["max_abs_dev"]))
    if m["hysys"] not in ("—", ""):
        approx = t("eos.card.l_hysys_approx") if m["hysys"].endswith("*") else ""
        pkg = m["hysys"].rstrip("*")
        lines.append(t("eos.card.l_hysys_kij", pkg=pkg, kij=kij, approx=approx) if kij is not None
                     else t("eos.card.l_hysys", pkg=pkg, approx=approx))
    else:
        lines.append(t("eos.card.l_hysys_none"))
    lines.append(t("eos.card.l_accuracy", metric=metric_label, v=100.0 * _effective_aard(pick_row)))
    st.code("\n".join(lines), language="text")


def _render_pending(display_name):
    st.info(t("eos.pending", name=display_name))
    st.markdown(t("eos.pending_md"))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render_eos_page():
    st.markdown(t("eos.title"), unsafe_allow_html=True)
    st.markdown(t("eos.intro"))

    with st.expander(t("eos.how_title")):
        st.markdown(t("eos.how_md"))

    st.divider()

    mix = radio_i18n("eos.select_mixture", list(MIXTURES), lambda k: t("eos.mix." + k), key="eos_mix")
    filename = MIXTURES[mix]
    display_name = t("eos.name." + mix)
    reco = _load_recommendation(filename)
    sys_key = filename.replace(".json", "")

    st.markdown(t("eos.heading", name=display_name), unsafe_allow_html=True)

    if reco is None or reco.get("status") == "pending":
        _render_pending(display_name)
        return

    if reco.get("status") == "example":
        st.warning(t("eos.example"))

    source = reco.get("source", {})
    meta_bits = []
    if source.get("n_datasets"):
        meta_bits.append(t("eos.meta.datasets", n=source["n_datasets"]))
    if source.get("n_points"):
        meta_bits.append(t("eos.meta.points", n=source["n_points"]))
    if reco.get("generated"):
        meta_bits.append(t("eos.meta.generated", d=reco["generated"]))
    if meta_bits:
        st.caption(" · ".join(meta_bits))
    provenance, method = pick(source, "provenance"), pick(reco, "method")
    if provenance or method:
        with st.expander(t("eos.sources_expander")):
            if provenance:
                st.markdown(f"{t('eos.sources')}: {provenance}")
            if method:
                st.markdown(f"{t('eos.method')}: {method}")

    metric_label = reco.get("metric_label", "x-AARD")

    bands = reco.get("condition_bands", [])
    if not bands:
        _render_pending(display_name)
        return

    # ------------------------------------------------------------------ inputs
    st.markdown(t("eos.s1"))
    t_default = float(0.5 * (bands[0]["T_K"][0] + bands[0]["T_K"][1]))
    p_default = float(0.5 * (bands[0]["P_bar"][0] + bands[0]["P_bar"][1]))

    col_t, col_p = st.columns(2)
    with col_t:
        user_t = st.number_input(t("eos.T_input"), min_value=150.0,
                                 max_value=700.0, value=round(t_default, 1), step=5.0, key=f"eos_T_{sys_key}")
    with col_p:
        user_p = st.number_input(t("eos.P_input"), min_value=0.1,
                                 max_value=500.0, value=round(p_default, 1), step=1.0, key=f"eos_P_{sys_key}")

    band, inside = _find_band(bands, user_t, user_p)

    band_label = pick(band, "label") or band.get("band_id", "")
    t_lo, t_hi = band["T_K"]
    p_lo, p_hi = band["P_bar"]
    if inside:
        st.success(t("eos.inside", band=band_label))
    else:
        st.warning(t("eos.outside", band=band_label))
    st.caption(t("eos.band_range", tlo=t_lo, thi=t_hi, plo=p_lo, phi=p_hi))

    ranking = band.get("ranking", [])
    if not ranking:
        st.error(t("eos.no_ranking"))
        return

    # ------------------------------------------------------------- top picks
    st.markdown(t("eos.s2"))
    rec_model = reco.get("recommended_model")
    if rec_model:
        st.info(t("eos.rec_model", name=pick(rec_model, "name"), reason=pick(rec_model, "reason")))

    top = _sorted(ranking)[0]
    direct_rows = [r for r in ranking if _mapping(r["eos"])["tier"] == "direct" and not np.isnan(_effective_aard(r))
                   and "search bound" not in (r.get("note") or "")]
    sim_pick = min(direct_rows, key=_effective_aard) if direct_rows else None
    same_pick = sim_pick is not None and sim_pick["eos"] == top["eos"]

    def _cards(entry, title):
        c1, c2, c3 = st.columns(3)
        c1.metric(title, entry.get("eos", "—"))
        c2.metric(t("eos.card.bip", bip=entry.get("bip_name", "kij")), _bip_text(entry), help=t("eos.card.bip_help"))
        aard = _effective_aard(entry)
        c3.metric(t("eos.card.aard", metric=metric_label), f"{100.0 * aard:.1f}%" if not np.isnan(aard) else "—",
                  help=t("eos.card.aard_help"))
        note = pick(entry, "note")
        if note:
            st.caption(t("eos.card.note", note=note))

    if same_pick:
        _cards(top, t("eos.card.top_direct"))
    else:
        _cards(top, t("eos.card.top_overall"))
        m_top = _mapping(top["eos"])
        if sim_pick is not None:
            st.caption(t("eos.card.top_caption", eos=top["eos"], tier=_tier_label(m_top["tier"])))
            _cards(sim_pick, t("eos.card.aspen_pick"))
        else:
            st.caption(t("eos.card.no_direct"))

    if sim_pick is not None:
        with st.expander(t("eos.aspen_card_title"), expanded=True):
            _aspen_card(reco, band, sim_pick, metric_label)
            st.caption(t("eos.aspen_card_caption"))

    # -------------------------------------------------------------- ranking
    st.markdown(t("eos.s3"))
    sim_only = st.toggle(t("eos.sim_only"), value=False, key=f"simonly_{sys_key}")
    shown = [r for r in _sorted(ranking) if (not sim_only) or _mapping(r["eos"])["tier"] in ("direct", "cond")]
    table = pd.DataFrame(
        [
            {
                t("eos.col.rank"): r.get("rank"),
                "EOS": r.get("eos"),
                "Aspen Plus": _mapping(r["eos"])["aspen"],
                "HYSYS": _mapping(r["eos"])["hysys"],
                "BIP": r.get("bip_name", "kij"),
                t("eos.col.default"): "" if r.get("bip_default") is None else f"{r['bip_default']:.4g}",
                t("eos.col.regressed"): r.get("bip_display") if r.get("bip_display") else ("" if r.get("bip_fitted") is None else f"{r['bip_fitted']:.4f}"),
                t("eos.col.used"): "O" if r.get("use_fitted") else "X",
                t("eos.col.aard_base", metric=metric_label): None if r.get("x_aard_base") is None else round(100.0 * r["x_aard_base"], 2),
                t("eos.col.aard_fit", metric=metric_label): None if r.get("x_aard_fit") is None else round(100.0 * r["x_aard_fit"], 2),
                t("eos.col.improvement"): r.get("validation_improvement_pct"),
                t("eos.col.note"): pick(r, "note"),
            }
            for r in shown
        ]
    )
    st.dataframe(table, hide_index=True)
    st.caption(t("eos.table_caption"))

    _render_ranking_chart(shown, metric_label, key=f"eos_chart_{sys_key}_{band.get('band_id', '')}_{int(sim_only)}")

    # ------------------------------------------------------------- warnings
    warnings = list(pick(band, "warnings") or [])
    comp_note = pick(reco, "composition_note")
    if warnings or comp_note:
        st.markdown(t("eos.s4"))
        if comp_note:
            st.info(comp_note)
        for w in warnings[:3]:
            st.warning(w)
        extra = warnings[3:]
    else:
        extra = []
    case_lines = [f"- (T={c.get('T_K')} K, P={c.get('P_bar')} bar): {pick(c, 'interp_status')}"
                  for c in band.get("cases", []) if c.get("interp_status")]
    if extra or case_lines:
        with st.expander(t("eos.cases_expander")):
            for w in extra:
                st.markdown(f"- {w}")
            if case_lines:
                st.markdown(t("eos.cases_title"))
                st.markdown("\n".join(case_lines))

    fits = reco.get("aspen_kij_T") or {}
    if fits:
        with st.expander(t("eos.kijT_expander")):
            st.markdown(t("eos.kijT_md"))
            st.dataframe(pd.DataFrame([
                {"EOS": e, "kaij": round(v["kaij"], 5), "kbij": round(v["kbij"], 7), "kcij": round(v["kcij"], 3),
                 t("eos.kijT.range"): f"{v['T_range_K'][0]:g}–{v['T_range_K'][1]:g}", t("eos.kijT.bands"): v["n_bands"],
                 t("eos.kijT.dev"): round(v["max_abs_dev"], 4),
                 t("eos.kijT.values"): ", ".join(f"{b['T_K']:g} K: {b['kij']:+.4f}" for b in v.get("band_values", []))}
                for e, v in fits.items()
            ]), hide_index=True)

    excluded = reco.get("excluded_eos", [])
    if excluded:
        with st.expander(t("eos.excluded_expander")):
            for e in excluded:
                st.markdown(f"- **{e.get('eos')}** — {pick(e, 'reason')}")

    if method:
        st.caption(t("eos.method_caption", m=method))
