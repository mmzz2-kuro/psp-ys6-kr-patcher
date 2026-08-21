# 064. Ys VI 상점 선택 이미지 분할 수정 결과

## 결과

- `shop_choice`의 잘못된 256×32 균등 분할을 질문 문구와 세 버튼의 실제 위치에
  맞는 네 편집 영역으로 교체했다.
- `売る`와 `やめる`가 서로 섞이지 않으며 모든 글자와 버튼 테두리가 포함된다.
- 사용자가 확인한 `block_offset: 1`은 변경하지 않았다.

## 변경 내용

- `tools/patchdata/ys6_additional_images/manifest.json`
  - 질문: `(44,8)–(160,36)`, 116×28
  - 구매: `(68,32)–(136,60)`, 68×28
  - 판매: `(68,60)–(136,88)`, 68×28
  - 그만두기: `(68,88)–(136,116)`, 68×28
  - `block_offset: 1` 유지
- 재생성 원본 조각:
  - `source_parts/shop_choice/line_01.png`
  - `source_parts/shop_choice/line_02.png`
  - `source_parts/shop_choice/line_03.png`
  - `source_parts/shop_choice/line_04.png`

## 겹침 처리

- 질문과 구매 영역은 `(68,32)–(136,36)`의 68×4 영역에서 겹친다.
- 두 조각은 같은 원본에서 추출돼 기본 배경 픽셀이 일치한다.
- 합성 순서상 구매 조각이 겹친 영역의 최종 픽셀을 결정한다.
- 질문 번역은 추가된 아래쪽 4픽셀 여백을 침범하지 않는 조건으로 사용한다.

## 검증

- 원본 조각 크기 116×28, 68×28, 68×28, 68×28 확인.
- 모든 좌표와 크기가 4픽셀 경계에 정렬됨을 확인.
- 네 조각에 대응 문구 또는 버튼 하나씩만 포함됨을 확인.
- `売る`와 `やめる`가 분리되고 글자·버튼 테두리가 잘리지 않음을 확인.
- 임시 RGB 전용 식별 편집 격리 검사:
  - 변경 블록: 4개
  - 변경 블록이 모두 네 영역 합집합 안에 존재
  - 수정 컨테이너: 9,450/10,240바이트
  - 할당 여유: 790바이트
- 관련 단위·통합 빌더 테스트 10개 통과.
- GUI와 동일한 통합 빌드 경로로 064 테스트 ISO 생성 성공.
- 생성 ISO 재추출 검사:
  - `block_offset: 1` 유지
  - 변경 블록: 4개
  - 영역 밖 변경 블록: 0개
  - 원본 ISO SHA-256 유지
- 검증용 `edited_parts/shop_choice/line_01~04.png`는 제거했다.
- 다른 사용자 편집 이미지는 수정하거나 삭제하지 않았다.

## 생성 파일

- 테스트 ISO:
  `patched/064-shop-choice-region-split-fix/Ys VI (Japan) - 064-shop-choice-region-test.iso`
- 테스트 ISO SHA-256:
  `F827E7C221FC522830E76DC081140979DA527C9578E3CDC4F57459BCD0CEDDAA`
- 격리 검사 보고서:
  `tools/patchdata/work/current/additional-images/064-shop-choice-isolation-report.json`
- 생성 ISO 검사 보고서:
  `tools/patchdata/work/current/additional-images/064-generated-iso-verification.json`
- 생성 ISO 재추출 이미지:
  `tools/patchdata/work/current/additional-images/064-shop-choice-from-generated-iso.png`

## 알려진 문제 및 정리 대상

- 현재 `edited_parts/shop_choice`에는 실제 한글 편집 이미지가 없다.
- 질문과 구매 영역의 4픽셀 겹침 때문에 질문 이미지의 아래 여백에 내용을 그리면
  구매 이미지가 해당 부분을 덮어쓴다.
- 064 테스트 ISO에는 위치 검증용 식별 픽셀만 들어 있으므로 배포용이 아니다.
- 실제 한글 이미지를 저장한 뒤 GUI로 새 ISO를 생성해 게임 화면을 확인해야 한다.
- 064 테스트 ISO는 검증 완료 후 불필요하면 삭제할 수 있다.
- 원본 ISO는 수정하지 않았다.
