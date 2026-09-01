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
