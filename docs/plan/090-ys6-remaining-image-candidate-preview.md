# 090. Ys VI 잔여 미번역 이미지 후보 합성 출력 계획

상태: 완료

## 목적

- 089번 조사에서 확인한 미번역 후보 5개를 사람이 읽고 편집할 수 있는 합성 PNG로 출력한다.
- 대상은 `p901.dds.z`, `p902.dds.z`, `v130.dds.z`, `v131.dds.z`, `v132.dds.z`이다.

## 작업 절차

1. 원본 ISO에서 대상 MIG 컨테이너를 읽고 각 picture를 추출한다.
2. picture 순서와 크기를 확인해 원래 화면 좌표대로 결합한다.
3. `p901`, `p902`는 480×272 구조의 본문·하단 조각을 각각 합성한다.
4. `v130`~`v132`는 480×64 구조로 합성한다.
5. 조각 경계, 누락 픽셀, 투명도와 문장 연결 상태를 시각적으로 검증한다.
6. 개별 원본 크기 PNG 5장과 한눈에 보는 확대 접촉 시트를 생성한다.

## 산출물

- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/p901.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/p902.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/v130.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/v131.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/v132.png`
- 후보 5장 확대 접촉 시트
- 합성 좌표와 검증 내용을 기록한 보고서
- `docs/result/090-ys6-remaining-image-candidate-preview.md`

## 변경 범위

- 필요하면 합성용 비GUI 스크립트를 `tools/scripts`에 추가한다.
- 원본 ISO, 번역 이미지, 추가 이미지 매니페스트, 캐시와 패치 ISO는 변경하지 않는다.

## 완료 기준

- 후보 5개가 글자나 배경 조각의 잘림 없이 각각 한 장의 이미지로 출력된다.
- picture 결합 경계와 최종 크기가 기록된다.
- 사용자가 이미지 내용을 확인할 수 있도록 결과 이미지를 제시한다.
