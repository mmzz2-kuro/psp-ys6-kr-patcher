# 078. Ys VI 타블라스 설명 한글 이미지 패치 결과

## 수행 내용

- 타블라스 5종, 14페이지의 일본어 원문을 전사하고 한국어로 번역했다.
- 기존 프로젝트 용어인 레다, 알마, 카난, 에멜, 에멜라스, 엘딘, 상자, 잿빛 에멜라스를 적용했다.
- 일본어 본문과 외곽선 영역을 제거하고 원본 배경 문양을 복원했다.
- Gulim Regular 17px, 흰 글자와 2px 검은 외곽선으로 한글 본문을 중앙 배치했다.
- 각 480×272 페이지를 원본과 동일한 8개 MIG 그림에 재분할했다.
- 각 MIG 그림의 DXT1 데이터 앞에 있는 16바이트 제어 데이터를 보존하는 컬렉션 전용 패치 경로를 추가했다.
- 타블라스 14개 리소스를 추가 이미지 매니페스트에 등록해 GUI의 `추가 이미지 적용` 선택에 포함했다.
- 별도 테스트 ISO 한 개를 생성했다.

## 대상 리소스

- 블루 타블라스: `p200`, `p201`
- 레드 타블라스: `p210`, `p211`, `p212`
- 골드 타블라스: `p220`, `p221`, `p222`
- 블랙 타블라스: `p230`, `p231`, `p232`
- 화이트 타블라스: `p240`, `p241`, `p242`

## 변경·생성 파일

- 변경: `tools/scripts/ys6_additional_image_patch.py`
- 변경: `tools/scripts/ys6_integrated_build.py`
- 변경: `tools/patchdata/ys6_additional_images/manifest.json`
- 추가: `tools/scripts/ys6_tabulas_localize.py`
- 추가: `tools/patchdata/ys6_additional_images/source_images/tabulas_p200.png` ~ `tabulas_p242.png`
- 추가: `tools/patchdata/ys6_additional_images/source_parts/tabulas_p*/page.png`
- 추가: `tools/patchdata/ys6_additional_images/edited_parts/tabulas_p*/page.png`
- 생성: `tools/patchdata/ys6_additional_images/tabulas_p*-preview.png`
- 생성: `tools/patchdata/ys6_additional_images/tabulas_p*-background-preview.png`
- 생성: `tools/patchdata/ys6_additional_images/tabulas-localize-report.json`
- 번역표: `tools/patchdata/work/current/image-discovery/tabulas/translation-table.md`

## 검증 결과

- Python 구문 검사: 성공
- 추가 이미지 매니페스트 JSON 검사: 성공
- 추가 이미지 입력 검사: 성공, 전체 수정 이미지 66개 중 타블라스 14개 인식
- GUI 공통 빌더 사전검증: 성공
- 타블라스 적용 리소스: 14개
- 타블라스 내부 MIG 그림: 112개
- 전체 추가 이미지 리소스: 27개
- 전체 추가 이미지 런타임 복제본: 49/49 교체 성공
- 할당 공간 초과: 없음
- ISO 내부 타블라스 컨테이너 14개가 빌드 작업본과 바이트 단위로 일치
- ISO 내부 컨테이너 14개 압축 해제 성공
- ISO 내부 이미지 14개 모두 480×272 재렌더 성공

### 타블라스 컨테이너 여유 공간

| 파일 | 패치 컨테이너 | 할당 공간 | 잔여 공간 |
|---|---:|---:|---:|
| `p200` | 46,366 | 53,248 | 6,882 |
| `p201` | 45,787 | 53,248 | 7,461 |
| `p210` | 47,761 | 53,248 | 5,487 |
| `p211` | 46,925 | 51,200 | 4,275 |
| `p212` | 46,446 | 51,200 | 4,754 |
| `p220` | 47,672 | 53,248 | 5,576 |
| `p221` | 46,428 | 53,248 | 6,820 |
| `p222` | 48,474 | 53,248 | 4,774 |
| `p230` | 41,643 | 47,104 | 5,461 |
| `p231` | 41,337 | 47,104 | 5,767 |
| `p232` | 41,247 | 47,104 | 5,857 |
| `p240` | 46,772 | 53,248 | 6,476 |
| `p241` | 47,827 | 51,200 | 3,373 |
| `p242` | 46,587 | 51,200 | 4,613 |

## 테스트 ISO

- 경로: `patched/078-ys6-tabulas-description-korean-image-patch/Ys VI (Japan) - 078-tabulas-korean-test.iso`
- 크기: 866,254,848바이트
- SHA-256: `ED79D5E88E2373050E248142DDDF97375081ADC0E5468CE45F020FA002B853BC`
- 용도: 타블라스 14페이지 인게임 표시 확인
- 작업 완료 후 불필요하면 삭제 가능한 테스트 ROM이다.

## 알려진 사항

- 정적 재렌더와 ISO 내부 검증은 완료했다. 실제 게임에서 페이지 전환, 글자 가독성 및 화면 가장자리 표시 여부는 사용자 인게임 확인이 필요하다.
- 일본어 제거 영역은 글자 마스크 기반으로 주변 배경을 복원했으며, 원본 배경 전체를 새로 생성하거나 블러 처리하지 않았다.
