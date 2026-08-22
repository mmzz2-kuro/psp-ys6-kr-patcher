# 090. Ys VI 잔여 미번역 이미지 후보 합성 출력 결과

## 수행 내용

- 원본 ISO에서 `p901`, `p902`, `v130`, `v131`, `v132` MIG 컬렉션을 직접 읽었다.
- 각 picture의 선행 16바이트 블록을 건너뛴 뒤 원래 화면 순서로 합성했다.
- `p901`, `p902`는 8개 조각을 480×272 이미지로 합성했다.
- `v130`~`v132`는 4개 조각을 480×64 이미지로 합성했다.
- 개별 PNG 5장과 2배 확대 접촉 시트를 출력했다.

## 생성 파일

- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/p901.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/p902.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/v130.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/v131.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/v132.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/candidate-contact-sheet-2x.png`
- `tools/patchdata/work/current/090-untranslated-image-candidate-preview/report.json`
- 추가: `tools/scripts/ys6_remaining_image_candidate_preview.py`
- 완료 갱신: `docs/plan/090-ys6-remaining-image-candidate-preview.md`

## 합성 좌표

- 480×272 리소스 본문: `(0,0) 256×256`, `(256,0) 128×256`, `(384,0) 64×256`, `(448,0) 32×256`
- 480×272 리소스 하단: `(0,256) 256×16`, `(256,256) 128×16`, `(384,256) 64×16`, `(448,256) 32×16`
- 480×64 리소스: `(0,0) 256×64`, `(256,0) 128×64`, `(384,0) 64×64`, `(448,0) 32×64`

각 picture는 물리 데이터 시작점에 표시용이 아닌 16바이트 선행 블록이 있어 `data_offset + 16`으로 렌더링했다. 단순 PNG 자르기가 아니라 원본 데이터 읽기 위치를 교정했기 때문에 최종 폭과 분할 좌표는 원본의 480픽셀 구조를 그대로 유지한다.

## 검증

- 대상 리소스: 5/5 추출 및 합성 성공
- 출력 크기: `p901`, `p902` 480×272 / `v130`~`v132` 480×64
- `p901`, `p902`: 외곽 프레임, 배경과 문장 경계 연속 확인
- `v130`~`v132`: 일본어 문장 연결과 중앙 배치 확인
- 합성 스크립트 Python 구문 검사: 성공
- 원본 ISO, 추가 이미지 매니페스트, 편집 이미지, 캐시와 패치 ISO는 변경하지 않았다.

## 알려진 사항

- 출력물은 번역 전 판독·편집용 원본 미리보기다.
- 번역 이미지를 패치할 때도 같은 picture 경계로 다시 분할하고, 물리 블록 오프셋을 보존해야 한다.
