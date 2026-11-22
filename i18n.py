# -*- coding: utf-8 -*-
"""Bilingual (English / Korean) strings for the SENLAB ammonia database app.

Usage
-----
    from i18n import t, get_lang, pick
    st.markdown(t("home.intro"))            # text in the current language
    label = pick(band, "label")             # JSON field: band["label_ko"] in Korean mode when present, else band["label"]

The language lives in st.session_state["lang"] ("en" | "ko"); it is also mirrored in the URL query string (?lang=ko)
so that a link can open the app in a given language. Add a new string by adding one entry to STRINGS.
"""
import streamlit as st

try:  # semi-public API; only used to detect calls made outside a script run
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:  # pragma: no cover
    def get_script_run_ctx():
        return object()

LANGS = {"en": "English", "ko": "한국어"}
DEFAULT_LANG = "en"
_LAST_LANG = DEFAULT_LANG  # language of the most recent script run; read only when no run context exists
#                            (Streamlit's AppTest formats widget labels after a run, outside any context)


def get_lang():
    global _LAST_LANG
    if get_script_run_ctx() is None:
        return _LAST_LANG
    lang = st.session_state.get("lang")
    if lang not in LANGS:
        q = st.query_params.get("lang", DEFAULT_LANG)
        lang = q if q in LANGS else DEFAULT_LANG
        st.session_state["lang"] = lang
    _LAST_LANG = lang
    return lang


def set_lang(lang):
    if lang in LANGS:
        st.session_state["lang"] = lang
        st.query_params["lang"] = lang


def t(key, **kwargs):
    """String `key` in the current language (falls back to English, then to the key itself)."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(get_lang()) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text


def radio(label_key, options, labels, key, default=None, **kwargs):
    """st.radio whose option labels follow the interface language without losing the selection.

    Streamlit's radio forgets its visual selection when the option labels change (the backend value survives,
    the frontend shows nothing selected). The widget is therefore keyed per language (`<key>__<lang>`) and the
    selected option is mirrored in session state under `<key>` so that a re-created radio starts on it.

    labels : dict option -> i18n key, or a callable option -> text.
    Returns the selected option (one of `options`, never a label).
    """
    opts = list(options)
    lang = get_lang()
    wkey = f"{key}__{lang}"
    cur = st.session_state.get(key, default if default is not None else opts[0])
    if cur not in opts:
        cur = opts[0]
    fmt = labels if callable(labels) else (lambda k: t(labels[k]))

    def _sync():
        st.session_state[key] = st.session_state[wkey]

    value = st.radio(t(label_key), opts, index=opts.index(cur), format_func=fmt, key=wkey, on_change=_sync, **kwargs)
    st.session_state[key] = value
    return value


def pick(obj, key, default=""):
    """Localised field of a JSON object: obj[key + '_ko'] in Korean mode when present, else obj[key]."""
    if not isinstance(obj, dict):
        return default
    if get_lang() == "ko" and obj.get(key + "_ko") not in (None, "", []):
        return obj[key + "_ko"]
    return obj.get(key, default)


STRINGS = {
    # ------------------------------------------------------------------ navigation / header
    "nav.home": {"en": "Home", "ko": "홈"},
    "nav.vp": {"en": "Vapor Pressure", "ko": "증기압"},
    "nav.density": {"en": "Density", "ko": "밀도"},
    "nav.cp": {"en": "Heat Capacity", "ko": "비열 (Shomate)"},
    "nav.dew": {"en": "Dew & Bubble Point", "ko": "이슬점 · 거품점"},
    "nav.lhv": {"en": "NH₃–H₂ Blend LHV", "ko": "NH₃·H₂ 혼소 발열량"},
    "nav.eos": {"en": "EOS Recommendation", "ko": "EOS 추천 (이성분계)"},
    "header.caption": {
        "en": "SENLAB Ammonia Properties Database · Sustainable Energy Network Lab., Seoul National University — "
              "thermophysical properties of ammonia and its mixtures (H₂O, H₂, N₂, CH₄) from literature data.",
        "ko": "SENLAB 암모니아 물성 데이터베이스 · 서울대학교 Sustainable Energy Network Lab. — 암모니아 및 혼합물(H₂O, H₂, N₂, CH₄)의 "
              "주요 물성을 문헌 데이터 기반으로 검색하고 시각화합니다."},
    "header.about_lab": {"en": "About Lab", "ko": "연구실 소개"},
    "header.about_title": {"en": "About this database · how to use", "ko": "이 데이터베이스에 대해 · 사용 방법"},
    "header.about_included": {
        "en": "**What's included**\n"
              "- Vapor pressure — saturation pressure of NH₃ at a given temperature\n"
              "- Density — NH₃ gas density versus temperature\n"
              "- Heat capacity — Cp°, ΔH and S° from the Shomate equation\n"
              "- Dew / bubble points — pure NH₃ and the H₂O, H₂, N₂, CH₄ binaries\n"
              "- NH₃–H₂ fuel-blend heating value · EOS recommendation",
        "ko": "**수록 내용**\n"
              "- 증기압 (Vapor Pressure) — 특정 온도에서 액체와 평형을 이루는 포화 증기의 압력\n"
              "- 밀도 (Density) — 온도에 따른 단위 부피당 질량\n"
              "- 비열 (Specific Heat) — Shomate 방정식 기반 Cp°, ΔH, S°\n"
              "- 이슬점 / 거품점 (Dew / Bubble Point) — 순수 NH₃ 및 H₂O·H₂·N₂·CH₄ 이성분계\n"
              "- NH₃·H₂ 혼소 연료 발열량 · EOS 추천"},
    "header.about_howto": {
        "en": "**How to use**\n"
              "1. Pick a property in the menu below (or a service card on the Home page)\n"
              "2. Enter the temperature, pressure or composition in the left card\n"
              "3. The values (cards) and the chart (right) update immediately; ◆ on the chart marks your input",
        "ko": "**사용 방법**\n"
              "1. 아래 메뉴(또는 홈 화면의 서비스 카드)에서 물성을 선택하고\n"
              "2. 왼쪽 카드에 온도·압력·조성 조건을 입력하면\n"
              "3. 값(카드)과 그래프(오른쪽)가 즉시 갱신됩니다. 그래프 위 ◆ 가 입력 조건입니다."},
    "header.select": {"en": "Select a property", "ko": "물성 선택"},
    "header.select_hint": {"en": "Select a property above.", "ko": "위에서 물성을 하나 선택하세요."},
    "sidebar.contributors": {"en": "Contributors", "ko": "기여자"},
    "sidebar.supervisor": {"en": "Supervisor", "ko": "지도교수"},
    "sidebar.homepage": {"en": "Sustainable Energy Network Lab. Homepage", "ko": "Sustainable Energy Network Lab. 홈페이지"},
    "sidebar.language": {"en": "Language", "ko": "언어"},

    # ------------------------------------------------------------------ home (landing)
    "home.intro": {
        "en": "The **SENLAB Ammonia Properties Database** is an open, literature-based collection of thermophysical "
              "property data for ammonia and its mixtures with water, hydrogen, nitrogen and methane. It was established by "
              "the Sustainable Energy Network Laboratory (SENLAB) at Seoul National University to support research, "
              "education and engineering of ammonia as a fuel.\n\n"
              "Data are collected from peer-reviewed journals and NIST sources (ThermoData Engine, Chemistry WebBook). "
              "Where measurements are unavailable, evaluated extrapolations are provided and clearly flagged, and "
              "equation-of-state parameters regressed on the literature data are supplied in Aspen Plus-ready form.",
        "ko": "**SENLAB 암모니아 물성 데이터베이스**는 암모니아와 그 혼합물(물·수소·질소·메탄)의 열물성을 문헌 데이터 기반으로 모아 "
              "공개하는 데이터베이스입니다. 서울대학교 Sustainable Energy Network Lab.(SENLAB)이 암모니아 연료 연구·교육·설계를 "
              "지원하기 위해 구축했습니다.\n\n"
              "데이터는 동료심사 학술지와 NIST 자료(ThermoData Engine, Chemistry WebBook)에서 수집했습니다. 실측이 없는 구간은 "
              "평가된 외삽값을 제공하되 외삽임을 분명히 표시하고, 문헌 데이터로 회귀한 상태방정식 파라미터는 Aspen Plus에 "
              "바로 넣을 수 있는 형식으로 제공합니다."},
    "home.learn_more": {"en": "Learn more about SENLAB", "ko": "SENLAB 더 알아보기"},
    "home.services": {"en": "Online Services", "ko": "온라인 서비스"},
    "home.open": {"en": "Open", "ko": "열기"},
    "home.svc.vp.title": {"en": "Vapor pressure of NH₃", "ko": "NH₃ 증기압"},
    "home.svc.vp.desc": {"en": "Saturation pressure versus temperature, 240–405 K, interpolated from literature data.",
                         "ko": "온도에 따른 포화 증기압, 240–405 K, 문헌값 보간."},
    "home.svc.density.title": {"en": "Density of NH₃ gas", "ko": "NH₃ 기체 밀도"},
    "home.svc.density.desc": {"en": "Gas density at atmospheric pressure, −35 to 400 °C.", "ko": "대기압 기체 밀도, −35 ~ 400 °C."},
    "home.svc.cp.title": {"en": "Heat capacity (Shomate)", "ko": "비열 (Shomate)"},
    "home.svc.cp.desc": {"en": "Cp°, H° − H°₂₉₈ and S° of ammonia gas, 200–1400 K (NIST Shomate equation).",
                         "ko": "암모니아 기체의 Cp°, H° − H°₂₉₈, S°, 200–1400 K (NIST Shomate 방정식)."},
    "home.svc.dew.title": {"en": "Dew and bubble points", "ko": "이슬점 · 거품점"},
    "home.svc.dew.desc": {"en": "Pure NH₃ and the binaries NH₃ + H₂O, H₂, N₂ and CH₄ from literature VLE data.",
                          "ko": "순수 NH₃ 및 NH₃ + H₂O·H₂·N₂·CH₄ 이성분계, 문헌 VLE 데이터 기반."},
    "home.svc.lhv.title": {"en": "NH₃–H₂ fuel-blend heating value", "ko": "NH₃·H₂ 혼소 연료 발열량"},
    "home.svc.lhv.desc": {"en": "Lower heating value, density and volumetric energy of ammonia–hydrogen blends.",
                          "ko": "암모니아·수소 혼합 연료의 저위발열량·밀도·부피당 에너지."},
    "home.svc.eos.title": {"en": "EOS recommendation", "ko": "EOS 추천"},
    "home.svc.eos.desc": {"en": "Which equation of state and kij to use for each binary and condition, with Aspen Plus-ready input.",
                          "ko": "이성분계·조건별로 어떤 상태방정식과 kij를 쓸지 추천하고 Aspen Plus 입력값까지 제공."},
    "home.contains": {"en": "Database contains", "ko": "데이터베이스 구성"},
    "home.contains.pure.title": {"en": "Pure ammonia", "ko": "순수 암모니아"},
    "home.contains.pure.body": {
        "en": "- Vapor pressure, 240–405 K\n- Gas density, −35 to 400 °C\n- Cp°, H° − H°₂₉₈, S°, 200–1400 K (Shomate)",
        "ko": "- 증기압, 240–405 K\n- 기체 밀도, −35 ~ 400 °C\n- Cp°, H° − H°₂₉₈, S°, 200–1400 K (Shomate)"},
    "home.contains.binary.title": {"en": "Binary mixtures", "ko": "이성분 혼합물"},
    "home.contains.binary.body": {
        "en": "- NH₃ + H₂O dew and bubble lines, 220–560 K, ≤ 10 MPa\n"
              "- NH₃ + H₂, N₂, CH₄ dew and bubble lines (Reamer & Sage, Lentz & Weber)\n"
              "- NH₃–H₂ fuel-blend LHV and density, −50 to 130 °C",
        "ko": "- NH₃ + H₂O 이슬선·거품선, 220–560 K, ≤ 10 MPa\n"
              "- NH₃ + H₂·N₂·CH₄ 이슬선·거품선 (Reamer & Sage, Lentz & Weber)\n"
              "- NH₃·H₂ 혼소 연료 LHV·밀도, −50 ~ 130 °C"},
    "home.contains.eos.title": {"en": "EOS recommendations", "ko": "EOS 추천"},
    "home.contains.eos.body": {
        "en": "- 4 binaries, 17 temperature–pressure bands\n"
              "- 13 models: Thermopack EOS + Aspen variants (PR-BM, RKS-BM, RK-ASPEN, SR-POLAR) + NRTL-RK\n"
              "- Regressed kij in Aspen PRKBV form, dew-line checks, extrapolation flags",
        "ko": "- 이성분계 4종, 온도·압력 대역 17개\n"
              "- 모델 13종: Thermopack EOS + Aspen 변형(PR-BM, RKS-BM, RK-ASPEN, SR-POLAR) + NRTL-RK\n"
              "- Aspen PRKBV 형식의 회귀 kij, 이슬선 검증, 외삽 표시"},
    "home.updates": {"en": "Updates", "ko": "업데이트"},
    "home.last_update": {"en": "Last major update to the site: {date}", "ko": "최근 주요 업데이트: {date}"},
    "home.update.1": {
        "en": "EOS recommendation v5.4 — full re-evaluation on Aspen TDE (NIST) V14 data; Aspen-selectable variants "
              "(PR-BM, RKS-BM, RK-ASPEN, SR-POLAR); NRTL-RK activity-coefficient row for NH₃ + H₂O; "
              "independent dew-line (vapour-composition) check for NH₃ + N₂ and NH₃ + CH₄.",
        "ko": "EOS 추천 v5.4 — Aspen TDE(NIST) V14 데이터로 전면 재평가; Aspen에서 선택 가능한 변형(PR-BM, RKS-BM, RK-ASPEN, SR-POLAR) 추가; "
              "NH₃ + H₂O에 활성계수 모델 NRTL-RK 행 추가; NH₃ + N₂·CH₄ 이슬선(기상 조성) 독립 검증."},
    "home.update.2": {"en": "Bilingual (English / Korean) interface, light theme and a redesigned landing page.",
                      "ko": "영어/한국어 전환 인터페이스, 라이트 테마, 새 첫 화면."},

    # ------------------------------------------------------------------ shared page strings
    "p.input": {"en": "**Input**", "ko": "**조건 입력**"},
    "p.known": {"en": "Known quantity", "ko": "알고 있는 값"},
    "p.temperature": {"en": "Temperature", "ko": "온도"},
    "p.pressure": {"en": "Pressure", "ko": "압력"},
    "p.temperature_K": {"en": "Temperature (K)", "ko": "온도 (K)"},
    "p.temperature_C": {"en": "Temperature (°C)", "ko": "온도 (°C)"},
    "p.pressure_MPa": {"en": "Pressure (MPa)", "ko": "압력 (MPa)"},
    "p.temp_unit": {"en": "Temperature unit", "ko": "온도 단위"},
    "p.literature": {"en": "Literature data", "ko": "문헌값"},
    "p.input_condition": {"en": "Input condition", "ko": "입력 조건"},
    "p.source": {"en": "Source", "ko": "출처"},
    "p.out_of_range": {"en": "This condition lies outside the literature data range; no value could be found.",
                       "ko": "이 조건에서는 문헌 데이터 범위를 벗어나 값을 찾을 수 없어요."},
    "p.mass_fraction": {"en": "NH₃ mass fraction (0–1)", "ko": "NH₃ 질량분율 (0–1)"},
    "p.dew_T": {"en": "Dew-point temperature", "ko": "이슬점 온도"},
    "p.bubble_T": {"en": "Bubble-point temperature", "ko": "거품점 온도"},
    "p.dew_P": {"en": "Dew-point pressure", "ko": "이슬점 압력"},
    "p.bubble_P": {"en": "Bubble-point pressure", "ko": "거품점 압력"},

    # vapour pressure
    "vp.range": {"en": "Valid range {tmin:.0f}–{tmax:.0f} K · {pmin:.3f}–{pmax:.1f} MPa · linear interpolation of literature data",
                 "ko": "유효 범위 {tmin:.0f}–{tmax:.0f} K · {pmin:.3f}–{pmax:.1f} MPa · 문헌값 선형 보간"},
    "vp.psat": {"en": "Saturation pressure", "ko": "포화 증기압"},
    # density
    "den.range": {"en": "Valid range {tmin:.0f}–{tmax:.0f} °C · linear interpolation of literature data",
                  "ko": "유효 범위 {tmin:.0f}–{tmax:.0f} °C · 문헌값 선형 보간"},
    "den.density": {"en": "Density", "ko": "밀도"},
    # heat capacity
    "cp.range": {"en": "Shomate equation (NIST) · 200–1400 K", "ko": "Shomate 방정식 (NIST) · 200–1400 K"},
    "cp.expander": {"en": "Shomate equation · coefficients · source", "ko": "Shomate 방정식 · 계수 · 출처"},
    "cp.eq_title": {"en": "**Shomate equation** ($t = T/1000$)", "ko": "**Shomate 방정식** ($t = T/1000$)"},
    # dew / bubble
    "dew.mixture": {"en": "Mixture", "ko": "혼합물"},
    "dew.pure": {"en": "Pure NH₃", "ko": "순수 NH₃"},
    "dew.pure_note": {"en": "For a pure substance the bubble and dew points coincide (vapour-pressure curve).",
                      "ko": "순수 물질은 거품점과 이슬점이 같습니다 (증기압 곡선)."},
    "dew.h2o_range": {"en": "Valid range 220–560 K · 0–10 MPa · 2-D spline interpolation",
                      "ko": "유효 범위 220–560 K · 0–10 MPa · 2차원 스플라인 보간"},
    "dew.h2o_legend": {"en": "Solid = bubble point · dotted = dew point", "ko": "실선 = 거품점 · 점선 = 이슬점"},
    "dew.bin_source": {"en": "Source: [{title}]({url}) · mole → mass fraction conversion · 1000×1000 grid interpolation",
                       "ko": "출처: [{title}]({url}) · 몰분율 → 질량분율 환산 · 1000×1000 격자 내삽"},
    "dew.bin_range": {"en": "Valid range {tmin:.1f}–{tmax:.1f} K · nearest grid value",
                      "ko": "유효 범위 {tmin:.1f}–{tmax:.1f} K · 격자에서 가장 가까운 값"},
    "dew.bin_legend": {"en": "● dew point · ◆ bubble point (literature measurements)", "ko": "● 이슬점 · ◆ 거품점 (문헌 실측값)"},
    "dew.heat_title": {"en": "**{name} · interpolated phase diagram** (colour = pressure, MPa)",
                       "ko": "**{name} · 내삽 상평형도** (색 = 압력, MPa)"},
    "dew.data_expander": {"en": "Processed literature data", "ko": "가공된 문헌 데이터 보기"},
    "dew.conv_expander": {"en": "Mole → mass fraction conversion", "ko": "몰분율 → 질량분율 환산 과정"},
    "dew.conv_md": {
        "en": "The literature reports NH₃ **mole fractions**; they were converted to **mass fractions** as follows.",
        "ko": "문헌은 NH₃ **몰분율** 기준이므로 아래 식으로 **질량분율**로 환산했습니다."},
    "dew.grid_button": {"en": "Build interpolation-grid CSV (about 45 MB)", "ko": "내삽 격자 CSV 생성 (약 45 MB)"},
    "dew.download": {"en": "⬇ Download CSV", "ko": "⬇ CSV 다운로드"},
    "dew.spinner": {"en": "Building the interpolation grid…", "ko": "내삽 격자 계산 중…"},

    # ------------------------------------------------------------------ LHV calculator
    "lhv.title": {"en": "## NH₃–H₂ Fuel-Blend Heating Value Calculator", "ko": "## NH₃·H₂ 혼소 연료 발열량 계산기"},
    "lhv.caption": {"en": "Choose the fuel state, then enter the hydrogen fraction and temperature to get the heating value and density.",
                    "ko": "연료 상태 선택 후 수소 비율·온도 입력 시 발열량과 밀도가 계산됩니다."},
    "lhv.state": {"en": "Fuel state", "ko": "연료 상태"},
    "lhv.state.gas": {"en": "Vapour (combustion)", "ko": "기체 (연소)"},
    "lhv.state.liq": {"en": "Liquid (storage)", "ko": "액체 (저장)"},
    "lhv.state.help": {"en": "An NH₃–H₂ gas mixture at the burner; liquid ammonia in storage.",
                       "ko": "연소 시엔 NH₃·H₂ 기체 혼합물, 저장 시엔 액체 암모니아입니다."},
    "lhv.basis": {"en": "Hydrogen fraction basis", "ko": "수소 비율 입력 기준"},
    "lhv.basis.mass": {"en": "mass fraction", "ko": "질량분율"},
    "lhv.basis.mole": {"en": "mole fraction", "ko": "몰분율"},
    "lhv.h2_fraction": {"en": "Hydrogen fraction ({basis}, %)", "ko": "수소 비율 ({basis}, %)"},
    "lhv.conv_mass": {"en": "→ mass fraction H₂ {h2:.1f}% / NH₃ {nh3:.1f}%", "ko": "→ 질량분율 H₂ {h2:.1f}% / NH₃ {nh3:.1f}%"},
    "lhv.conv_mole": {"en": "→ mole fraction H₂ {h2:.1f}% / NH₃ {nh3:.1f}%", "ko": "→ 몰분율 H₂ {h2:.1f}% / NH₃ {nh3:.1f}%"},
    "lhv.nh3_fraction": {"en": "Ammonia {basis}: **{pct:.1f}%**   ·   {conv}", "ko": "암모니아 {basis}: **{pct:.1f}%**   ·   {conv}"},
    "lhv.liquid_info": {
        "en": "In the liquid state only **pure ammonia** is present.\n\n"
              "Hydrogen's critical temperature is −240 °C, so it cannot be liquid anywhere in this range (−50 to 130 °C); "
              "**the H₂ fraction is therefore not considered.**",
        "ko": "액체 상태에서는 **순수 암모니아**만 존재합니다.\n\n"
              "수소의 임계온도는 −240 °C로 이 온도 범위(−50 ~ 130 °C)에서 액체로 존재할 수 없어, **H₂ 비율은 고려하지 않습니다.**"},
    "lhv.results": {"en": "### Results", "ko": "### 결과"},
    "lhv.kpi_caption": {"en": "Key figures — LHV per mass · energy per volume", "ko": "대표 지표 — 질량당 LHV · 부피당 에너지"},
    "lhv.std_lhv": {"en": "Standard LHV (per mass)", "ko": "표준 LHV (질량당)"},
    "lhv.std_lhv_help": {"en": "Energy released by burning 1 kg of fuel. Fixed by the composition, independent of temperature.",
                         "ko": "연료 1 kg을 태울 때 나오는 에너지. 조성에 따라 정해지며 온도와는 무관합니다."},
    "lhv.vol_energy": {"en": "Volumetric energy", "ko": "부피당 에너지"},
    "lhv.vol_energy_help": {"en": "Energy per unit volume: standard LHV × density.", "ko": "단위 부피당 에너지. 표준 LHV × 밀도."},
    "lhv.secondary": {"en": "Secondary figures", "ko": "보조 지표"},
    "lhv.density": {"en": "Density", "ko": "밀도"},
    "lhv.eff_lhv": {"en": "Effective LHV", "ko": "유효 LHV"},
    "lhv.eff_lhv_help": {"en": "Standard LHV corrected for the fuel temperature and state (reference: vapour at 25 °C).",
                         "ko": "표준 LHV의 온도·상태 보정값 (25 °C 기체 기준)."},
    "lhv.summary_gas": {"en": "Input summary — vapour · H₂ (mass) {h2:.1f}% / NH₃ {nh3:.1f}% · {T:.1f} °C · (NH₃ saturation pressure ≈ {psat:.2f} bar)",
                        "ko": "입력 요약 — 기체 · H₂(질량) {h2:.1f}% / NH₃ {nh3:.1f}% · {T:.1f} °C · (NH₃ 포화압력 ≈ {psat:.2f} bar)"},
    "lhv.summary_liq": {"en": "Input summary — liquid storage · pure NH₃ · {T:.1f} °C · (saturation pressure ≈ {psat:.2f} bar)",
                        "ko": "입력 요약 — 액체 저장 · 순수 NH₃ · {T:.1f} °C · (포화압력 ≈ {psat:.2f} bar)"},
    "lhv.csv.state": {"en": "Fuel state", "ko": "연료 상태"},
    "lhv.csv.gas": {"en": "vapour (combustion)", "ko": "기체(연소)"},
    "lhv.csv.liq": {"en": "liquid (storage)", "ko": "액체(저장)"},
    "lhv.csv.h2": {"en": "H2 mass fraction (%)", "ko": "수소 질량분율 (%)"},
    "lhv.csv.nh3": {"en": "NH3 mass fraction (%)", "ko": "암모니아 질량분율 (%)"},
    "lhv.csv.T": {"en": "Temperature (C)", "ko": "온도 (C)"},
    "lhv.csv.std": {"en": "Standard LHV (MJ/kg)", "ko": "표준 LHV (MJ/kg)"},
    "lhv.csv.eff": {"en": "Effective LHV (MJ/kg)", "ko": "유효 LHV (MJ/kg)"},
    "lhv.csv.rho": {"en": "Density (kg/m3)", "ko": "밀도 (kg/m3)"},
    "lhv.csv.vol": {"en": "Volumetric energy (MJ/L)", "ko": "부피당 에너지 (MJ/L)"},
    "lhv.csv.psat": {"en": "NH3 saturation pressure (bar)", "ko": "NH3 포화압력 (bar)"},
    "lhv.csv.header": {"en": "item,value", "ko": "항목,값"},
    "lhv.download": {"en": "⬇ Download results (CSV)", "ko": "⬇ 결과 CSV 다운로드"},
    "lhv.method_expander": {"en": "Method · assumptions · data sources", "ko": "계산 방법 · 가정 · 데이터 출처"},
    "lhv.method_md": {
        "en": "**Fuel state**\n"
              "- **Vapour (combustion)**: a gas mixture of NH₃ vapour and H₂ — the blended fuel as it reaches the burner. The density is the ideal-mixture gas density **at the NH₃ saturation pressure of each temperature**; at another operating pressure the gas density scales with pressure.\n"
              "- **Liquid (storage)**: pure liquid ammonia. Hydrogen cannot be liquid in this temperature range (critical temperature −240 °C) and liquid and gas do not mix into one phase, so **the stored state is pure NH₃**.\n\n"
              "**Standard LHV** — mass-weighted average of the component LHVs (H₂ 120, NH₃ 18.6 MJ/kg). Depends on the composition only, not on temperature or state.\n\n"
              "**Effective LHV** — the standard value corrected for the fuel temperature and state (enthalpy), referenced to vapour at 25 °C.\n\n"
              "**Density / volumetric energy** — ideal mixing for the gas (volume additivity); volumetric energy = standard LHV × density.\n\n"
              "**Data source** — NIST Thermophysical Properties of Fluid Systems (NIST Chemistry WebBook); pure components (NH₃, H₂) interpolated linearly in temperature.\n\n"
              "**Validity and caveats** — −50 to 130 °C. Accuracy degrades near the critical point (about 132 °C). The real NH₃–H₂ phase equilibrium (VLE) and pressure dependence are simplified.",
        "ko": "**연료 상태**\n"
              "- **기체(연소)**: NH₃ 증기 + H₂가 섞인 기체 혼합물. 실제 버너로 가는 혼소 연료 상태입니다. 밀도는 각 온도의 **NH₃ 포화압력 기준** 기체 혼합 밀도(이상혼합)이며, 운전 압력이 다르면 기체 밀도는 압력에 비례해 달라집니다.\n"
              "- **액체(저장)**: 순수 액체 암모니아. 수소는 임계온도(−240 °C) 때문에 이 온도 범위에서 액체가 될 수 없고, 액체와 기체는 한 상으로 섞이지 않으므로 **저장 상태는 순수 NH₃**입니다.\n\n"
              "**표준 LHV** — 성분 LHV의 질량가중 평균 (H₂ 120, NH₃ 18.6 MJ/kg). 조성에만 의존하며 온도·상태와 무관합니다.\n\n"
              "**유효 LHV** — 표준값에 연료의 온도·상태(엔탈피)를 보정 (25 °C 기체 기준).\n\n"
              "**밀도 / 부피당 에너지** — 기체는 이상혼합(부피 가산), 부피당 에너지 = 표준 LHV × 밀도.\n\n"
              "**데이터 출처** — NIST Thermophysical Properties of Fluid Systems (NIST Chemistry WebBook). 순물질(NH₃, H₂)을 온도별 선형보간.\n\n"
              "**유효 범위 · 주의** — −50 ~ 130 °C. 임계점(약 132 °C) 근처는 정확도 저하 가능. 실제 NH₃–H₂ 혼합물의 상평형(VLE)·압력 의존성은 단순화되어 있습니다."},
    "lhv.chart_gas": {"en": "📈 Effect of the hydrogen fraction (zoom and hover for values)", "ko": "📈 수소 비율에 따른 변화 (마우스로 확대·값 확인)"},
    "lhv.chart_liq": {"en": "📈 Liquid NH₃ versus temperature (zoom and hover for values)", "ko": "📈 온도에 따른 액체 NH₃ 변화 (마우스로 확대·값 확인)"},
    "lhv.series_std": {"en": "Standard LHV", "ko": "표준 LHV"},
    "lhv.series_vol": {"en": "Volumetric energy", "ko": "부피당 에너지"},
    "lhv.series_rho": {"en": "Density", "ko": "밀도"},
    "lhv.chart_gas_title": {"en": "Vapour · {T:.0f} °C", "ko": "기체 · {T:.0f} °C"},
    "lhv.chart_liq_title": {"en": "Liquid NH₃ (storage)", "ko": "액체 NH₃ (저장)"},
    "lhv.gas_note": {"en": "More H₂ raises the LHV per mass but lowers the energy per volume (lighter fuel) — a trade-off.",
                     "ko": "H₂↑ → 질량당 LHV↑, 하지만 가벼워져 부피당 에너지↓ (트레이드오프)."},
    "lhv.liq_note": {"en": "A warmer storage temperature expands the liquid NH₃, lowering its density and volumetric energy.",
                     "ko": "저장 온도가 오르면 액체 NH₃가 팽창해 밀도·부피에너지가 감소합니다."},

    # ------------------------------------------------------------------ EOS recommendation
    "eos.title": {"en": "#### Data 6: EOS Recommendation for NH₃ Binary Mixtures", "ko": "#### Data 6: NH₃ 이성분 혼합물 EOS 추천"},
    "eos.intro": {
        "en": "For each ammonia binary mixture, candidate equations of state (EOS) are evaluated against **literature VLE "
              "measurements (Aspen TDE)** and the binary interaction parameter (kij) is regressed. From those results this page "
              "recommends **the EOS and kij suited to your condition (T, P)** and **the property method and kij to enter directly "
              "in Aspen Plus / HYSYS**.",
        "ko": "암모니아 이성분 혼합물에 대해, **문헌 VLE 실측 데이터(Aspen TDE)** 를 기준으로 후보 상태방정식(EOS)들을 평가하고 "
              "이성분 상호작용 파라미터(kij)를 회귀한 결과로부터 **입력 조건(T, P)에 적합한 EOS와 kij 값**, 그리고 "
              "**Aspen Plus/HYSYS에 바로 넣을 물성법·kij**를 추천해 드려요."},
    "eos.how_title": {"en": "How the evaluation works", "ko": "평가 방법이 궁금하다면 클릭하세요."},
    "eos.how_md": {
        "en": "The recommendations for each system are generated offline by the following workflow.\n\n"
              "1. **Literature data** — the measured VLE points of the binary (with sources) are extracted from the NIST TDE inside Aspen Plus as a `.bkp` file.\n"
              "2. **Local sampling** — the measurements bracketing the condition of interest (T\\*, P\\*) are selected by rule (|ΔT| ≤ 10 °C, 0.3P\\* ≤ P ≤ 3P\\*, T·P bracketing). When the condition cannot be bracketed, an extrapolation warning is attached to the result.\n"
              "3. **EOS evaluation and regression** — for every candidate EOS (Thermopack plus in-house Aspen variants) ① the default kij is evaluated (base) → ② a single kij per EOS is regressed on the selected sample → ③ the cases are recomputed (fit), and the models are ranked by the liquid-composition error **x-AARD** (bubble-pressure AARD for the fully miscible system). Vapour compositions y are not used in the regression, and a train/validation split guards against over-fitting.\n"
              "4. **Simulator mapping** — every EOS is mapped to its Aspen Plus / HYSYS property-method name (direct / approximate / reference only) and kij is also provided in the Aspen input form (kaij + kbij·T + kcij/T). Models that commercial simulators lack are kept as an \"accuracy ceiling\".\n"
              "5. **Publication** — the ranking, kij, validity range and warnings of each condition band are committed as `eos_recommendations/*.json`, which this page reads.",
        "ko": "각 계의 추천 결과는 아래 워크플로(오프라인)로 생성됩니다.\n\n"
              "1. **문헌 데이터 확보** — Aspen Plus의 NIST TDE에서 해당 이성분계의 문헌 VLE 실측점(출처 포함)을 `.bkp`로 추출합니다.\n"
              "2. **국소 샘플 선택** — 관심 조건 (T\\*, P\\*)를 감싸는 실측점을 규칙(|ΔT| ≤ 10 °C, 0.3P\\* ≤ P ≤ 3P\\*, T·P bracketing)으로 선택합니다. 감싸지 못하면 외삽 경고가 결과에 표시됩니다.\n"
              "3. **EOS 평가·회귀** — Thermopack(및 자체 구현 Aspen 변형)으로 후보 EOS별 ① 기본 kij 계산(base) → ② 선택 샘플만으로 EOS당 단일 kij 회귀 → ③ 재계산(fit)을 수행하고, 액상 조성 오차 **x-AARD**(전조성 혼화계는 기포압 AARD)로 순위를 매깁니다. 기상 y는 회귀에 사용하지 않으며, train/validation 분리로 과적합을 점검합니다.\n"
              "4. **시뮬레이터 매핑** — 각 EOS를 Aspen Plus/HYSYS 물성법 이름에 대응시키고(직접 / 근사 / 참고용), kij를 Aspen 입력 형식(kaij + kbij·T + kcij/T)으로도 제공합니다. 상용 시뮬레이터에 없는 모델은 \"정확도 상한\" 참고용으로 남겨 둡니다.\n"
              "5. **결과 등재** — 조건 밴드별 추천 순위·kij·유효범위·경고를 `eos_recommendations/*.json`으로 커밋하면 이 페이지에 반영됩니다."},
    "eos.select_mixture": {"en": "Select a mixture:", "ko": "원하시는 혼합물을 선택해주세요:"},
    "eos.mix.n2": {"en": "1. $NH_3 + N_2$ — nitrogen", "ko": "1. $NH_3 + N_2$ 혼합물 — 질소"},
    "eos.mix.h2o": {"en": "2. $NH_3 + H_2O$ — water", "ko": "2. $NH_3 + H_2O$ 혼합물 — 물"},
    "eos.mix.h2": {"en": "3. $NH_3 + H_2$ — hydrogen", "ko": "3. $NH_3 + H_2$ 혼합물 — 수소"},
    "eos.mix.ch4": {"en": "4. $NH_3 + CH_4$ — methane", "ko": "4. $NH_3 + CH_4$ 혼합물 — 메탄"},
    "eos.name.n2": {"en": "NH₃ + N₂ (nitrogen)", "ko": "NH₃ + N₂ (질소)"},
    "eos.name.h2o": {"en": "NH₃ + H₂O (water)", "ko": "NH₃ + H₂O (물)"},
    "eos.name.h2": {"en": "NH₃ + H₂ (hydrogen)", "ko": "NH₃ + H₂ (수소)"},
    "eos.name.ch4": {"en": "NH₃ + CH₄ (methane)", "ko": "NH₃ + CH₄ (메탄)"},
    "eos.heading": {"en": "### EOS recommendation for {name}", "ko": "### {name} 혼합물의 EOS 추천"},
    "eos.pending": {"en": "**The {name} system has not been evaluated yet.** Produce the results as below and commit them; this page then shows them automatically.",
                    "ko": "**{name} 계는 아직 평가 전이에요.** 아래 순서로 결과를 만들어 커밋하면 이 페이지에 자동으로 표시됩니다."},
    "eos.pending_md": {
        "en": "1. Register both components in **Aspen Plus**, retrieve the **NIST TDE Binary VLE** data and save it as `.bkp`\n"
              "2. In **Claude cowork**, attach the `.bkp` and the evaluation workbook and run \"analyse according to the EOS agent instructions\" (specify the T, P cases of interest)\n"
              "3. Save the results in the `eos_recommendations/<system>.json` schema and commit them to this repository (schema: see `eos_recommendations/README.md`)",
        "ko": "1. **Aspen Plus**에서 두 물질을 등록하고 **NIST TDE Binary VLE** 데이터를 조회한 뒤 `.bkp`로 저장\n"
              "2. **Claude cowork**에서 `.bkp` + 평가 워크북을 첨부하고 \"EOS agent 지침에 따라 분석\" 실행 (관심 조건 T, P 케이스를 함께 지정)\n"
              "3. 산출된 결과를 `eos_recommendations/<계이름>.json` 스키마로 저장해 이 저장소에 커밋 (스키마: `eos_recommendations/README.md` 참고)"},
    "eos.example": {"en": "⚠️ **Example data.** These are placeholder values that only illustrate the layout, not real evaluation results. Real values appear once the evaluated JSON replaces this file.",
                    "ko": "⚠️ **예시 데이터입니다.** 화면 구성을 보여드리기 위한 자리표시자 값이며 실제 평가 결과가 아니에요. 실제 값은 평가 완료 후 JSON 교체 시 반영됩니다."},
    "eos.meta.datasets": {"en": "{n} literature data sets", "ko": "문헌 데이터셋 {n}개"},
    "eos.meta.points": {"en": "{n} measured points", "ko": "실측점 {n}개"},
    "eos.meta.generated": {"en": "evaluated {d}", "ko": "평가일 {d}"},
    "eos.sources_expander": {"en": "Data sources and evaluation method", "ko": "데이터 출처·평가 방법 상세"},
    "eos.sources": {"en": "**Sources**", "ko": "**출처**"},
    "eos.method": {"en": "**Method**", "ko": "**방법**"},
    "eos.s1": {"en": "### 1. Condition of interest", "ko": "### 1. 관심 조건 입력"},
    "eos.T_input": {"en": "Temperature (K):", "ko": "온도를 입력해주세요 (K):"},
    "eos.P_input": {"en": "Pressure (bar):", "ko": "압력을 입력해주세요 (bar):"},
    "eos.inside": {"en": "✅ Inside the validated range · **{band}**", "ko": "✅ 검증 범위 안 · **{band}** 기준"},
    "eos.outside": {"en": "⚠️ Outside the validated range — showing the nearest band, **{band}**, for reference (extrapolation)",
                    "ko": "⚠️ 검증 범위 밖 — 가장 가까운 **{band}** 결과를 참고로 보여드려요 (외삽 주의)"},
    "eos.band_range": {"en": "Validated range of this band: T {tlo:g}–{thi:g} K · P {plo:g}–{phi:g} bar",
                       "ko": "이 밴드의 검증 범위: T {tlo:g}–{thi:g} K · P {plo:g}–{phi:g} bar"},
    "eos.no_ranking": {"en": "This band has no ranking yet.", "ko": "이 밴드에는 아직 순위 정보가 없어요."},
    "eos.s2": {"en": "### 2. Recommendation", "ko": "### 2. 추천 결과"},
    "eos.rec_model": {"en": "**Recommended model for design-grade calculations: {name}** — {reason} The EOS ranking below is the fallback for cases where an EOS must be used.",
                      "ko": "**정밀 계산 권장 모델: {name}** — {reason} 아래 EOS 순위는 'EOS를 꼭 써야 할 때'의 차선책이에요."},
    "eos.card.bip": {"en": "{bip} (recommended)", "ko": "{bip} (권장값)"},
    "eos.card.bip_help": {"en": "The regressed value when 'regressed used' is O, otherwise the default value.", "ko": "회귀값 사용(O)이면 회귀값, 아니면 기본값이에요."},
    "eos.card.aard": {"en": "Expected {metric}", "ko": "예상 {metric}"},
    "eos.card.aard_help": {"en": "Mean relative deviation from the literature measurements of this band.", "ko": "이 대역 문헌 실측점에 대한 평균 상대오차예요."},
    "eos.card.note": {"en": "Note: {note}", "ko": "비고: {note}"},
    "eos.card.top_direct": {"en": "Recommended EOS (rank 1 · directly usable in Aspen)", "ko": "추천 EOS (1위 · Aspen 직접 사용 가능)"},
    "eos.card.top_overall": {"en": "Recommended EOS (rank 1 · overall)", "ko": "추천 EOS (1위 · 전체)"},
    "eos.card.top_caption": {"en": "↑ The overall rank 1, **{eos}**, maps to commercial simulators only as '{tier}', so treat it as the accuracy ceiling. The best model you can select directly in Aspen Plus / HYSYS is below.",
                             "ko": "↑ 전체 1위 **{eos}** 는 상용 시뮬레이터 대응이 '{tier}'이라 정확도 상한 참고용이에요. Aspen Plus/HYSYS에서 바로 쓸 수 있는 1위는 아래입니다."},
    "eos.card.aspen_pick": {"en": "Best directly usable in Aspen", "ko": "Aspen에서 바로 쓰는 1위"},
    "eos.card.no_direct": {"en": "No EOS with a direct Aspen Plus counterpart is available in this band.", "ko": "이 대역에는 Aspen Plus에 직접 대응되는 EOS 결과가 없어요."},
    "eos.tier.direct": {"en": "direct", "ko": "직접"},
    "eos.tier.cond": {"en": "approximate (re-check)", "ko": "근사·재확인"},
    "eos.tier.none": {"en": "reference only", "ko": "참고용"},
    "eos.default_suffix": {"en": "{v:.4f} (default)", "ko": "{v:.4f} (기본값)"},
    "eos.aspen_card_title": {"en": "Aspen Plus / HYSYS input card — copy and paste", "ko": "Aspen Plus / HYSYS 입력 카드 — 복사해서 붙여넣기"},
    "eos.aspen_card_caption": {"en": "Pure-component constants (Tc, Pc, ω) differ slightly between thermopack and the Aspen databank, so results may differ in the last digits. Flash 2–3 in-band conditions in Aspen and compare the solubility once.",
                               "ko": "물성상수(Tc·Pc·ω)가 thermopack과 Aspen 데이터뱅크 사이에 미세하게 달라 결과가 소수점 수준으로 차이날 수 있어요. Aspen에서 대역 안 조건 2~3점을 플래시해 용해도를 한 번 대조해 보시길 권합니다."},
    "eos.card.l_method": {"en": "Aspen Plus method : {v}", "ko": "Aspen Plus 물성법 : {v}"},
    "eos.card.l_param": {"en": "Parameter form    : Parameters → Binary Interaction → {param}-1   ({a} / {b})", "ko": "파라미터 입력란   : Parameters → Binary Interaction → {param}-1   ({a} / {b})"},
    "eos.card.l_param_nrtl": {"en": "Parameter form    : Parameters → Binary Interaction → NRTL-1   (component i = NH3 (AMMONIA), j = H2O (WATER))",
                              "ko": "파라미터 입력란   : Parameters → Binary Interaction → NRTL-1   (성분 i = NH3(AMMONIA), j = H2O(WATER) 순서)"},
    "eos.card.l_nrtl": {"en": "Band constants    : AIJ = 0, AJI = 0, BIJ = {b12:+.0f}, BJI = {b21:+.0f}, CIJ = {alpha:g}   (τij = BIJ/T, T {tlo:g}–{thi:g} K)   — prefer Aspen's built-in ENRTL-RK parameters when available",
                        "ko": "이 대역 상수      : AIJ = 0, AJI = 0, BIJ = {b12:+.0f}, BJI = {b21:+.0f}, CIJ = {alpha:g}   (τij = BIJ/T, T {tlo:g}–{thi:g} K)   — Aspen 내장 ENRTL-RK 파라미터가 있으면 그쪽이 우선"},
    "eos.card.l_kij": {"en": "Band constant     : kaij = {kij:.4f}   (T {tlo:g}–{thi:g} K, P {plo:g}–{phi:g} bar)   ← safest choice",
                       "ko": "이 대역 상수      : kaij = {kij:.4f}   (T {tlo:g}–{thi:g} K, P {plo:g}–{phi:g} bar)   ← 가장 안전"},
    "eos.card.l_params": {"en": "Band constants    : {vals}   (T {tlo:g}–{thi:g} K, P {plo:g}–{phi:g} bar)", "ko": "이 대역 상수      : {vals}   (T {tlo:g}–{thi:g} K, P {plo:g}–{phi:g} bar)"},
    "eos.card.l_tform": {"en": "All-band T form   : kaij = {ka:.4f}, kbij = {kb:.6f}, kcij = {kc:.2f}   (kij = kaij + kbij·T + kcij/T, valid {lo:g}–{hi:g} K only; reproduces the band values within {dev:.3f})",
                         "ko": "전 대역 온도식    : kaij = {ka:.4f}, kbij = {kb:.6f}, kcij = {kc:.2f}   (kij = kaij + kbij·T + kcij/T, {lo:g}–{hi:g} K 안에서만; 밴드값 재현 오차 ≤ {dev:.3f})"},
    "eos.card.l_hysys_approx": {"en": " (the HYSYS version is a modified model — approximate)", "ko": " (HYSYS판은 자체 수정 모델이라 근사)"},
    "eos.card.l_hysys_kij": {"en": "HYSYS             : {pkg} package → enter kij = {kij:.4f} under Binary Coeffs{approx}", "ko": "HYSYS             : {pkg} 패키지 → Binary Coeffs에 kij = {kij:.4f} 입력{approx}"},
    "eos.card.l_hysys": {"en": "HYSYS             : {pkg}{approx}", "ko": "HYSYS             : {pkg}{approx}"},
    "eos.card.l_hysys_none": {"en": "HYSYS             : no corresponding property package", "ko": "HYSYS             : 해당 물성법 없음"},
    "eos.card.l_accuracy": {"en": "Expected accuracy : {metric} {v:.1f}% (against the literature data of this band)", "ko": "기대 정확도       : {metric} {v:.1f}% (이 대역 문헌 실측 기준)"},
    "eos.s3": {"en": "### 3. Model-by-model comparison", "ko": "### 3. EOS별 상세 비교"},
    "eos.sim_only": {"en": "Show only models selectable in Aspen Plus / HYSYS", "ko": "시뮬레이터(Aspen Plus/HYSYS)에서 고를 수 있는 모델만 보기"},
    "eos.col.rank": {"en": "Rank", "ko": "순위"},
    "eos.col.default": {"en": "Default", "ko": "기본값"},
    "eos.col.regressed": {"en": "Regressed", "ko": "회귀값"},
    "eos.col.used": {"en": "Regressed used", "ko": "회귀값 사용"},
    "eos.col.aard_base": {"en": "{metric} (default, %)", "ko": "{metric} (기본, %)"},
    "eos.col.aard_fit": {"en": "{metric} (regressed, %)", "ko": "{metric} (회귀, %)"},
    "eos.col.improvement": {"en": "Validation improvement (%)", "ko": "검증 개선율 (%)"},
    "eos.col.note": {"en": "Note", "ko": "비고"},
    "eos.table_caption": {"en": "* in the Aspen Plus / HYSYS columns = the name exists but parameter sets or α options differ (approximate, re-check). — = not available in commercial simulators (accuracy-ceiling reference).",
                          "ko": "Aspen Plus/HYSYS 열의 * 표시 = 이름은 있으나 파라미터 세트·α 옵션이 달라 근사·재확인 필요. — = 상용 시뮬레이터에 없음(정확도 상한 참고용)."},
    "eos.chart.bar": {"en": "{metric} with the recommended setting", "ko": "추천 설정의 {metric}"},
    "eos.chart.tick": {"en": "{metric} with the default BIP", "ko": "기본 BIP의 {metric}"},
    "eos.chart.tick_hover": {"en": "%{y} default: %{x:.1f}%<extra></extra>", "ko": "%{y} 기본값: %{x:.1f}%<extra></extra>"},  # Plotly template: no t() kwargs
    "eos.chart.off": {"en": "default {v:.0f}% →", "ko": "기본 {v:.0f}% →"},
    "eos.chart.xaxis": {"en": "{metric} (%) — lower is better", "ko": "{metric} (%) — 낮을수록 좋음"},
    "eos.s4": {"en": "### 4. Notes and warnings", "ko": "### 4. 주의사항"},
    "eos.cases_expander": {"en": "Evaluation cases and extrapolation details", "ko": "평가 케이스·외삽 상세 보기"},
    "eos.cases_title": {"en": "**Case status**", "ko": "**평가 케이스 상태**"},
    "eos.kijT_expander": {"en": "kij temperature form (Aspen PRKBV form) — all EOS", "ko": "kij 온도식 (Aspen PRKBV 형식) — 전 EOS"},
    "eos.kijT_md": {"en": "kij = kaij + kbij·T + kcij/T (T in K). An interpolation through the recommended band values — use it only inside the stated temperature range.",
                    "ko": "kij = kaij + kbij·T + kcij/T (T in K). 밴드별 권장 kij를 잇는 보간식이며, 표시된 온도 범위 안에서만 쓰세요."},
    "eos.kijT.range": {"en": "T range (K)", "ko": "T 범위 (K)"},
    "eos.kijT.bands": {"en": "Bands", "ko": "밴드 수"},
    "eos.kijT.dev": {"en": "Max. deviation from band values", "ko": "밴드값 재현 오차"},
    "eos.kijT.values": {"en": "Band values", "ko": "밴드값"},
    "eos.excluded_expander": {"en": "EOS excluded for this system", "ko": "이 계에서 제외된 EOS 확인하기"},
    "eos.method_caption": {"en": "Evaluation method: {m}", "ko": "평가 방법: {m}"},
    # Aspen map display strings (names that contain prose)
    "eos.map.rksbm": {"en": "RKS-BM (= VLE of the SRK method)", "ko": "RKS-BM (= SRK 물성법의 VLE)"},
    "eos.map.nrtl": {"en": "NRTL-RK (activity-coefficient model)", "ko": "NRTL-RK (활성계수 모델)"},
    "eos.map.nrtl_hysys": {"en": "NRTL (different τ form)*", "ko": "NRTL (τ 형식 다름)*"},
    "eos.map.tcpr": {"en": "PENG-ROB + Twu α / volume-translation options*", "ko": "PENG-ROB + Twu α·부피보정 옵션*"},
    "eos.map.cpa": {"en": "CPA (check V12+)*", "ko": "CPA (V12+ 확인)*"},
    "eos.map.hv": {"en": "— (see the PRWS / PRMHV2 family)", "ko": "— (PRWS·PRMHV2 계열 참고)"},
}
