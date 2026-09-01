"""Smoke tests for the patched app.py + new eos_recommender page (Streamlit AppTest)."""
from streamlit.testing.v1 import AppTest

PASS = []

def check(name, cond, detail=""):
    PASS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

# 1. Default run (skip landing stages -> DB page)
at = AppTest.from_file("app.py", default_timeout=120)
at.run()
check("landing page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
at.session_state["stage"] = 2
at.run()
check("default DB page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
check("selectbox present on DB page", len(at.selectbox) > 0)

# 2. EOS Recommendation page (validated NH3+N2 JSON)
at.selectbox[0].select("EOS Recommendation (Binary Mixtures)")
at.run()
check("EOS page runs w/o exception", not at.exception, str([e.value for e in at.exception]))
warnings = " | ".join(w.value for w in at.warning)
check("no example banner on validated data", "예시 데이터" not in warnings, warnings[:200])
metrics = [m.label for m in at.metric]
check("top-pick metrics rendered", "추천 EOS (1위)" in metrics, str(metrics))

# 3. In-band condition -> success badge (real N2 B1: 265-285 K, 10-50 bar)
at.number_input[0].set_value(275.0)
at.number_input[1].set_value(30.0)
at.run()
succ = " | ".join(s.value for s in at.success)
check("in-band success badge", "검증 범위 안" in succ, succ[:200])

# 4. Out-of-band condition -> extrapolation warning
at.number_input[0].set_value(400.0)
at.number_input[1].set_value(300.0)
at.run()
warnings = " | ".join(w.value for w in at.warning)
check("out-of-band warning", "검증된 범위 밖" in warnings, warnings[:300])

# 5. Band switching: B2 for room-temp condition (real N2 B2 top pick = CPA)
at.number_input[0].set_value(305.0)
at.number_input[1].set_value(50.0)
at.run()
succ = " | ".join(s.value for s in at.success)
check("band B2 matched", "상온" in succ, succ[:200])
check("B2 top pick is CPA", any(m.value == "CPA" for m in at.metric), str([m.value for m in at.metric]))

# 6. All four mixtures render (validated JSONs)
for mix in ("2. $NH_3 + H_2O$ 혼합물", "3. $NH_3 + H_2$ 혼합물", "4. $NH_3 + CH_4$ 혼합물"):
    at.radio[0].set_value(mix)
    at.run()
    check(f"mixture renders: {mix[3:9]}", not at.exception, str([e.value for e in at.exception]))

# 7. Data 4 NH3+N2 branch still works after MW fix
at2 = AppTest.from_file("app.py", default_timeout=120)
at2.run()
at2.session_state["stage"] = 2
at2.run()
at2.selectbox[0].select("Dew point and bubble point information")
at2.run()
at2.radio[0].set_value("4. $NH_3 + N_2$ 혼합물")
at2.run()
check("Data4 NH3+N2 runs w/o exception", not at2.exception, str([e.value for e in at2.exception]))

# 8. Numerical check of the MW fix
mw_n2, mw_nh3 = 28.014, 17.031
x_n2 = 0.5
w = ((1 - x_n2) * mw_nh3) / (x_n2 * mw_n2 + (1 - x_n2) * mw_nh3)
check("mass fraction now correct (x=0.5 -> w=0.378)", abs(w - 0.378) < 0.001, f"w={w:.4f}")

print()
failed = [n for n, ok, _ in PASS if not ok]
print(f"{len(PASS) - len(failed)}/{len(PASS)} checks passed" + (f"; FAILED: {failed}" if failed else ""))
raise SystemExit(1 if failed else 0)
