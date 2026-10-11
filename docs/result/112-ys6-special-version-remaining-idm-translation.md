# 112. Ys VI SPECIAL VERSION 잔여 IDM 번역 결과

상태: 완료(2026-08-27 사용자 실기 확인)

## 수행 내용

- 잔여 일본어 IDM 2,029개 발생 위치를 827개 고유 문구로 정리했다.
- 기존 번역 534개를 재사용하고 SPECIAL VERSION 전용 문구 293개를 신규 번역·교정했다.
- 행동 설명, 일반 대사, 선택지 및 시스템 안내를 포함해 미처리 고유 문구를 0개로 만들었다.
- 111번 번역 4,127개와 잔여 번역 2,029개를 합친 6,156개 대상 위치를 적용했다.
- standalone IDM 177개와 대응 런타임 아카이브 복사본 177개를 함께 갱신했다.

## 번역 검증

- 빈 번역: 0개
- 일본어 잔존: 0개
- 개행 구조 불일치: 0개
- 대상 위치별 번역 충돌: 0개
- 인코딩 불가 문자였던 원문 기호 `③`은 의미를 유지하는 ASCII `3`으로 교정했다.

## 폰트 및 매핑

- revision 4 기존 매핑: 946개
- revision 5 신규 글리프: 18개
- 신규 문자: `꼼넓넸뇨뒀뜬몬밟삽섞엉캄털텨튕틴팠햇`
- revision 5 최종 매핑: 964개
- 최종 폰트 테이블: 2,304개
- 기존 946개 매핑의 순서·행 내용: 완전 보존
- 신규 코드 충돌: 0개
- 신규 폰트 인덱스 충돌: 0개
- BOOT/EBOOT 신규 폰트 테이블 주소: `0x360000`

### 상속된 revision 4 중복

- revision 4에는 `쩔`과 `코`가 동일 게임 코드 `0x817E`를 사용하는 기존 중복 1건이 있다.
- 112번 신규 18자와의 충돌은 없으며 기존 세이브 호환을 위한 append-only 조건에 따라 이번 작업에서는 변경하지 않았다.

## IDM 용량 검증

- standalone 할당량 초과: 0개
- 아카이브 할당량 초과: 0개
- 가장 작은 여유는 `s_4010`의 28바이트다.
- `s_4010` 최종 크기: 4,068/4,096바이트
- 그다음으로 여유가 작은 `s_3030`: 1,937/2,048바이트

## ISO 검증

- 6,156개 번역 바이트 재추출 비교: 통과
- standalone IDM 177개 재추출 비교: 통과
- 런타임 아카이브 복사본 177개 재추출 비교: 통과
- 확장 BOOT/EBOOT 재추출 비교: 통과
- BOOT extent LBA: 347,616
- EBOOT extent LBA: 348,661
- volume space size: 349,707섹터
- ISO 크기: 716,199,936바이트
- ISO SHA-256: `17653FBD597B594EC2F1D9A2C18A9E16D48D9B137125197DC4EAA10D53C14EE9`
- BOOT SHA-256: `DDB804E79DC743B8C4560AC1D14E15BB98E5304D9DD280D1BFE03CA4CC73556E`
- EBOOT SHA-256: `35CD0B0CF3FEBD4726C2695CA9675500066ED93EBE05D1D3A7ABD3CDCEA91DEB`

## 생성·변경 파일

- 번역·검증 도구: `tools/scripts/ys6_special_remaining_idm_workspace.py`
- 수동 번역 반영 도구: `tools/scripts/ys6_special_remaining_idm_overrides.py`
- 사전 검증 및 ISO 생성 도구: `tools/scripts/ys6_special_remaining_idm_preflight.py`
- 작업 자료: `tools/patchdata/work/current/112-special-version-remaining-idm-translation`
- revision 5 매핑: `tools/patchdata/work/current/112-special-version-remaining-idm-translation/hangul-mapping.json`
- 검증 보고서: `tools/patchdata/work/current/112-special-version-remaining-idm-translation/preflight-report.json`
- 시험 ISO: `patched/112-special-version-remaining-idm-translation/Ys VI Special Version - 112-remaining-idm-translation.iso`

## 사용자 실기 확인 항목

1. 초반 `s_0551` 기존 대사와 행동 보조 설명이 함께 한글로 표시되는지 확인한다.
2. 봉인의 동굴 및 SPECIAL 전용 수련 이벤트의 대사와 선택지를 확인한다.
3. 대화 색상, 들여쓰기, 줄바꿈 및 진행이 정상인지 확인한다.
4. 기존 시스템 메시지와 일반 대사가 사라지거나 깨지지 않는지 확인한다.
5. 맵 이동, 저장 및 불러오기가 정상 작동하는지 확인한다.

## 사용자 실기 확인 결과

- 2026-08-27 사용자가 112번 시험 ISO에서 색상 행동 설명을 포함한 신규 한글 출력이 정상임을 확인했다.
- 112번은 이 확인을 기준으로 완료 처리한다.
- 이후 특정 맵, 대사, 글리프 또는 진행 문제를 발견하면 본 이슈를 재개하거나 별도 회귀 수정 계획으로 처리한다.

## 알려진 사항 및 정리 대상

- revision 4에서 상속된 `0x817E` 중복은 별도 호환성 계획 없이 수정하지 않는다.
- 이번 ISO는 109번 ISO를 재현 가능한 기반으로 사용했으며 111번 ISO는 비교용으로 보존한다.
- 현재 확인되지 않은 후반부 개별 문구 문제는 발견 시 재현 위치와 함께 후속 처리한다.
