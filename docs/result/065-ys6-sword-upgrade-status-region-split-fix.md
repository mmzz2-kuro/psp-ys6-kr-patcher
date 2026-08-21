# 065. Ys VI 검 강화 상태 이미지 분할 수정 결과

## 결과

- `sword_upgrade_status`의 화면상 한 문구가 텍스처에서 두 조각으로 나뉘는
  구조를 편집·패치 흐름에 반영했다.
- 편집자는 문구마다 결합된 159×31 PNG 하나를 수정하면 된다.
- 패치 적용 시 도구가 PNG를 126×31과 33×31로 다시 분할하여 지정된 두 위치에
  자동으로 삽입한다.
- `block_offset: 1`은 변경하지 않았다.

## 적용 좌표

- `line_01`
  - 본문: `(130,80)–(256,111)`, 126×31
  - 보조: `(160,144)–(193,175)`, 33×31
- `line_02`
  - 본문: `(130,112)–(256,143)`, 126×31
  - 보조: `(194,144)–(227,175)`, 33×31

## 변경 내용

- `tools/scripts/ys6_additional_image_patch.py`
  - 기존 단일 `box`와 새 복수 `boxes` 형식을 모두 지원한다.
  - 추출 시 복수 조각을 지정 순서대로 가로 결합한다.
  - 합성 시 결합 이미지를 각 조각 너비로 역분할하여 원래 좌표에 붙인다.
- `tools/scripts/tests/test_ys6_additional_image_patch.py`
  - 복수 조각 결합 및 역분할 회귀 테스트 2개를 추가했다.
- `tools/patchdata/ys6_additional_images/manifest.json`
  - `sword_upgrade_status`의 두 영역을 각각 두 개의 원본 사각형으로 변경했다.
- 재생성 편집 원본:
  - `source_parts/sword_upgrade_status/line_01.png`, 159×31
  - `source_parts/sword_upgrade_status/line_02.png`, 159×31

## 검증

- 원본 조각 결합 후 즉시 역분할한 결과가 원본 텍스처와 픽셀 단위로 일치했다.
- 관련 단위·통합 빌더 테스트 12개가 통과했다.
- GUI가 사용하는 `ys6_patch_builder.py` 통합 빌드 경로로 테스트 ISO를 생성했다.
- 생성 ISO에서 `emeparts0.dds.z`를 재추출하여 확인했다.
  - 컨테이너 검증 성공
  - 변경 블록: 4개
  - 네 지정 영역 밖 변경 블록: 0개
  - `block_offset: 1` 유지
  - 원본 ISO SHA-256 유지
- 검증용 `edited_parts/sword_upgrade_status/line_01.png`와 `line_02.png`는 제거했다.
- 다른 사용자 편집 이미지는 변경하거나 삭제하지 않았다.

## 생성 파일

- 테스트 ISO:
  `patched/065-sword-upgrade-status-region-split-fix/Ys VI (Japan) - 065-sword-upgrade-status-region-test.iso`
- 테스트 ISO SHA-256:
  `D2B9C1048BC4ED43C66AC1979081C73B44636FB683F8543E66F74AAE3C012DA7`
- 생성 ISO 검사 보고서:
  `tools/patchdata/work/current/additional-images/065-generated-iso-verification.json`
- 생성 ISO 재추출 결합 이미지:
  `tools/patchdata/work/current/additional-images/065-sword-upgrade-status-from-generated-iso/`

## 알려진 문제 및 정리 대상

- 현재 `edited_parts/sword_upgrade_status`에는 실제 한글 편집 이미지가 없다.
- 테스트 ISO에는 위치 검증용 식별 픽셀만 들어 있으므로 배포용이 아니다.
- 실제 번역 이미지는 반드시 159×31 크기로 저장해야 한다.
- 065 테스트 ISO는 검증 완료 후 불필요하면 삭제할 수 있다.
- 원본 ISO와 원본 PNG는 수정하지 않았다.
