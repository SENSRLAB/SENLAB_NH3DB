"""Smoke tests for the SENLAB_NH3DB app (bilingual UI, v7) + EOS recommendation page (Streamlit AppTest).

Navigation is exercised the way a user does it (service-card buttons on the Home page, the EN/한국어 control in
the header) so that the test also covers the stale-label handling of the language switch.
"""
from streamlit.testing.v1 import AppTest

PASS = []


def check(name, cond, detail=""):
    PASS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


def has_hangul(s):
    return any("가" <= ch <= "힣" for ch in s)


def all_text(at):
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info]
    parts += [w.value for w in at.warning] + [s.value for s in at.success] + [m.label for m in at.metric]
    return " | ".join(str(p) for p in parts)


def headings(at):
    return [m.value for m in at.markdown if m.value.startswith("###")]


def lang_control(at):
    return [b for b in at.get("button_group") if b.key == "lang_sel"][0]


def goto(at, page):
    """Open a page from the Home page's service card (works in either language)."""
    at.button(key=f"home_{page}").click().run()
    return at


# 1. Default run (Home landing page, English)
at = AppTest.from_file("app.py", default_timeout=120)
at.run()
check("home page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
check("home page shows the Online Services block", any("Online Services" in m.value for m in at.markdown))
check("English home has no Hangul", not has_hangul(all_text(at)))
check("language control present, English selected", lang_control(at).value == "en")

# 2. EOS Recommendation page (NH3+N2 default) opened from the service card
goto(at, "eos")
check("EOS page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
check("EOS page opened", at.session_state["prop"] == "eos" and any("EOS recommendation for" in h for h in headings(at)), str(headings(at)[:3]))
metrics = [m.label for m in at.metric]
check("top-pick metrics rendered", any("Recommended EOS" in m for m in metrics), str(metrics))
check("Aspen input card rendered", any("Aspen Plus method" in c.value for c in at.code), str([c.value[:40] for c in at.code]))

# 3. In-band condition -> success badge (N2 low-T band: 265-290 K, 10-50 bar) -> an Aspen variant is the pick
at.number_input[0].set_value(275.0)
at.number_input[1].set_value(30.0)
at.run()
succ = " | ".join(s.value for s in at.success)
check("in-band success badge", "Inside the validated range" in succ, succ[:200])
vals275 = [m.value for m in at.metric]
check("Aspen-variant model is top pick at 275 K", any(v in ("SR-POLAR", "PR-BM", "RKS-BM", "RK-ASPEN") for v in vals275), str(vals275))

# 4. Out-of-band condition -> extrapolation warning
at.number_input[0].set_value(400.0)
at.number_input[1].set_value(300.0)
at.run()
warnings = " | ".join(w.value for w in at.warning)
check("out-of-band warning", "Outside the validated range" in warnings, warnings[:300])

# 5. Cryogenic band: overall top SAFT-VR Mie, Aspen pick shown separately
at.number_input[0].set_value(250.0)
at.number_input[1].set_value(30.0)
at.run()
vals = [m.value for m in at.metric]
check("cryogenic overall top SAFT-VR Mie", "SAFT-VR Mie" in vals, str(vals))
check("cryogenic Aspen pick present", any(v in ("PR-BM", "PR", "SRK", "RKS-BM", "RK-ASPEN", "SR-POLAR") for v in vals), str(vals))

# 6. Simulator-only toggle filters the table
at.toggle[0].set_value(True)
at.run()
check("toggle run w/o exception", not at.exception, str([e.value for e in at.exception]))
at.toggle[0].set_value(False)
at.run()

# 7. All four mixtures render; H2O shows recommended-model info + composition note
for mix in ("h2o", "h2", "ch4"):
    at.radio(key="eos_mix__en").set_value(mix)
    at.run()
    check(f"mixture renders: {mix}", not at.exception, str([e.value for e in at.exception]))
    if mix == "h2o":
        infos = " | ".join(i.value for i in at.info)
        check("H2O recommended model banner", "Recommended model for design-grade" in infos, infos[:200])
        check("H2O composition note", "NH₃-rich" in infos, infos[:300])
        check("no Korean text on the English H2O page", not has_hangul(infos + all_text(at)))

# 8. Language switch on the EOS page (H2O selected, custom condition) via the header control
at.radio(key="eos_mix__en").set_value("h2o").run()   # the T/P inputs are keyed per system → select first, then set
at.number_input[0].set_value(300.0).run()
check("custom condition set before the switch", at.number_input[0].value == 300.0, str([n.value for n in at.number_input]))
lang_control(at).set_value("ko").run()
check("switch to Korean runs w/o exception", not at.exception, str([e.value for e in at.exception]))
check("language state + URL updated", at.session_state["lang"] == "ko" and at.query_params.get("lang") == "ko")
check("page, mixture and inputs survive the switch",
      at.session_state["prop"] == "eos" and at.radio(key="eos_mix__ko").value == "h2o" and at.number_input[0].value == 300.0)
ko_text = all_text(at)
check("Korean EOS page shows Korean headings", "추천 결과" in ko_text and "관심 조건" in ko_text, ko_text[:200])
infos_ko = " | ".join(i.value for i in at.info)
check("Korean recommended-model banner", "정밀 계산 권장 모델" in infos_ko and has_hangul(infos_ko), infos_ko[:200])
check("Korean band label in badge", any(has_hangul(s.value) for s in at.success) or any(has_hangul(w.value) for w in at.warning))
code_ko = " | ".join(c.value for c in at.code)
check("Korean Aspen card", "Aspen Plus 물성법" in code_ko, code_ko[:120])
table_cols = list(at.dataframe[0].value.columns)
check("Korean table columns", "순위" in table_cols and "비고" in table_cols, str(table_cols))
# switch back to English: everything English again, state kept
lang_control(at).set_value("en").run()
check("switch back to English runs w/o exception", not at.exception, str([e.value for e in at.exception]))
check("English again, state kept", at.session_state["lang"] == "en" and at.session_state["prop"] == "eos"
      and at.radio(key="eos_mix__en").value == "h2o" and not has_hangul(all_text(at)))

# 9. Korean session from the start (?lang=ko): home → dew/bubble → LHV through the service cards
at2 = AppTest.from_file("app.py", default_timeout=120)
at2.query_params["lang"] = "ko"
at2.run()
check("?lang=ko opens Korean home", not at2.exception and any("온라인 서비스" in m.value for m in at2.markdown))
check("Korean home has Korean contributor names", any("고우진" in m.value for m in at2.sidebar.markdown))
goto(at2, "dew")
check("Korean dew/bubble page runs w/o exception", not at2.exception, str([e.value for e in at2.exception]))
check("Korean dew/bubble page opened", at2.session_state["prop"] == "dew" and "#### 이슬점 · 거품점" in headings(at2), str(headings(at2)[:2]))
check("Korean dew/bubble page shows 조건 입력", any("조건 입력" in m.value for m in at2.markdown))
at2.get("button_group")  # the mixture control exists
mix_ctl = [b for b in at2.get("button_group") if b.key == "db_sub"][0]
mix_ctl.set_value("NH₃ + N₂").run()
check("Korean N2 dew/bubble page", not at2.exception and any("내삽 상평형도" in m.value for m in at2.markdown), str([e.value for e in at2.exception]))
# home → LHV
at2.session_state["prop"] = "home"  # the pills' own callback path is covered above; here we only need the card
at2.run()
goto(at2, "lhv")
check("Korean LHV page runs w/o exception", not at2.exception, str([e.value for e in at2.exception]))
check("Korean LHV title", at2.session_state["prop"] == "lhv" and any(m.value.startswith("## NH₃·H₂ 혼소 연료 발열량") for m in at2.markdown))
at2.radio(key="lhv_mode__ko").set_value("liq").run()
check("Korean LHV liquid mode", not at2.exception and any("순수 암모니아" in i.value for i in at2.info))

# 10. English dew/bubble + LHV pages (N2 molar-mass fix retained)
at3 = AppTest.from_file("app.py", default_timeout=120)
at3.run()
goto(at3, "dew")
check("Dew/bubble page runs w/o exception", not at3.exception, str([e.value for e in at3.exception]))
check("English dew/bubble page opened", "#### Dew & Bubble Point" in headings(at3))
src = open("app.py", encoding="utf-8").read()
check("N2 molar mass 28.014 present in app.py", "28.014" in src)
at3.session_state["prop"] = "home"
at3.run()
goto(at3, "lhv")
check("LHV page runs w/o exception", not at3.exception, str([e.value for e in at3.exception]))
check("English LHV opened, no Hangul", at3.session_state["prop"] == "lhv" and not has_hangul(all_text(at3)))

# 11. Every i18n key has both languages
from i18n import STRINGS
missing = [k for k, v in STRINGS.items() if not v.get("en") or not v.get("ko")]
check("all i18n strings have en + ko", not missing, str(missing))

print()
failed = [n for n, ok, _ in PASS if not ok]
print(f"{len(PASS) - len(failed)}/{len(PASS)} checks passed" + (f"; FAILED: {failed}" if failed else ""))
raise SystemExit(1 if failed else 0)
