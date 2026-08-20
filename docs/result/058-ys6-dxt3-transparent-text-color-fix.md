# 058. Ys VI DXT3 투명 이미지 글자 색상 압축 수정 결과

## 원인 판단 정정

- 이 문서에서 다룬 DXT3 색상 인코딩은 개선됐지만, 게임에서 원본 일본어가
  표시된 직접 원인은 색상 압축이 아니었다.
- 원본 ISO에는 독립 `placename02.dds.z` 외에 동일한 맵 아카이브 런타임 사본이
  14개 존재하며, 058 빌드는 독립 파일만 교체했다.
- 실제 런타임 사본 동기화는 059에서 수정하고 검증했다.

## 결과

- DXT3의 투명 검정 배경이 반투명 흰색 글자의 RGB 끝점 선택에 포함되어 글자가
  검게 복원되던 문제를 수정했다.
- `place_names_02/line_05.png`, `line_06.png`를 적용한 통합 ISO를 생성하고,
  ISO에서 다시 추출한 이미지에서 한글 글자가 흰색 계열로 보이는 것을 확인했다.

## 변경 내용

- `tools/scripts/ys6_additional_image_patch.py`
  - 알파가 0인 픽셀을 DXT3 RGB 색상 탐색에서 제외했다.
  - 가시 픽셀의 RGB 오차에 알파값을 가중치로 적용했다.
  - DXT3 RGB 블록을 항상 4색 불투명 모드로 인코딩했다.
  - 완전 투명 블록은 원본 RGB 8바이트를 유지하고 알파만 0으로 기록했다.
  - DXT3 4비트 알파는 편집 PNG에서 별도로 양자화했다.
  - 수정되지 않은 블록과 057의 논리·물리 블록 오프셋 변환은 유지했다.
- `tools/scripts/tests/test_ys6_additional_image_patch.py`
  - 투명 검정과 반투명 흰색이 함께 있는 블록의 색상 복원 검사를 추가했다.
  - 완전 투명 블록의 원본 RGB 보존 검사를 추가했다.

## 검증

- Python 컴파일 검사 통과.
- 새 DXT3 검사와 기존 통합 빌더 검사 총 7개 통과.
- 실제 편집 이미지 2개 적용 결과:
  - 인식된 편집 이미지: 2개
  - 변경 DXT3 블록: 547개
  - 가시 픽셀: 3,310개
  - RGB RMSE: 0.0
  - DXT3 4비트 양자화 기준 최대 알파 오차: 0
  - 투명 픽셀이 불투명해진 사례: 0개
- `place_names_00`, `place_names_01`, `place_names_02` DXT3 블록 회귀 검사 통과.
- 통합 사전검사 통과, 할당 공간 초과 없음.
  - 생성 `placename02.dds.z`: 6,200바이트
  - 할당 공간: 8,192바이트
- 생성 ISO에서 추출한 컨테이너가 빌드 작업본과 바이트 단위로 일치했다.
- 원본 ISO SHA-256은 빌드 전후 모두
  `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`로 유지됐다.

## 생성 파일

- 테스트 ISO:
  `patched/058-dxt3-transparent-text-color-fix/Ys VI (Japan) - 058-dxt3-color-fix-test.iso`
- 테스트 ISO SHA-256:
  `A582DF407CC0B07464250A73F92F06540A06082E97119FCF83A058E19E0C8A7F`
- 오차 보고서:
  `tools/patchdata/work/current/additional-images/dxt3-color-alpha-report.json`
- ISO 재추출 이미지:
  `tools/patchdata/work/current/additional-images/place_names_02-from-generated-iso.png`
- 어두운 배경 확인 이미지:
  `tools/patchdata/work/current/additional-images/place_names_02-from-generated-iso-dark-preview.png`

## 알려진 문제 및 정리 대상

- 058 테스트 ISO는 14개 런타임 사본이 원본이므로 지역명 반영 검증용으로 사용할
  수 없다. 후속 059 테스트 ISO를 사용해야 한다.
- 생성한 058 테스트 ISO는 이 이슈의 검증 작업본이다. 런타임 확인이 끝나 불필요해지면
  해당 ISO를 삭제할 수 있다.
- 원본 ISO와 `source_images`는 변경하지 않았다.
