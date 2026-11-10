"""Smoke tests for the SENLAB_NH3DB app (English UI, v6) + EOS recommendation page (Streamlit AppTest)."""
from streamlit.testing.v1 import AppTest

PASS = []

def check(name, cond, detail=""):
    PASS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

# 1. Default run (Home landing page)
at = AppTest.from_file("app.py", default_timeout=120)
at.run()
check("home page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
check("home page shows the Online Services block", any("Online Services" in m.value for m in at.markdown))

# 2. EOS Recommendation page (NH3+N2 default)
at.session_state["prop"] = "EOS Recommendation"
at.run()
check("EOS page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
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
for mix in ("2. $NH_3 + H_2O$ — water", "3. $NH_3 + H_2$ — hydrogen", "4. $NH_3 + CH_4$ — methane"):
    at.radio[0].set_value(mix)
    at.run()
    check(f"mixture renders: {mix[3:12]}", not at.exception, str([e.value for e in at.exception]))
    if "H_2O" in mix:
        infos = " | ".join(i.value for i in at.info)
        check("H2O recommended model banner", "Recommended model for design-grade" in infos, infos[:200])
        check("H2O composition note", "NH₃-rich" in infos, infos[:300])
        check("no Korean text left on the H2O page", not any(("가" <= ch <= "힣") for ch in infos))

# 8. Dew/bubble page still works (N2 molar-mass fix retained)
at2 = AppTest.from_file("app.py", default_timeout=120)
at2.run()
at2.session_state["prop"] = "Dew & Bubble Point"
at2.run()
check("Dew/bubble page runs w/o exception", not at2.exception, str([e.value for e in at2.exception]))
src = open("app.py", encoding="utf-8").read()
check("N2 molar mass 28.014 present in app.py", "28.014" in src)

# 9. LHV page runs
at3 = AppTest.from_file("app.py", default_timeout=120)
at3.run()
at3.session_state["prop"] = "NH₃–H₂ Blend LHV"
at3.run()
check("LHV page runs w/o exception", not at3.exception, str([e.value for e in at3.exception]))

print()
failed = [n for n, ok, _ in PASS if not ok]
print(f"{len(PASS) - len(failed)}/{len(PASS)} checks passed" + (f"; FAILED: {failed}" if failed else ""))
raise SystemExit(1 if failed else 0)
