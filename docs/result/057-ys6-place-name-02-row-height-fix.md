# 057. Ys VI 지역명 행 높이 및 4×4 블록 오프셋 수정 결과

## 결과

- `place_names_02`의 잘못된 40/56픽셀 분할을 256×32픽셀 고정 행 6개로 수정했다.
- `source_images` 전체에서 확인된 4×4 압축 블록 오프셋을 논리 화면 좌표로
  교정했다.

## 변경 내용

- 지역명 고정 분할 규칙을 처리 스크립트에 추가했다.
  - `place_names_00`: 256×32, 8개
  - `place_names_01`: 256×32, 8개
  - `place_names_02`: 256×32, 6개
- `place_names_02`의 사용하지 않는 y=192–256 영역은 조각에서 제외하고 원본으로
  유지한다.
- 매니페스트의 11개 리소스에 `block_offset: 1`을 기록했다.
- 추출 화면에서는 4×4 블록 스트림을 한 칸 앞으로 회전하여 논리 좌표로 표시한다.
- 재삽입에서는 수정한 논리 블록을 대응하는 원본 저장 블록 위치에 기록한다.
- 교정된 `source_images`, `source_parts`, 연락 시트를 다시 생성했다.

## 검증

- 지역명 세 리소스의 모든 조각이 256×32임을 확인했다.
- 원본 ISO에서 직접 디코딩하고 오프셋을 교정한 결과가 11개 `source_images`와
  픽셀 단위로 모두 일치했다.
- `place_names_02/line_05.png` 단일 픽셀 변경 역테스트:
  - 변경 DXT3 블록: 1개
  - 컨테이너 크기: 7,637바이트
  - 할당 여유: 555바이트
- 실제 통합 사전검사 통과:
  - 추가 이미지 1개 및 변경 블록 1개 인식
  - 할당 공간 초과 없음
- 역테스트용 편집 PNG는 검사 후 제거했다.
- 원본 ISO는 수정하지 않았다.

## 변경 파일

- `tools/scripts/ys6_additional_image_patch.py`
- `tools/patchdata/ys6_additional_images/manifest.json`
- `tools/patchdata/ys6_additional_images/source_images/*`
- `tools/patchdata/ys6_additional_images/source_parts/*`
- `tools/patchdata/ys6_additional_images/source-images-contact-sheet.png`
