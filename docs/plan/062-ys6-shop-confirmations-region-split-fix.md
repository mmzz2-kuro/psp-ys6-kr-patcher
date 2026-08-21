# 062. Ys VI 상점 확인 문구 이미지 분할 수정 계획

## 상태

- 완료 (2026-08-21)

## 문제

- `shop_confirmations`의 현재 원본 조각은 256×256 이미지를 문구 수로 균등
  분할한 256×84, 256×84, 256×88 크기다.
- 실제 텍스처는 여러 패널, 선택 버튼, 색상 영역이 섞인 아틀라스이므로 현재
  조각마다 다른 패널과 버튼이 함께 들어가고 일부 문구는 분할 경계에 걸린다.
- 사용자가 문구만 편집하기 어렵고, 넓은 배경 영역까지 불필요하게 재인코딩될
  위험이 있다.

## 확인 사항

- `shop_confirmations.block_offset`의 현재 값 `1`은 정상 적용된 상태로 사용자가
  확인했으므로 변경하지 않는다.
- 현재 오프셋 1 원본 이미지에서 세 문구의 편집 영역을 다음 좌표로 확정했다.

| 조각 | 원문 | 좌표 | 크기 |
|---|---|---|---:|
| `line_01` | `売りますか？` | `(160, 0)–(240, 20)` | 80×20 |
| `line_02` | `買いますか？` | `(0, 108)–(92, 128)` | 92×20 |
| `line_03` | `Goldが足りません。` | `(0, 200)–(176, 224)` | 176×24 |

- 세 영역 모두 글자 앞에 8픽셀의 추가 여백을 포함한다.
- 모든 좌표와 크기는 4×4 DXT 블록 경계에 맞는다.
- 확인용 출력에서 각 조각에는 대응 문구 하나만 들어가며 구매·판매·그만두기
  버튼과 다른 문구는 포함되지 않는다.

## 목표

- `source_parts/shop_confirmations`를 실제 문구 위치에 맞는 세 조각으로 다시
  생성한다.
- GUI에서 각 문구를 독립적으로 편집하고 원래 아틀라스 좌표에 정확히 합성할 수
  있게 한다.
- 문구 영역 밖의 패널, 버튼 및 미사용 영역은 원본 압축 블록 그대로 유지한다.

## 수정 범위

1. `tools/patchdata/ys6_additional_images/manifest.json`의
   `shop_confirmations.regions`를 확정 좌표와 크기로 변경한다.
2. `block_offset: 1`과 `source_block_offset_applied: true`는 유지한다.
3. 현재 `source_images/shop-confirmations.png`에서 다음 파일을 다시 추출한다.
   - `source_parts/shop_confirmations/line_01.png`: 80×20
   - `source_parts/shop_confirmations/line_02.png`: 92×20
   - `source_parts/shop_confirmations/line_03.png`: 176×24
4. 향후 `prepare`를 다시 실행해도 균등 분할로 돌아가지 않도록 명시적 영역 정의를
   유지한다.
5. 기존 `compose_payload`의 직사각형 영역 합성 경로를 사용한다. 세 문구는 각각
   하나의 직사각형으로 안전하게 분리되므로 `pieces` 확장은 하지 않는다.
6. 현재 `edited_parts/shop_confirmations` 상태를 확인하고 기존 사용자 편집 파일이
   있으면 자동으로 덮어쓰지 않는다.

## 검증

1. 원본 조각 검사
   - 세 파일의 크기가 각각 80×20, 92×20, 176×24인지 확인
   - 글자 앞 8픽셀 여백이 포함되는지 확인
   - 각 파일에 대응 문구 하나만 포함되는지 확인
   - 선택 버튼이나 인접 패널이 섞이지 않는지 확인
2. 좌표 검사
   - 모든 좌표가 4픽셀 정렬인지 확인
   - 세 영역이 서로 겹치지 않는지 확인
   - `block_offset: 1`이 변경되지 않았는지 확인
3. 무수정 왕복 검사
   - 새 원본 조각을 그대로 합성했을 때 논리 RGBA가 유지되는지 확인
   - 문구 영역 밖의 DXT 블록이 원본 바이트와 동일한지 확인
4. 격리 편집 검사
   - 사용자 작업 공간과 분리된 임시 디렉터리에서 각 조각에 식별 변경 적용
   - 변경 블록이 각 문구 영역 안에만 존재하는지 확인
   - 다른 문구, 패널 및 버튼이 바뀌지 않는지 확인
   - 임시 파일 정리 확인
5. GUI 통합 검사
   - 세 편집 이미지 인식
   - 독립 `PSP_GAME/USRDIR/data/menu/shopp1.dds.z` 교체 목록 포함
   - 컨테이너 할당 공간 초과 없음
6. 생성 ISO 재추출 검사
   - `shopp1.dds.z`를 다시 추출해 편집 결과와 좌표 확인
   - 문구 영역 밖 미편집 블록 유지 확인
   - 원본 ISO SHA-256 유지 확인

## 산출물

- 수정 매니페스트:
  `/tools/patchdata/ys6_additional_images/manifest.json`
- 재생성 원본 조각:
  `/tools/patchdata/ys6_additional_images/source_parts/shop_confirmations/`
- 검증 결과:
  `/tools/patchdata/work/current/additional-images/`
- 테스트 ISO:
  `/patched/062-shop-confirmations-region-split-fix/`
- 결과 문서:
  `/docs/result/062-ys6-shop-confirmations-region-split-fix.md`

## 제외 범위

- `shop_confirmations.block_offset` 변경
- 구매·판매·그만두기 버튼 이미지 번역 또는 변경
- 상점 패널과 배경 디자인 변경
- 다른 추가 이미지 리소스 분할 변경
- 원본 ISO 직접 수정

## 위험 및 대응

- 기존 편집 PNG가 있으면 크기가 새 좌표와 맞지 않을 수 있다. 발견 시 덮어쓰지
  않고 이전 필요성을 먼저 보고한다.
- 문구와 배경이 같은 DXT 블록을 공유하므로 4×4 경계 안에서만 편집하고 나머지
  블록은 원본 바이트를 유지한다.

## 복구 방법

- 변경은 매니페스트, 생성 원본 조각과 별도 062 테스트 ISO에만 적용한다.
- 문제가 생기면 이전 256×84/84/88 영역 정의와 원본 조각으로 복원한다.
- 원본 ISO와 사용자 편집 이미지는 수정하지 않는다.
