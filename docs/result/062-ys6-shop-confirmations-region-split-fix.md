# 062. Ys VI 상점 확인 문구 이미지 분할 수정 결과

## 결과

- `shop_confirmations`의 잘못된 256×84/84/88 균등 분할을 실제 문구 위치에
  맞는 세 편집 영역으로 교체했다.
- 사용자가 확인한 `block_offset: 1`은 변경하지 않았다.
- 세 문구 모두 요청한 왼쪽 8픽셀 여백을 포함하며, 다른 패널과 선택 버튼은
  조각에 포함되지 않는다.

## 변경 내용

- `tools/patchdata/ys6_additional_images/manifest.json`
  - `line_01` 판매 확인: `(160, 0)–(240, 20)`, 80×20
  - `line_02` 구매 확인: `(0, 108)–(92, 128)`, 92×20
  - `line_03` Gold 부족: `(0, 200)–(176, 224)`, 176×24
  - `block_offset: 1` 유지
  - `source_block_offset_applied: true` 유지
- 재생성 원본 조각:
  - `source_parts/shop_confirmations/line_01.png`
  - `source_parts/shop_confirmations/line_02.png`
  - `source_parts/shop_confirmations/line_03.png`

## 검증

- 원본 조각 크기 80×20, 92×20, 176×24 확인.
- 모든 좌표 및 크기가 4픽셀 경계에 정렬됨을 확인.
- 각 조각에 대응 문구 하나와 왼쪽 여백만 포함됨을 육안으로 확인.
- 구매·판매·그만두기 버튼 및 인접 패널이 조각에 포함되지 않음을 확인.
- 임시 RGB 전용 식별 편집 격리 검사:
  - 변경 블록: 3개
  - 변경 블록이 모두 세 문구 영역 안에 존재
  - 수정 컨테이너: 15,630/16,384바이트
  - 할당 여유: 754바이트
- 관련 단위·통합 빌더 테스트 10개 통과.
- GUI와 동일한 통합 빌드 경로로 062 테스트 ISO 생성 성공.
- 생성 ISO 재추출 검사:
  - `block_offset: 1` 유지
  - 변경 블록: 3개
  - 문구 영역 밖 변경 블록: 0개
  - 원본 ISO SHA-256 유지
- 임시 편집 PNG 세 개는 빌드 후 정확히 제거했으며
  `edited_parts/shop_confirmations`는 다시 빈 상태다.
- 다른 사용자 편집 이미지는 수정하거나 삭제하지 않았다.

## 생성 파일

- 테스트 ISO:
  `patched/062-shop-confirmations-region-split-fix/Ys VI (Japan) - 062-shop-confirmations-region-test.iso`
- 테스트 ISO SHA-256:
  `CDD6C0F98C5CC9F32DC02EDBC323314E0FBADDC7BFC8560B64ACCC0819215895`
- 격리 검사 보고서:
  `tools/patchdata/work/current/additional-images/062-shop-confirmations-isolation-report.json`
- 생성 ISO 검사 보고서:
  `tools/patchdata/work/current/additional-images/062-generated-iso-verification.json`
- 생성 ISO 재추출 이미지:
  `tools/patchdata/work/current/additional-images/062-shop-confirmations-from-generated-iso.png`

## 알려진 문제 및 정리 대상

- 현재 `edited_parts/shop_confirmations`에는 실제 한글 편집 이미지가 없다.
- 062 테스트 ISO에는 위치 검증용 식별 픽셀 3개만 들어 있으므로 배포용이 아니다.
- 실제 한글 조각을 저장한 뒤 GUI로 새 ISO를 생성해 게임 화면을 확인해야 한다.
- 062 테스트 ISO는 검증 완료 후 불필요하면 삭제할 수 있다.
- 원본 ISO는 수정하지 않았다.
