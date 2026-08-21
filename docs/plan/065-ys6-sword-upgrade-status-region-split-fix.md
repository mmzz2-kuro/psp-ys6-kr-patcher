# 065. Ys VI 검 강화 상태 이미지 분할 수정 계획

상태: 완료

## 배경

- `sword_upgrade_status`의 현재 분할은 256×256 원본을 위·아래 128픽셀로
  나누고 있어, 일본어 상태 문구뿐 아니라 무기 그림과 강화 목록 UI까지 포함한다.
- 편집 이미지에 불필요한 UI가 포함되면 번역 이미지 합성 시 원본 UI를 덮어쓸
  위험이 있다.

## 현재 상태

- 대상 원본:
  `tools/patchdata/ys6_additional_images/source_images/sword-upgrade-status.png`
- 현재 영역:
  - `line_01`: `(0,0)–(256,128)`, 256×128
  - `line_02`: `(0,128)–(256,256)`, 256×128
- `block_offset: 1`이 적용되어 있으며 이 값은 변경하지 않는다.
- `edited_parts/sword_upgrade_status`에는 현재 편집 이미지가 없다.

## 확인된 저장 구조

- 화면상 한 문구가 텍스처 안에서는 두 직사각형으로 나뉘어 저장되어 있다.
- `line_01`:
  - 본문 조각: `(130,80)`, 126×31
  - 보조 조각: `(160,144)`, 33×31
- `line_02`:
  - 본문 조각: `(130,112)`, 126×31
  - 보조 조각: `(194,144)`, 33×31
- 편집용 이미지는 각 쌍을 왼쪽부터 본문 126픽셀, 보조 33픽셀 순서로 이어 붙인
  159×31 이미지로 제공한다.

## 변경 계획

1. 매니페스트가 한 편집 이미지에 복수의 원본 사각형을 지정할 수 있도록 영역
   구조를 확장한다.
2. 추출할 때 각 문구의 두 조각을 지정 순서로 가로 결합한다.
   - `line_01.png`: 159×31
   - `line_02.png`: 159×31
3. 합성할 때 편집 이미지의 앞 126×31과 뒤 33×31을 다시 분리하여 각 원본
   좌표에 붙여 넣는다.
4. `block_offset: 1`과 ISO 내부 대상 경로는 유지한다.
5. 결합 이미지에서 문구가 자연스럽게 이어지고 편집 후 역분할 결과가 정확한지
   시각적으로 확인한다.
6. 임시 식별 편집 이미지를 사용해 변경 블록이 네 원본 사각형을 포함하는 압축
   블록 범위 안에만 존재하는지 검사한다.
7. 기존 단일 사각형 리소스의 추출·합성이 이전과 동일하게 작동하도록 호환성을
   유지하고 관련 단위 테스트를 추가한다.
8. GUI 동일 통합 빌드 경로로 테스트 ISO를 생성해 재추출한다.
9. 검증용 임시 편집 이미지는 제거하고 결과를 `/docs/result`에 기록한다.

## 변경 대상

- `tools/patchdata/ys6_additional_images/manifest.json`
- `tools/patchdata/ys6_additional_images/source_parts/sword_upgrade_status/line_01.png`
- `tools/patchdata/ys6_additional_images/source_parts/sword_upgrade_status/line_02.png`
- 검증 보고서 및 065 테스트 ISO
- `docs/result/065-ys6-sword-upgrade-status-region-split-fix.md`

## 보존 및 주의 사항

- 원본 ISO와 원본 PNG는 수정하지 않는다.
- `block_offset`은 변경하지 않는다.
- 다른 리소스의 사용자 편집 이미지는 수정하거나 삭제하지 않는다.
- 테스트 ISO는 `/patched/065-sword-upgrade-status-region-split-fix`에 별도로 둔다.

## 완료 기준

- 두 분할 이미지에 대응 상태 문구만 온전히 포함된다.
- 매니페스트 영역과 실제 PNG 크기가 일치한다.
- 변경 블록이 지정 영역을 벗어나지 않는다.
- GUI 동일 빌드와 생성 ISO 재추출 검증이 성공한다.
