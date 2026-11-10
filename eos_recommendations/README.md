# eos_recommendations — EOS 추천 결과 저장소

앱의 **"EOS Recommendation (Binary Mixtures)"** 페이지(`eos_recommender.py`)가 읽는 계별 결과 JSON을 보관하는 폴더입니다. 파일 하나 = 이성분계 하나.

| 파일명 | 계 |
|---|---|
| `nh3_n2.json` | NH₃ + N₂ |
| `nh3_h2o.json` | NH₃ + H₂O |
| `nh3_h2.json` | NH₃ + H₂ |
| `nh3_ch4.json` | NH₃ + CH₄ |

파일이 없거나 `"status": "pending"`이면 앱에 "평가 전" 안내가 표시되고, `"status": "example"`이면 예시 데이터 경고 배너와 함께 표시되며, `"status": "validated"`가 실제 결과입니다.

## 결과 생성 방법 (요약)

1. **Aspen Plus**에서 두 물질 등록 → **NIST TDE Binary VLE** 조회 → `.bkp` 저장 (예: `NH3_N2.bkp`)
2. **Claude cowork**에 `.bkp` + EOS 평가 워크북(`Binary EOS Evaluation <계>.xlsx`)을 주고 "EOS agent 지침에 따라 분석" 실행 — 관심 조건 (T, P) 케이스를 함께 지정
   - 내부 동작: 케이스 주변 실측 9점 선택(bracketing, 부족 시 웹 보강/외삽 경고) → Thermopack으로 EOS별 base 계산 → 선택 샘플 통합 단일 kij 회귀 → fit 재계산 → x-AARD 순위
   - Thermopack 물질 ID 주의: 메탄은 `CH4`가 아니라 `C1`. CPA는 기본 생성자(`cpa("NH3,N2")`)로만 호출
3. 결과를 아래 스키마의 JSON으로 저장해 이 폴더에 커밋 → Streamlit Cloud가 자동 재배포

## JSON 스키마 (schema_version 1.0)

```jsonc
{
  "schema_version": "1.0",
  "system": "NH3-N2",                  // 내부 식별자
  "display_name": "NH₃ + N₂",
  "solvent": "NH3",                    // 액상 주성분
  "solute": "N2",                      // 희박 용질 (x_solute 평가 대상)
  "status": "validated",               // "validated" | "example" | "pending"
  "generated": "2026-09-01",           // 평가일
  "method": "EOS/BIP agent v1.1 — local 9-point kij regression (Thermopack)",
  "source": {
    "bkp_file": "NH3_N2.bkp",
    "n_datasets": 12,                  // TDE 문헌 데이터셋 수
    "n_points": 150,                   // 실측점 수
    "provenance": "Aspen Plus TDE (NIST) literature binary VLE"
  },
  "excluded_eos": [                    // 이 계에서 평가 불가한 EOS와 사유
    {"eos": "GERG-2008", "reason": "NH3 is not a GERG-2008 component"}
  ],
  "condition_bands": [                 // 조건 밴드별 결과 (kij 온도의존성 때문에 분리)
    {
      "band_id": "B1",
      "label": "저온 대역",
      "T_K": [223.15, 273.15],         // 검증 범위 (선택 샘플이 커버한 범위)
      "P_bar": [5.0, 40.0],
      "cases": [                       // 평가에 사용한 목표 케이스들
        {"T_K": 253.15, "P_bar": 20.0, "interp_status": "INTERP"}
        // interp_status: "INTERP" | "EXTRAPOLATION: ..." | "WEB_AUGMENTED"
      ],
      "warnings": [],                  // 자유 텍스트 경고
      "ranking": [
        {
          "rank": 1,
          "eos": "tcPR",
          "bip_name": "kij",           // SAFT 계열은 "eps_kij" 등
          "bip_default": -0.036,
          "bip_fitted": -0.0228,
          "use_fitted": true,          // 회귀값 사용 권장 여부 (개선 확인 시 true)
          "x_aard_base": 0.0547,       // 분율 단위 (0.0547 = 5.47 %)
          "x_aard_fit": 0.0674,
          "validation_improvement_pct": 33.6,
          "note": ""
        }
      ]
    }
  ]
}
```

규약: x-AARD는 분율로 저장(표시할 때 %). 밴드는 서로 겹치지 않게. 회귀가 없는 EOS(예: 노출 파라미터 없음)는 `bip_fitted: null, use_fitted: false`로 base만 기재. 실측 자체 데이터를 회귀에 추가한 경우 `source.provenance`에 `+ SENLAB experimental (LAB###)`처럼 명시.

## v1.1 추가 필드 (2026-11, Aspen 호환 층)

- 순위 행: `bip_display`(2-파라미터 모델의 표시용 문자열, 예 HV-NRTL), `engine`(평가 엔진: thermopack / custom PR-BM 등). `x_aard_base: null`은 기본값 평가 생략.
- 시스템 레벨: `aspen_kij_T` — EOS별 `{kaij, kbij, kcij, T_range_K, n_bands, max_abs_dev, band_values}`; kij = kaij + kbij·T + kcij/T (Aspen PRKBV/RKSKBV 형식). 밴드별 권장 kij를 잇는 보간식이며 T_range_K 밖에서는 사용 금지.
- NH3+H2O: `recommended_model`(정밀 계산 권장 모델 — e-NRTL/Data 4), `composition_note`(조성별 정확도 안내).
- 시뮬레이터 매핑(EOS → Aspen Plus/HYSYS 물성법, 직접/근사/참고용)은 JSON이 아니라 `eos_recommender.py`의 `ASPEN_MAP`에 있음. 새 EOS를 추가하면 거기에 한 줄 추가.
- 추가된 행: NH3+N2 `PR-BM`(자체 구현 PR + Boston-Mathias α; kij 부호가 PR과 반대), NH3+H2O `PR (HV-NRTL)`(Huron-Vidal 혼합규칙 2-파라미터; Aspen 직접 대응 없음, 상한 참고용).

## v5 (2026-11-04 재평가) 추가 사항

- 데이터: Aspen Plus V14 TDE 재추출 .bkp 4개로 전 모델 재평가. 정제 규칙은 각 JSON의 `source.provenance`·`method`에 기재(293 K 희박 TXY 세트의 압력 재구성, H2 BVLE016 제외, N2 Cannon 라벨 보정·LAB 증강, H2O pure-NH3 Psat 상한 필터).
- 자체 구현 Aspen 변형(`engine: custom …`): `PR-BM`, `RKS-BM`(= Aspen SRK 물성법의 VLE), `RK-ASPEN`(2-파라미터 `bip_params: {kaij, kbij}`), `SR-POLAR`(`{kij, lij}`). 2-파라미터 행은 `bip_fitted: null` + `bip_display` + `bip_params`.
- 케이스에 `x_ref`(기준 용해도)와 밴드에 `n_samples` 추가. H2O 밴드에는 `full_set_check`(상위 3개 모델을 대역 전체 실측점으로 재검산한 조성별 AARD) 추가.
- 재현 코드: `eos2/` 파이프라인(bkp_parse → qc_data → refs/bands_h2o → eval_tp/eval_custom/eval_h2o → build_v5) — 저장소 외부(Claude 작업공간)에서 실행. 요청 시 제공.

## v5.1 (2026-11-04) — 1-파라미터 회귀 안정화

- 원인: 1-파라미터 kij 회귀(bounded Brent)가 비매끄러운 목적함수(플래시 실패 → 페널티)에서 국소 최소에 갇히는 경우가 있었음. 대표 사례 NH3+H2 335 K 대역의 PR(kij 0.052, x-AARD 69%) — 실제 최적은 kij ≈ 0.34(약 4%).
- 조치: `scoring.evaluate`에 탐색 구간 전체 격자 스캔(25점 + 기본값) 후 최적 격자점 주변만 국소 최소화. thermopack 1-파라미터 8종과 자체 구현 PR-BM·RKS-BM의 전 대역(N2·H2·CH4)을 재회귀. 2-파라미터(RK-ASPEN·SR-POLAR)·CPA·H2O 행은 그대로.
- 결과: 갱신된 `nh3_n2.json`·`nh3_h2.json`·`nh3_ch4.json`(3개). `nh3_h2o.json`은 변경 없음.

## v5.2 (2026-11-05) — NH3+CH4 데이터 QC 추가

- Lentz & Weber 1994의 298.2 K / 82 bar 점(x_CH4 = 0.084)을 제외: x/P가 이웃 점의 3배이고 Krichevskii & Efremova 1953은 99 bar에서 0.038. 이 점이 305 K 대역의 회귀(SSE 지배)와 기준값(국소 보간)을 함께 왜곡하고 있었음.
- 305 K 대역만 재평가: 기준값 30 bar 0.01096 → 0.01002, 50 bar 0.02277 → 0.02190. 같은 kij의 PR이 1.1% → 5.5%로 바뀌는 만큼 이 대역의 점수 불확도는 ±5% 수준으로 보아야 함. Aspen 1위 PR-BM 2.4%(kij 0.094), 전체 1위 SAFT-VRQ Mie 0.2%.
- Lentz 세트 나머지(273 K: 75 bar 0.034 > 100 bar 0.029 비단조, 유효숫자 2자리)는 273 K 유일 출처라 유지 — 275 K 대역 12% 바닥의 원인. 독립적인 270–280 K·50–200 bar 데이터(문헌 또는 연구실 측정)가 해법.
- 갱신 파일: `nh3_ch4.json`만. v5.1 패키지 미반영 시 v5.2 패키지(질소·수소·메탄 3개)로 한 번에 반영.

## v5.3 (2026-11-06) — NH3+H2O에 활성계수 모델 행(NRTL-RK) 추가

- 질문 "e-NRTL을 순위에 넣을 수 없나"에 대한 답: Aspen의 e-NRTL(ENRTL-RK) 자체는 전해질 모델 + 비공개 데이터뱅크 파라미터라 재현 불가. 대신 그 뼈대인 **NRTL 활성계수 모델 + SRK 기상(γ-φ) = Aspen NRTL-RK 물성법**을 `nrtl_rk.py`로 구현해 5개 대역에서 τij = bij/T 2-파라미터(α 0.2/0.3 선택)로 회귀.
- 결과(전체 실측점 재검산): 243 K 4.2% · 273 K 5.9% · 307 K 7.5% · 339 K 6.0% · 381 K 7.3% — 저온 두 대역은 1위, 나머지는 EOS 상위와 동급. 물 부화 희박 영역(x<0.1)도 EOS 상위와 비슷(4–9%). 즉 물 혼합물의 5–9% 바닥은 모델 종류가 아니라 문헌 간 산포(9–15개 출처 혼합)에서 온다.
- 순위 행 필드: `bip_params: {b12_K, b21_K, alpha}`, `bip_display`, `engine: custom gamma-phi (NRTL + SRK)`. Aspen 입력: NRTL-1 (i = AMMONIA, j = WATER) AIJ = AJI = 0, BIJ = b12, BJI = b21, CIJ = α. `eos_recommender.py`의 ASPEN_MAP에 NRTL-RK 추가(입력 카드 NRTL 형식).
- 순성분 증기압: NH3 thermopack CPA 표(0.1 %), H2O IAPWS Wagner-Pruss(228–273 K는 외삽). teqp 0.23.2의 Tillner-Roth NH3–H2O 모델은 물 부화 저밀도 상태에서 비물리적 압력을 내 기준식 활용은 보류.
- 갱신 파일: `nh3_h2o.json`, `eos_recommender.py`. (v5.2 미반영이면 이 패키지의 JSON 4개 + py 1개를 한 번에 업로드.)

## v5.4 (2026-11-09) — 이슬선(y-only) 독립 검증 필드

- TDE에 있었지만 x 회귀에 쓰지 않은 기상 조성 세트(N2: Reamer & Sage 1959 이슬선 5개 등온선 + Glowka 1992 등조성 이슬점; CH4: Glowka 1992)로 각 대역의 Aspen 1위 모델이 내는 기상 NH3 분율을 검증. 밴드에 `dew_line_check` {n_points, sources, P_bar, model, y_aard_pct, y_aad, y_aard_pct_kij0_PR} 추가, warnings에 한 줄 요약.
- 결과: N2 275 K SR-POLAR 4.6%(kij=0이면 23.5%), 305 K PR 4.0%(14.1%), 340 K RK-ASPEN 2.4%(10.9%) — 회귀 kij가 x뿐 아니라 y도 맞춘다는 독립 확인. CH4는 2–6%이나 kij=0과 차이가 없어 y로는 kij를 판별하지 못함(저압에서 y는 NH3 증기압이 지배). 밴드 온도 범위 밖(N2 378·394 K)은 외삽이라 제외(7–21%).
- 재현: `eos2/ycheck.py <out_json_dir>` → ycheck_<sys>.csv, ycheck_summary.json.

## v6 (2026-11-10) — English interface

- All UI text (app.py, lhv_calculator.py, eos_recommender.py) and every string in the four recommendation JSONs are now in English; the Korean originals are kept in the maintainer's workspace (`eos2/json_ko_backup/`). Regeneration: `eos2/translate_json.py <dir>` applies the template-based translation to freshly built JSONs and reports any Korean text left.
- New landing page (Home): about, online-service cards, database contents, updates. Navigation pills: Home · Vapor Pressure · Density · Heat Capacity · Dew & Bubble Point · NH₃–H₂ Blend LHV · EOS Recommendation.
- Marker strings used by the renderer: "search bound" in a ranking note excludes that row from the Aspen pick (was "탐색 경계").
