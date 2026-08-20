# 061. Ys VI 저장 확인 이미지 블록 오프셋 및 분할 수정 결과

## 결과

- `save_confirmations`에 잘못 적용된 4×4 블록 오프셋을 제거했다.
- 원본 ISO의 오프셋 0 렌더로 `save-confirmations.png`를 다시 생성해 좌측 4픽셀
  밀림과 마지막 블록 래핑을 제거했다.
- 세 문구를 실제 아틀라스 위치에 맞는 독립 편집 조각으로 다시 분할했다.
- 독립 `saveicon2.dds.z`와 `init.bin/static_tex.dds.z` 그림 69의 동기화 및
  생성 ISO 재추출 검사를 통과했다.

## 변경 내용

- `tools/patchdata/ys6_additional_images/manifest.json`
  - `save_confirmations.block_offset`: `1` → `0`
  - 문구 순서와 원문 정정
  - 잘못된 40/40/48 수평 분할을 실제 문구 좌표로 교체
- 새 편집 영역:
  - `line_01` 로드 확인: `(80, 0)–(324, 24)`, 244×24
  - `line_02` 덮어쓰기 확인: `(80, 48)–(324, 72)`, 244×24
  - `line_03` 삭제 확인: `(88, 68)–(320, 92)`, 232×24
- `tools/scripts/ys6_additional_image_patch.py`
  - 매니페스트에 오프셋이 없는 새 리소스의 기본값을 0으로 변경했다.
  - RGBA 변경 검사가 알파뿐 아니라 RGB 전체 채널을 보도록 수정했다.
  - 알파를 유지하고 글자 색상만 바꾼 편집도 변경 블록으로 인식한다.
- 재생성 파일:
  - `source_images/save-confirmations.png`
  - `source_parts/save_confirmations/line_01.png`
  - `source_parts/save_confirmations/line_02.png`
  - `source_parts/save_confirmations/line_03.png`

## 검증

- 새 원본 PNG가 원본 ISO payload의 오프셋 0 렌더와 픽셀 단위로 동일함을 확인했다.
- 세 편집 좌표와 크기가 모두 4픽셀 정렬임을 확인했다.
- 각 조각에는 대응 문구 하나만 포함되며 인접 문구와 우측 `Yes/No/Delete`가
  포함되지 않는다.
- RGB만 변경한 편집 감지 검사:
  - 적용 영역: `line_01`
  - 변경 블록: 1개
- 관련 단위·통합 빌더 테스트 10개 통과.
- 임시 식별 편집 격리 검사:
  - 독립 파일 변경 블록: 3개
  - 내장 그림 69 변경 블록: 3개
  - 모든 변경 블록이 세 문구 영역 안에만 존재
  - 독립 파일과 내장 그림 69의 렌더 결과 동일
  - 독립 컨테이너: 14,416/16,384바이트, 여유 1,968바이트
  - `static_tex` 컨테이너: 663,458/665,600바이트, 여유 2,142바이트
- 061 테스트 ISO 재추출:
  - 독립 파일과 내장 그림 69 렌더 동일
  - 식별 변경 블록 3개가 문구 영역 안에만 존재
  - 원본 ISO SHA-256 유지
- 임시 편집 파일 제거 후 실제 GUI 사전검사:
  - 현재 사용자 지역명 이미지: 22개
  - 추가 이미지 리소스: 3개
  - 지역명 런타임 사본: 41/41개 교체
  - 할당 공간 초과: 0개
- 사용자 편집 이미지는 생성·수정·삭제하지 않았다.

## 생성 파일

- 테스트 ISO:
  `patched/061-save-confirmations-offset-and-region-split-fix/Ys VI (Japan) - 061-save-confirmations-offset-region-test.iso`
- 테스트 ISO SHA-256:
  `414135B1CF582EA1DD41FC8E41D1229F4DDFF831A276123E128AF72C69AA7830`
- 격리 검사 보고서:
  `tools/patchdata/work/current/additional-images/061-save-confirmations-isolation-report.json`
- 생성 ISO 검사 보고서:
  `tools/patchdata/work/current/additional-images/061-generated-iso-verification.json`
- 생성 ISO 재추출 이미지:
  `tools/patchdata/work/current/additional-images/061-save-confirmations-from-generated-iso.png`

## 알려진 문제 및 정리 대상

- 현재 `edited_parts/save_confirmations`는 비어 있으며 실제 한글 편집 이미지는
  아직 적용되지 않았다.
- 061 테스트 ISO의 저장 확인 문구에는 위치 검증용 식별 픽셀 3개만 들어 있으므로
  배포용이 아니다.
- 실제 한글 조각을 저장한 뒤 GUI로 새 ISO를 생성해 게임 화면을 확인해야 한다.
- 061 테스트 ISO는 검증이 끝난 뒤 삭제할 수 있다.
- 원본 ISO는 수정하지 않았다.
