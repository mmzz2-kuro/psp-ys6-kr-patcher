# 111. Ys VI SPECIAL VERSION 전체 대응 IDM 대사 이식 결과

상태: 전체 시험 ISO 생성 완료 / 사용자 실기 확인 대기

## 수행 내용

- 109번에서 확정한 IDM 대응 4,127개를 최신 `tools/config/dialogue-translations.json`과 다시 동기화했다.
- 사용자가 이후 수정한 번역 13개를 감지해 최신 문장으로 반영했다.
- mapping revision 3의 기존 434개 행을 순서·코드·폰트 인덱스까지 그대로 보존했다.
- 남은 신규 한글 512자를 사용자 정의 Shift-JIS 코드와 확장 폰트 인덱스에 append했다.
- 110번 실기 검증 방식으로 BOOT/EBOOT의 폰트 테이블을 1,774개에서 2,286개로 확장했다.
- 번역 대상 IDM 131개와 대응하는 런타임 아카이브 복사본 131개를 함께 갱신했다.
- 확장 BOOT/EBOOT은 기반 ISO의 기존 파일을 건드리지 않고 ISO 끝의 신규 extent에 배치했다.

## 매핑 및 폰트 결과

- 기반 매핑: revision 3, 434자
- 신규 확장 글리프: 512자
- 최종 매핑: revision 4, 946자
- 기반 실제 폰트 테이블: 1,774개
- 최종 폰트 테이블: 2,286개
- 확장 테이블 크기: 68,580바이트
- 신규 가상 주소: `0x360000`
- 신규 코드 및 폰트 인덱스 중복: 0건
- 원본 IDM의 신규 코드 충돌: 0건
- 기존 매핑 434개 선두 비교: 완전 일치

## IDM 적용 결과

- 대응 확정 번역: 4,127개
- 수정 IDM: 131개
- 수정 런타임 복사본: 131개
- 수정 아카이브: 131개
- standalone 할당량 초과: 0개
- 아카이브 할당량 초과: 0개
- 최소 남은 할당 여유: 9바이트
- 모호 대응 282개, 미대응 665개, 번역 충돌 7개는 계획대로 제외했다.

### `s_4010` 처리

- 사용자가 관련 번역 13개를 축약·교정했다.
- 최종 IDM 크기: 4,087바이트
- standalone 및 아카이브 할당량: 4,096바이트
- 남은 여유: 9바이트
- 번역 축약으로 기존 할당량에 들어가므로 아카이브 구조 확장이나 신규 extent 이전은 수행하지 않았다.

## 기존 109번 회귀 검증

- 109번에서 먼저 적용한 번역: 1,650개
- 사용자 수정 대상: 4개
- 사용자 수정 없이 기존 바이트가 그대로 유지된 번역: 1,646개
- 예상하지 않은 변경: 0개

## 실행 파일 검증

- BOOT/EBOOT 프로그램 헤더 순서: `PT_LOAD`, `PT_LOAD`, 신규 `PT_LOAD`, PSP relocation
- 여섯 폰트 주소 재배치 target segment: index 2
- 재배치 후 세 폰트 테이블 주소: 모두 `0x360000`
- 세 검색 경로 상한: 모두 2,286
- 기존 1,774개 폰트 레코드: 신규 테이블 선두에서 바이트 단위 유지
- 신규 글리프 공백 또는 16×14 셀 초과: 0개

## ISO 검증

- 4,127개 번역 인코딩 재추출 비교: 통과
- 독립 IDM 131개 재추출 비교: 통과
- 런타임 아카이브 복사본 131개 재추출 비교: 통과
- 아카이브 엔트리 offset 및 할당 구조 보존: 통과
- 확장 BOOT/EBOOT 재추출 비교: 통과
- 신규 BOOT extent LBA: 347,616
- 신규 EBOOT extent LBA: 348,661
- volume space size: 349,706섹터
- 테스트 ISO 크기: 716,197,888바이트
- 테스트 ISO SHA-256: `E6D657D6BCF15BE692F2F8E6627DFDA656C62BA83C9E0EB68E928E27A010BD3F`
- 확장 BOOT SHA-256: `A92A4216C0BD59F18973E7A1F3EA0FB35070ADCD6F21BD9C9475E709BA451CE6`
- 확장 EBOOT SHA-256: `5679C01A5CB232EE721BC71A5D8654F24835ED83A38B11415008196344944C46`

## 생성·변경 파일

- 전체 빌드 도구: `tools/scripts/ys6_special_full_idm_build.py`
- 확장 폰트 도구 보강: `tools/scripts/ys6_special_font_expand.py`
- 작업 자료: `tools/patchdata/work/current/111-special-version-full-idm-dialogue-port`
- 최종 매핑: `tools/patchdata/work/current/111-special-version-full-idm-dialogue-port/hangul-mapping.json`
- 적용 번역 목록: `tools/patchdata/work/current/111-special-version-full-idm-dialogue-port/full-resolved-translations.json`
- 글리프 아틀라스: `tools/patchdata/work/current/111-special-version-full-idm-dialogue-port/expanded-glyph-atlas.png`
- 빌드 보고서: `tools/patchdata/work/current/111-special-version-full-idm-dialogue-port/build-report.json`
- 시험 ISO: `patched/111-special-version-full-idm-dialogue-port/Ys VI Special Version - 111-full-idm-dialogue-port.iso`

## 사용자 실기 확인 항목

1. ISO가 정상 부팅되고 시스템 메시지와 대화 글자가 표시되는지 확인한다.
2. 초반 `s_0551` 대사에서 기존 매핑 글자가 유지되는지 확인한다.
3. 109번에서 보류되었던 대사에서 신규 확장 글자가 표시되는지 확인한다.
4. `s_4010` 지역 대화가 정상 출력되고 대화 진행이 멈추지 않는지 확인한다.
5. 맵 이동, 저장 및 불러오기가 정상 동작하는지 확인한다.

## 알려진 사항 및 정리 대상

- 이번 ISO는 대응이 확정된 IDM 대사 전체 시험본이며 모호·미대응·충돌 항목은 포함하지 않는다.
- 인물·몬스터명, 아이템, 별도 시스템 메시지, 이미지, 영상, XMB 및 아날로그 스틱 이식은 포함하지 않는다.
- 사용자 실기 확인 전까지 111번을 최종 완료로 확정하지 않는다.
- 110번의 1차 실패 ISO와 최소 증명 ISO는 111번 결과에 포함되지 않으며, 확인 후 불필요하면 삭제할 수 있다.
