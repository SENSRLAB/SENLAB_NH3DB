"""Smoke tests for the SENLAB_NH3DB app + EOS recommendation page v4 (Streamlit AppTest)."""
from streamlit.testing.v1 import AppTest

PASS = []

def check(name, cond, detail=""):
    PASS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

# 1. Default run (pills default = 증기압)
at = AppTest.from_file("app.py", default_timeout=120)
at.run()
check("default page runs w/o exception", not at.exception, str([e.value for e in at.exception]))

# 2. EOS Recommendation page (NH3+N2 default)
at.session_state["prop"] = "EOS 추천 (이성분계)"
at.run()
check("EOS page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
metrics = [m.label for m in at.metric]
check("top-pick metrics rendered", any("추천 EOS" in m for m in metrics), str(metrics))
check("Aspen input card rendered", any("Aspen Plus 물성법" in c.value for c in at.code), str([c.value[:40] for c in at.code]))

# 3. In-band condition -> success badge (N2 저온 대역: 265-290 K, 10-50 bar) -> PR-BM is the top pick
at.number_input[0].set_value(275.0)
at.number_input[1].set_value(30.0)
at.run()
succ = " | ".join(s.value for s in at.success)
check("in-band success badge", "검증 범위 안" in succ, succ[:200])
check("PR-BM top pick at 275 K", any(m.value == "PR-BM" for m in at.metric), str([m.value for m in at.metric]))

# 4. Out-of-band condition -> extrapolation warning
at.number_input[0].set_value(400.0)
at.number_input[1].set_value(300.0)
at.run()
warnings = " | ".join(w.value for w in at.warning)
check("out-of-band warning", "범위 밖" in warnings, warnings[:300])

# 5. 극저온 band: overall top SAFT-VR Mie, Aspen pick shown separately
at.number_input[0].set_value(250.0)
at.number_input[1].set_value(30.0)
at.run()
vals = [m.value for m in at.metric]
check("극저온 overall top SAFT-VR Mie", "SAFT-VR Mie" in vals, str(vals))
check("극저온 Aspen pick present", "PR-BM" in vals or "PR" in vals or "SRK" in vals, str(vals))

# 6. Simulator-only toggle filters the table (toggle is the first toggle widget on the page)
at.toggle[0].set_value(True)
at.run()
check("toggle run w/o exception", not at.exception, str([e.value for e in at.exception]))
at.toggle[0].set_value(False)
at.run()

# 7. All four mixtures render; H2O shows recommended-model info + composition note
for mix in ("2. $NH_3 + H_2O$ 혼합물 — 물", "3. $NH_3 + H_2$ 혼합물 — 수소", "4. $NH_3 + CH_4$ 혼합물 — 메탄"):
    at.radio[0].set_value(mix)
    at.run()
    check(f"mixture renders: {mix[3:12]}", not at.exception, str([e.value for e in at.exception]))
    if "H_2O" in mix:
        infos = " | ".join(i.value for i in at.info)
        check("H2O recommended model banner", "정밀 계산 권장" in infos, infos[:200])
        check("H2O composition note", "NH₃ ≥ 50%" in infos, infos[:300])

# 8. Dew/bubble page still works (N2 molar-mass fix retained)
at2 = AppTest.from_file("app.py", default_timeout=120)
at2.run()
at2.session_state["prop"] = "이슬점 · 거품점"
at2.run()
check("Dew/bubble page runs w/o exception", not at2.exception, str([e.value for e in at2.exception]))
src = open("app.py", encoding="utf-8").read()
check("N2 molar mass 28.014 present in app.py", "28.014" in src)

print()
failed = [n for n, ok, _ in PASS if not ok]
print(f"{len(PASS) - len(failed)}/{len(PASS)} checks passed" + (f"; FAILED: {failed}" if failed else ""))
raise SystemExit(1 if failed else 0)
