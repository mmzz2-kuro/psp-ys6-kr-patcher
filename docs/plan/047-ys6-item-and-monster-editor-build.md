# 047. 아이템·몬스터명 GUI 편집 및 통합 패치 계획

## 목적

PSP판 이스 6의 아이템·장비 이름과 설명을 기존 사용자용 GUI에서 검토·편집하고, 승인된 항목만 현재 한글 패치 ISO 빌드에 함께 반영한다.

몬스터 관련 데이터도 표시 문자열이 확인된 범위에서 같은 GUI와 빌드 흐름에 포함한다.

## 확인된 대상

### 아이템·장비

- ISO 경로: `PSP_GAME/USRDIR/data/misc/invinfo.dat`
- 크기: 13,448바이트
- 레코드: 184바이트 × 73개
- 이름 영역: 레코드 상대 위치 `0x00..0x33` (52바이트)
- 비문자 메타데이터: `0x34..0x4B` (24바이트)
- 설명 영역: `0x4C..0xB7` (108바이트)
- PSP판과 Windows 한글판의 73개 메타데이터가 전부 일치한다.
- Windows 한글판 이름·설명 73개를 초깃값으로 재사용할 수 있다.

### 몬스터

- `enemyinfo.dat`: 264바이트 × 70개 레코드의 전투 수치 중심 데이터이며 표시 이름 문자열은 확인되지 않았다.
- 실제 몬스터 이름 후보는 `castinfo.dat`와 기존 `tools/config/cast-names.json`의 `CAST_Mxxx` 레코드다.
- 현재 `CAST_Mxxx` 레코드는 76개이며, 번역이 입력된 항목은 11개, `reviewed` 항목은 0개다.
- 몬스터 능력치 자체는 번역 대상이 아니므로 수정하지 않는다.

## 사용자 작업 흐름

### 아이템

1. GUI의 `아이템` 탭에서 일본어 이름·설명과 Windows 한글판 초깃값을 확인한다.
2. 사용자가 한국어 이름·설명을 교정한다.
3. 상태를 `override`로 바꾼 항목만 패치에 반영한다.
4. 여러 항목을 선택하여 한 번에 `override`로 전환할 수 있게 한다.

### 몬스터명

1. 기존 `인물명` 탭을 `인물·몬스터명` 탭으로 확장한다.
2. `전체 / 인물 / 몬스터` 필터를 제공한다.
3. `CAST_Mxxx`를 몬스터로 분류하고 기존 편집·검색·상태 변경 기능을 그대로 사용한다.
4. 기존 규칙대로 `reviewed` 상태의 이름만 패치에 반영한다.

아이템은 대사 작업 흐름과 맞춰 `untranslated`, `draft`, `override`, `excluded`, `conflict` 상태를 사용한다. Windows판에서 가져온 번역은 자동 승인하지 않고 `draft`로 시작한다.

## 데이터 배치

- 사용자 편집 JSON: `/tools/config/item-translations.json`
- 재현 가능한 원본·참조 데이터: `/tools/patchdata/`
- GUI: 기존 `/tools/ys6_dialogue_viewer.py`에 아이템 탭 추가
- 비GUI 파서·검증·패처: `/tools/scripts`

`.work`의 조사 파일을 GUI가 직접 참조하지 않게 한다. 필요한 원본 해시, Windows 대응 번역 및 구조 정보는 `tools/config`와 `tools/patchdata`에 정식 배치한다.

## 구현 범위

### 1. 아이템 작업공간

다음 필드를 가진 JSON 작업공간을 생성한다.

- `index`
- `resource_id`
- `source_name`
- `source_description`
- `translation_name`
- `translation_description`
- `status`
- `notes`
- 원본 필드 바이트와 SHA-256 등 무결성 정보

Windows판 번역 73개를 `draft`로 채운다. 미해결 코드 `97D7`, `97D8`은 지원 가능한 인용부호 후보로 정규화하되, 원래 코드와 치환 내역을 notes 또는 생성 보고서에 남긴다.

### 2. 아이템 GUI 탭

- ID, 일본어 이름, 한국어 이름, 상태를 표로 표시
- 일본어·한국어 설명을 여러 줄 편집기로 표시
- 이름·설명·ID·상태 통합 검색
- 상태 필터
- 다중 선택 `override` 전환
- 선택 항목 저장 및 전체 JSON 저장
- 고정 바이트 영역 초과를 편집 시점과 저장 시점에 표시
- 미지원 문자 및 NUL 문자 오류 표시

### 3. 몬스터 GUI 정리

- 탭 이름을 `인물·몬스터명`으로 변경
- `CAST_Mxxx` 기준 몬스터 필터 추가
- 전체/인물/몬스터별 개수와 reviewed 개수 표시
- 다중 선택 reviewed 전환이 기존 탭에 없다면 추가
- 기존 인물명 JSON 형식과 번역은 보존

### 4. 아이템 인코딩·검증

- 현재 한글 글리프 매핑을 사용해 한국어를 게임 바이트로 인코딩한다.
- 이름은 첫 NUL을 포함해 52바이트 이내, 설명은 첫 NUL을 포함해 108바이트 이내인지 검증한다.
- 줄바꿈은 게임 원본 형식인 CRLF로 정규화한다.
- 첫 NUL 이후 영역은 0으로 채워 Windows판에 남아 있던 일본어 잔여 바이트를 제거한다.
- ID·가격·능력치 등 24바이트 메타데이터가 변경되지 않았는지 검증한다.
- `override`가 아닌 항목은 PSP 원본 바이트를 그대로 유지한다.

### 5. 런타임 위치 및 패치

- 독립 `data/misc/invinfo.dat`와 `data/arc/init.bin` 내부 복사본을 비교한다.
- 두 복사본이 같고 런타임 후보라면 기존 `castinfo.dat` 처리와 같은 방식으로 동시에 패치한다.
- 아카이브 엔트리의 인덱스·플래그·할당 크기를 기록한다.
- 원본 SHA-256과 레코드 구조가 예상과 다르면 빌드를 중단한다.
- 파일 크기는 13,448바이트로 유지한다.

### 6. 통합 빌더 확장

- 아이템 `override` 이름·설명과 몬스터 `reviewed` 이름의 한글을 폰트 글리프 수집 대상에 포함한다.
- 패치 빌드 탭에 다음 개수를 표시한다.
  - 대사 override
  - 아이템 override / draft
  - 인물 reviewed
  - 몬스터 reviewed
- preflight와 ISO 빌드가 대사, 인물·몬스터명, 아이템을 한 번에 처리한다.
- 빌드 보고서에 아이템별 원문·번역·인코딩 길이·수정 위치를 기록한다.

## 예정 파일

### 추가

- `/tools/config/item-translations.json`
- `/tools/scripts/ys6_invinfo.py`
- `/tools/scripts/ys6_item_workspace.py`

### 변경

- `/tools/ys6_dialogue_viewer.py`
- `/tools/scripts/ys6_patch_builder.py`
- `/tools/scripts/ys6_integrated_build.py`
- 필요 시 `/tools/config/cast-names.json`
- 필요 시 `/tools/patchdata/build-config.json`

분석용 `ys6_invinfo_inventory.py`는 비교·추출 용도로 유지하고, 실제 빌드용 파싱과 수정은 엄격한 검증을 포함한 별도 모듈로 분리한다.

## 검증 계획

1. 작업공간 73개 레코드와 PSP 원본 인덱스·ID가 일치하는지 확인한다.
2. Windows 한글판 초깃값 73개와 미해결 문자 수를 확인한다.
3. 모든 draft를 그대로 둔 preflight에서 아이템 수정 수가 0인지 확인한다.
4. 시험 항목 하나만 override하여 이름·설명 필드 외 변경이 없는지 확인한다.
5. 길이 초과, 미지원 문자, NUL 입력을 의도적으로 넣어 빌드가 중단되는지 역테스트한다.
6. `invinfo.dat` 독립 파일과 `init.bin` 내부 복사본이 동일하게 수정되는지 확인한다.
7. 몬스터 필터에 `CAST_Mxxx` 76개가 표시되는지 확인한다.
8. 몬스터 이름 하나를 reviewed로 만든 시험에서 기존 castinfo 패치 경로로 반영되는지 확인한다.
9. 결과 `invinfo.dat`의 크기와 73개 메타데이터가 원본과 동일한지 확인한다.
10. 통합 preflight를 통과한다.
11. GUI 시작과 JSON 기본 로딩을 확인한다.

## 완료 조건

- GUI에서 73개 아이템 이름·설명을 검색·편집·저장할 수 있다.
- 다중 선택 override 전환이 가능하다.
- Windows 한글판 번역은 draft로 제공되고 자동 패치되지 않는다.
- override 아이템만 패치 빌드에 반영된다.
- 몬스터 76개를 기존 인물과 구분해 편집할 수 있다.
- reviewed 몬스터명은 기존 castinfo 패치 흐름에 반영된다.
- 비문자 메타데이터와 파일 크기는 변하지 않는다.
- 원본 ISO는 수정되지 않고 결과 ISO만 `/patched` 아래에 생성할 수 있다.
- 구현 및 검증 결과가 `/docs/result`에 작성된다.

## 제외 및 보류

- `enemyinfo.dat`의 HP·공격력·AI 등 게임 밸런스 수치 수정
- 아직 식별되지 않은 시스템 메시지
- MIG 이미지 편집과 삽입
- 모든 draft 아이템의 자동 override 전환
- 사용자 확인 없이 새 ISO 생성

## ROM 처리

- 원본 ISO를 직접 수정하지 않는다.
- 구현 검증은 우선 preflight와 추출 파일 비교로 수행한다.
- 실제 ISO 생성은 사용자가 별도로 요청하거나 GUI에서 직접 빌드할 때 `/patched` 아래에 둔다.
- 불필요한 테스트 ISO는 생성하지 않는다.

## 상태

- 사용자 확인 완료
- 구현 및 사전 검증 완료
- 결과: `/docs/result/047-ys6-item-and-monster-editor-build.md`
