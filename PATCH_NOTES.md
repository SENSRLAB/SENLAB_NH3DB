# SENLAB_NH3DB 최종 업데이트 — EOS Recommendation 기능 + 평가 데이터 4계 (2026-09-01)

이 압축 하나가 **최종본 전체**입니다. 이전에 나눠 보낸 zip·JSON들을 모두 대체합니다.

## 적용 방법 (순서대로)

1. 이 압축을 SENLAB_NH3DB 저장소 폴더(로컬 클론) 루트에 풀어 **기존 파일 덮어쓰기**
2. (선택) 확인: `pip install streamlit` 후 `python3 test_apptest.py` → "checks passed" 확인, 또는 `streamlit run app.py`로 직접 열어보기
3. 커밋·푸시:
   ```bash
   git add -A
   git commit -m "Add EOS Recommendation (Data 6) with validated H2/N2/CH4/H2O results; fix N2 molar mass"
   git push
   ```
4. Streamlit Cloud가 자동 재배포(1~2분) → 앱 셀렉트박스에 "EOS Recommendation (Binary Mixtures)" 메뉴 확인
5. 각 혼합물 페이지에서 관심 T·P를 넣어 추천·경고가 뜨는지 확인

새 의존성 없음(requirements.txt 그대로).

## 무엇이 들어있나

| 파일 | 내용 |
|---|---|
| `app.py` | Data 6 메뉴 추가 + **NH₃+N₂ 질량분율 버그 수정**(mw_n2 14.006→28.014) + CH₄ 설명 오타 수정 |
| `eos_recommender.py` | Data 6 페이지 모듈 (지표 라벨 지원: H₂O는 bubble-P AARD로 표시, 극단적 base 오차는 차트 축 클리핑) |
| `eos_recommendations/nh3_h2.json` | NH₃+H₂ 검증 결과 (275/305 K, ≤85 bar; 저압 기준값은 KK 물리 외삽) |
| `eos_recommendations/nh3_n2.json` | NH₃+N₂ 검증 결과 (데이터 정제 + 연구실 CSV 증강 + KK) |
| `eos_recommendations/nh3_ch4.json` | NH₃+CH₄ 검증 결과 (저압 전부 KK 기준 — 불확도 ±20~35% 경고 포함) |
| `eos_recommendations/nh3_h2o.json` | NH₃+H₂O 검증 결과 (변형 기준: 기포압 AARD; 활성계수 모델 병행 권고 포함) |
| `eos_recommendations/README.md` | JSON 스키마 v1.0 문서 + 새 계 추가 절차 |
| `README.md` | 업데이트 일지 반영 |
| `test_apptest.py` | 스모크 테스트 (선택) |

## 결과 요약 (밴드별 추천 1위)

| 계 | 저온 ~275 K | 상온 ~305 K | 비고 |
|---|---|---|---|
| NH₃+H₂ | SRK (kij 0.176) 4.0% | CPA (기본값) 5.9% | 기본 kij=0 오차 22~74% |
| NH₃+N₂ | SW (kij 0.147) 5.9% | CPA (기본값) 7.5% | 기본 오차 90~319% |
| NH₃+CH₄ | SAFT-VR Mie (기본값) 10.6% | SAFT-VR Mie (기본값) 4.8% | 저압 기준값 불확도 ±20~35% |
| NH₃+H₂O | PC-SAFT (내장 kij −0.25) 24.7% | PC-SAFT 24.7% | 기포압 AARD 기준. 정밀 계산은 활성계수 모델/Data 4 보간 권장 |

## 주의사항

- **NH₃+N₂ 질량분율 값이 바뀝니다**: mw_n2 수정으로 기존 앱 화면 값(예: 몰분율 0.5 → 질량분율 0.549)이 올바른 값(0.378)으로 변경 — 이전 값을 인용한 보고서가 있다면 갱신 필요
- 각 JSON의 warnings에 외삽·불확도·물리 제약(예: 305 K에서 10 bar는 NH₃ 증기압 미만이라 액상 부재)이 명시되어 있고 앱에 그대로 표시됩니다
- 새 계(예: NH₃+Ar)를 추가하려면: Aspen TDE → .bkp (Retrieve 후 **Save Data** 필수) → Claude cowork에서 평가 → JSON 커밋 (`eos_recommendations/README.md` 참고)
