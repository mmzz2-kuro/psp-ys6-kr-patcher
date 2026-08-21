# 063. Ys VI 상점 구매·판매·그만두기 버튼 영역 추가 결과

## 결과

- `shop_confirmations`에 `買う / 売る / やめる` 버튼을 포함한 64×78 편집
  영역을 추가했다.
- 요청 좌표와 크기를 그대로 유지했으며 `block_offset: 1`은 변경하지 않았다.
- GUI 통합 빌드와 생성 ISO 재추출 검사에서 버튼 영역 변경을 확인했다.

## 변경 내용

- `tools/patchdata/ys6_additional_images/manifest.json`
  - id: `choice_buttons`
  - file: `choice_buttons.png`
  - box: `(187, 74)–(251, 152)`
  - size: 64×78
  - source text: `買う / 売る / やめる`
- 새 원본 조각:
  - `tools/patchdata/ys6_additional_images/source_parts/shop_confirmations/choice_buttons.png`
- 기존 062의 세 확인 문구 영역과 `block_offset: 1`은 유지했다.

## 비정렬 좌표 처리

- 편집 PNG와 논리 합성 좌표는 요청값 64×78 및 `(187,74)`를 그대로 사용한다.
- 실제 DXT 영향 블록 범위는 `(184,72)–(252,152)`다.
- 경계 블록은 편집 PNG 밖 픽셀을 전체 원본 이미지에서 가져와 함께 인코딩한다.

## 검증

- 원본 `choice_buttons.png` 크기 64×78 확인.
- `買う`, `売る`, `やめる` 세 버튼이 모두 포함되고 잘리지 않음을 확인.
- 비정렬 좌상단 식별 변경 격리 검사:
  - 변경 블록: 1개
  - 변경 블록이 확장 DXT 범위 안에 존재
  - 수정 컨테이너: 15,621/16,384바이트
  - 할당 여유: 763바이트
- 관련 단위·통합 빌더 테스트 10개 통과.
- GUI와 동일한 통합 빌드 경로로 063 테스트 ISO 생성 성공.
- 생성 ISO 재추출 검사:
  - `block_offset: 1` 유지
  - 버튼 영역 변경 확인
  - 원본 ISO SHA-256 유지
- 검증용 `edited_parts/shop_confirmations/choice_buttons.png`는 제거했다.
- 사용자 `line_01.png`, `line_02.png`, `line_03.png`는 수정하거나 삭제하지 않고
  모두 보존했다.

## 생성 파일

- 테스트 ISO:
  `patched/063-shop-confirmations-choice-buttons-region/Ys VI (Japan) - 063-choice-buttons-region-test.iso`
- 테스트 ISO SHA-256:
  `D2DB9581902DEDD5F65B12A2621172F4D53190D4B90AC8159D1D6C40FD7B2BA3`
- 격리 검사 보고서:
  `tools/patchdata/work/current/additional-images/063-choice-buttons-isolation-report.json`
- 생성 ISO 검사 보고서:
  `tools/patchdata/work/current/additional-images/063-generated-iso-verification.json`
- 생성 ISO 재추출 이미지:
  `tools/patchdata/work/current/additional-images/063-shop-confirmations-from-generated-iso.png`

## 알려진 문제 및 정리 대상

- 현재 실제 사용자 편집 `choice_buttons.png`는 아직 없다.
- 063 테스트 ISO의 버튼 영역에는 위치 검증용 식별 픽셀만 들어 있으므로 배포용이
  아니다.
- 실제 한글 버튼 이미지를 저장한 뒤 GUI로 새 ISO를 생성해 게임 화면을 확인해야
  한다.
- 063 테스트 ISO는 검증 완료 후 불필요하면 삭제할 수 있다.
- 원본 ISO는 수정하지 않았다.
