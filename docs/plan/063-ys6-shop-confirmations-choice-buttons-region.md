# 063. Ys VI 상점 구매·판매·그만두기 버튼 영역 추가 계획

## 상태

- 완료 (2026-08-21)

## 문제

- 062에서 `shop_confirmations`의 세 확인 문구만 독립 편집 영역으로 분리했다.
- 같은 텍스처에 있는 `買う`, `売る`, `やめる` 버튼도 추가 편집 대상으로 제공해야
  한다.

## 확인된 영역

- 원본 논리 좌표: `(187, 74)`
- 크기: 64×78
- 박스: `(187, 74)–(251, 152)`
- 포함 내용:
  - `買う`
  - `売る`
  - `やめる`
- 현재 `shop_confirmations.block_offset: 1`은 변경하지 않는다.

## 목표

- 요청한 64×78 영역을 `shop_confirmations`의 네 번째 편집 이미지로 추가한다.
- GUI에서 세 버튼을 하나의 PNG로 편집하고 원래 좌표에 정확히 합성할 수 있게 한다.
- 기존 세 문구 영역과 다른 아틀라스 요소는 유지한다.

## 수정 범위

1. `tools/patchdata/ys6_additional_images/manifest.json`의
   `shop_confirmations.regions`에 다음 항목을 추가한다.
   - id: `choice_buttons`
   - source text: `買う / 売る / やめる`
   - file: `choice_buttons.png`
   - box: `[187, 74, 251, 152]`
   - width: 64
   - height: 78
2. `source_parts/shop_confirmations/choice_buttons.png`를 현재 오프셋 1 원본에서
   정확히 64×78로 추출한다.
3. `edited_parts/shop_confirmations/choice_buttons.png`가 있으면 GUI가 자동으로
   인식하고 같은 좌표에 합성하도록 기존 직사각형 영역 처리 경로를 사용한다.
4. 기존 세 문구 조각과 `block_offset: 1`은 변경하지 않는다.
5. 향후 `prepare` 재실행에서도 네 번째 영역이 유지되게 한다.

## 비정렬 좌표 처리

- 요청 좌표 `(187,74)`와 끝 좌표 `(251,152)` 중 x 및 시작 y는 4픽셀 경계가
  아니다.
- 편집 PNG 크기와 합성 좌표는 요청값 64×78을 그대로 유지한다.
- DXT 블록 단위 실제 영향 범위는 바깥쪽 4픽셀 경계로 확장된
  `(184,72)–(252,152)`다.
- 경계 블록은 편집 영역 밖 픽셀을 원본 전체 이미지에서 함께 가져와 재인코딩한다.
  따라서 편집 PNG 밖의 픽셀을 임의로 덮어쓰지 않는다.

## 검증

1. 원본 조각 검사
   - 출력 크기가 정확히 64×78인지 확인
   - 세 버튼 전체가 잘리지 않고 포함되는지 확인
   - 인접 문구나 다른 버튼이 포함되지 않는지 확인
2. 매니페스트 검사
   - 기존 세 문구 영역 유지
   - 네 번째 영역 좌표·크기·파일명 확인
   - `block_offset: 1` 유지 확인
3. 격리 편집 검사
   - 임시 `choice_buttons.png`에 식별 변경 적용
   - 변경 블록이 확장 영향 범위 `(184,72)–(252,152)` 안에만 존재하는지 확인
   - 경계 블록의 편집 영역 밖 픽셀이 원본과 최대한 동일하게 유지되는지 확인
   - 기존 세 문구 영역이 바뀌지 않는지 확인
4. GUI 통합 검사
   - `choice_buttons.png`를 추가 이미지로 인식
   - `shopp1.dds.z` 교체 목록 포함
   - 컨테이너 할당 공간 초과 없음
5. 생성 ISO 재추출 검사
   - 버튼 편집 결과가 요청 좌표에 나타나는지 확인
   - 기존 세 문구와 다른 UI 요소 유지 확인
   - 원본 ISO SHA-256 유지 확인

## 산출물

- 수정 매니페스트:
  `/tools/patchdata/ys6_additional_images/manifest.json`
- 새 원본 조각:
  `/tools/patchdata/ys6_additional_images/source_parts/shop_confirmations/choice_buttons.png`
- 검증 결과:
  `/tools/patchdata/work/current/additional-images/`
- 테스트 ISO:
  `/patched/063-shop-confirmations-choice-buttons-region/`
- 결과 문서:
  `/docs/result/063-ys6-shop-confirmations-choice-buttons-region.md`

## 제외 범위

- 기존 세 확인 문구 좌표 변경
- `shop_confirmations.block_offset` 변경
- 버튼 외 상점 패널 디자인 변경
- 다른 추가 이미지 리소스 변경
- 원본 ISO 직접 수정

## 복구 방법

- 매니페스트의 `choice_buttons` 항목과 생성된 원본 조각만 제거하면 062 상태로
  돌아간다.
- 별도 063 테스트 ISO만 생성하며 원본 ISO는 수정하지 않는다.
