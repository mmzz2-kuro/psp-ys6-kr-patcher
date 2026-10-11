# 116. Ys VI SPECIAL VERSION 인물·몬스터명 및 아이템 이식 결과

상태: 완료 / 실기 확인 대기

## 수행 결과

- SPECIAL VERSION에 인물·몬스터명 70개와 안전 대응 아이템 72개를 이식했다.
- 검토가 필요한 `ky_09`와 SPECIAL 전용 아이템 4개는 원본 레코드 전체를 보존했다.
- 독립 `castinfo.dat.z`, `invinfo.dat.z`와 `init.bin` 내부 런타임 복사본을 함께 교체했다.
- GUI와 공용 빌더가 revision 7, 인물·몬스터 70개, 아이템 72개, 검토 제외 5개를 표시하고 동일한 빌드 경로를 사용하도록 반영했다.

## SPECIAL 전용 작업공간

- 파일: `tools/patchdata/ys6_special_version/cast-item-translations.json`
- 인물·몬스터 적용: 70개
- 아이템 적용: 72개
- 아이템 제외: 5개
- 각 적용 행은 SPECIAL 원문, 대상 식별자·아이템 ID, 원본 필드 또는 레코드 해시, 번역과 대응 방법을 보존한다.

### 원문 기준 재대응

- SPECIAL `CAST_M720` 원문 `ユエ`에 `유에` 적용
- SPECIAL `CAST_M730` 원문 `セラ`에 `세라` 적용
- 동일 원문을 공유하는 인물 레코드는 번역 충돌이 없는지 검사한 뒤 같은 번역을 사용한다.

## 아이템 적용

- SPECIAL 내부 구조: 헤더 16바이트, 184바이트 × 77개
- 필드: 이름 32바이트, 메타데이터 44바이트, 설명 108바이트
- 적용 72개 이름·설명 공간 초과: 0개
- 메타데이터 변경: 0개
- 미선택 레코드 변경: 0개
- 설명 줄바꿈은 LF에서 CRLF로 변환했다.
- 한국어 번역에서 사용 중인 원문 인용부호 `「`, `」`를 기존 CP932 글리프로 보존할 수 있도록 공용 인코더의 허용 문장부호에 추가했다.

### 보존한 아이템

- `ky_09` 알마의 날개: 설명 검토 필요
- `ky_20`, `ky_21`, `ky_22`, `ky_23`: SPECIAL 전용 신규 번역 필요

## revision 7 글리프

- revision 6의 기존 964개 행을 순서·코드·폰트 인덱스까지 유지했다.
- 신규 11자를 append했다.
  - `랴`, `쉐`, `겸`, `듬`, `똬`, `롱`, `링`, `벅`, `볍`, `뿜`, `클`
- 신규 코드: `0xF2DC`~`0xF2E6`
- 신규 폰트 인덱스: 2305~2315
- 최종 매핑: revision 7, 975자
- 최종 폰트 테이블: 2,316개
- 문자·게임 코드·폰트 인덱스 중복: 0개
- 기존 `코=0x817E`, `쩔=0xF2DB` 유지

## 압축 및 할당 공간

| 대상 | 출력 크기 | 할당 크기 |
|---|---:|---:|
| 독립 `castinfo.dat.z` | 3,524 | 4,096 |
| `init.bin`의 `castinfo.dat.z` | 3,524 | 4,096 |
| 독립 `invinfo.dat.z` | 4,325 | 6,144 |
| `init.bin`의 `invinfo.dat.z` | 4,325 | 6,144 |

- 할당량 초과: 0개
- 독립 압축 파일과 `init.bin` 런타임 payload: 각각 일치
- 비대상 `init.bin` 엔트리와 아카이브 구조: 보존

## GUI 및 빌더

- SPECIAL 프로필 상태 표시:
  - IDM 적용 6,156개
  - 인물·몬스터 70개
  - 아이템 72개
  - 아이템 검토 제외 5개
  - 글리프 revision 7, 975자
- GUI `사전 검증`과 `패치 ISO 만들기`는 같은 SPECIAL 전용 작업공간과 압축 결과를 사용한다.
- 배포 구성은 `cast-item-translations.json`과 revision 7 매핑의 SHA-256을 검증한다.

## 검증 결과

- Python 구문 검사: 통과
- SPECIAL GUI 공용 빌더 inspect: 통과
- SPECIAL 전체 사전 검증: 통과
- 기존 IDM 번역 6,156개 재추출: 통과
- IDM 런타임 복사본 177개 재추출: 통과
- 인물·몬스터 인코딩 70개: 일치
- 아이템 이름·설명 인코딩 72개: 일치
- 제외 아이템 원본 레코드 5개: 일치
- 독립/런타임 payload 쌍 2개: 일치
- 신규 글리프 11개 코드·인덱스·비트맵: 일치
- BOOT/EBOOT 신규 extent 재추출: 일치
- 일반판 전체 사전 검증 회귀: 통과
- 변경 파일 공백 검사: 오류 없음

## 생성·변경 파일

- `tools/patchdata/ys6_special_version/cast-item-translations.json`
- `tools/patchdata/ys6_special_version/hangul-mapping.json`
- `tools/patchdata/ys6_special_version/build-config.json`
- `tools/scripts/ys6_special_cast_item.py`
- `tools/scripts/ys6_special_cast_item_audit.py`
- `tools/scripts/ys6_special_remaining_idm_preflight.py`
- `tools/scripts/ys6_special_patch_builder.py`
- `tools/scripts/ys6_hangul_codec.py`
- `tools/ys6_dialogue_viewer.py`
- `tools/patchdata/work/current/116-ys6-special-version-cast-item-port/preflight-report.json`
- `tools/patchdata/work/current/116-ys6-special-version-cast-item-port/cast-item-audit.json`
- `tools/patchdata/work/current/116-ys6-special-version-cast-item-port/new-glyph-atlas.png`

## 테스트 ISO

- 경로: `patched/116-ys6-special-version-cast-item-port/Ys VI Special Version - 116-cast-item-port.iso`
- 크기: 716,201,984바이트
- SHA-256: `0C2940ACBA0B99A2CFBFF2E02277F15CAE492E8B4932EC880575997C45AEAB14`
- 원본 SPECIAL VERSION ISO는 변경하지 않았다.
- 실기 확인 후 불필요하면 삭제할 수 있는 작업본이다.

## 실기 확인 항목

1. 장비·아이템 화면에서 기존 72개 아이템명과 설명이 한글로 표시되는지 확인한다.
2. `ky_09`와 SPECIAL 전용 아이템은 일본어 원본 상태인지 확인한다.
3. NPC 이름 및 확인 가능한 몬스터 이름이 한글로 표시되는지 확인한다.
4. `유에`, `세라`가 서로 바뀌지 않았는지 확인한다.
5. 아이템 가격·능력치, 장비 효과와 게임 진행이 정상인지 확인한다.
