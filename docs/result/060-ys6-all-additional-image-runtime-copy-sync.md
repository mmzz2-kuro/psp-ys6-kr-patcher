# 060. Ys VI 전체 추가 이미지 런타임 사본 동기화 결과

## 결과

- `place_names_00`, `place_names_01`, `place_names_02`의 모든 확인된 맵
  아카이브 사본을 GUI 통합 빌드 동기화 대상으로 등록했다.
- 현재 사용자 편집 상태인 `place_names_01` 8개와 `place_names_02` 6개를 실제
  060 ISO에 적용하고 각각 13개와 14개 런타임 사본에서 동일하게 반영된 것을
  확인했다.
- 현재 편집 파일이 없는 `place_names_00`은 사용자 작업 공간을 변경하지 않는
  격리 검사에서 14개 사본 동기화를 확인했다.

## 변경 내용

- `tools/patchdata/ys6_additional_images/manifest.json`
  - `place_names_00` 런타임 사본 14개 추가
  - `place_names_01` 런타임 사본 13개 추가
  - 059의 `place_names_02` 런타임 사본 14개 유지
- 059에서 구현한 공통 `runtime_copies` 처리 경로를 사용하므로 GUI에서 지역명
  편집 파일을 넣고 빌드하면 해당 독립 파일과 맵 아카이브 사본이 함께 교체된다.

## 전체 추가 이미지 사본 관계

- 맵 아카이브 사본:
  - `place_names_00`: 14개
  - `place_names_01`: 13개
  - `place_names_02`: 14개
  - 전체: 41개
- 기존 `static_tex` 내장 사본 동기화:
  - `save_confirmations`: 그림 69
  - `item_use_confirmation`: 그림 62
  - `item_message`: 그림 61
- 확인된 중복 사본이 없는 독립 리소스:
  - `world_map`
  - `sword_upgrade_status`
  - `sword_upgrade_confirmation`
  - `shop_choice`
  - `shop_confirmations`

## 검증

- 매니페스트 런타임 사본 정의 41개 및 고유 정의 41개 확인.
- 관련 단위·통합 빌더 테스트 9개 통과.
- `place_names_00` 격리 단일 블록 검사:
  - 변경 블록: 1개
  - 런타임 사본 교체 및 일치: 14/14개
  - 수정 컨테이너: 8,795바이트
  - 최소 할당 여유: 1,445바이트
- `place_names_01` 격리 단일 블록 검사:
  - 변경 블록: 1개
  - 런타임 사본 교체 및 일치: 13/13개
  - 수정 컨테이너: 9,454바이트
  - 최소 할당 여유: 786바이트
- 실제 사용자 이미지 통합 빌드:
  - 편집 이미지: 14개
  - 편집 리소스: `place_names_01`, `place_names_02`
  - 변경 DXT3 블록: 3,389개
  - 런타임 사본 교체: 27/27개
  - 할당 공간 초과: 0개
- 생성 ISO 재추출:
  - `place_names_01`: 컨테이너·payload·렌더 일치 13/13개
  - `place_names_02`: 컨테이너·payload·렌더 일치 14/14개
- 원본 ISO SHA-256은 빌드 후에도
  `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`로 유지됐다.
- 격리 검사는 임시 디렉터리에서 수행했으며 사용자 편집 파일을 생성·수정·삭제하지
  않았다.

## 생성 파일

- 테스트 ISO:
  `patched/060-all-additional-image-runtime-copy-sync/Ys VI (Japan) - 060-all-additional-image-runtime-copy-sync-test.iso`
- 테스트 ISO SHA-256:
  `2EB7E50AC63BBC5EA427F7FFEAD422B2569F74F007662E72AD4DFF960CC28879`
- 격리 검사 보고서:
  `tools/patchdata/work/current/additional-images/060-runtime-copy-isolation-report.json`
- 생성 ISO 검사 보고서:
  `tools/patchdata/work/current/additional-images/060-generated-iso-runtime-copy-report.json`
- 생성 ISO 재추출 이미지 및 어두운 배경 미리보기:
  - `060-place_names_01-from-generated-iso.png`
  - `060-place_names_01-dark-preview.png`
  - `060-place_names_02-from-generated-iso.png`
  - `060-place_names_02-dark-preview.png`

## 알려진 문제 및 정리 대상

- `place_names_00`은 현재 사용자 편집 이미지가 없어 060 ISO에서 실제 변경되지
  않았다. 향후 GUI 편집 시 등록된 14개 사본이 자동 동기화된다.
- 에뮬레이터 또는 실기에서 `place_names_01` 지역명의 실제 표시는 아직 확인하지
  않았다.
- 060 테스트 ISO는 런타임 확인 후 불필요하면 삭제할 수 있다.
- 원본 ISO와 사용자 편집 이미지는 수정하지 않았다.
