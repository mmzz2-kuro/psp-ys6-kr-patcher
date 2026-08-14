# 047. 아이템·몬스터명 GUI 편집 및 통합 패치 결과

> 정정: 이 문서의 최초 구현은 이름 영역을 52바이트로 잘못 처리해 가격·능력치 일부를 0으로 지우는 문제가 있었다. 048에서 이름 32바이트, 메타데이터 44바이트로 수정하고 전수 검증했다. 최종 구현 상태는 `docs/result/048-ys6-invinfo-price-field-boundary-fix.md`를 따른다.

## 결과

기존 `tools/ys6_dialogue_viewer.py`에 `아이템` 탭을 추가하고, 기존 인물명 탭을 `인물·몬스터명`으로 확장했다. 아이템 이름·설명은 사용자가 `override`로 승인한 항목만 통합 패치 빌드에 반영된다. 몬스터명은 기존 `castinfo.dat`의 `CAST_Mxxx` 레코드를 별도 필터로 보여 주며 `reviewed` 항목만 기존 이름 패치 흐름에 반영된다.

새 ISO는 생성하지 않았다.

## 아이템 작업공간

- 파일: `tools/config/item-translations.json`
- 레코드: 73개
- 현재 상태: draft 73개, override 0개
- 초깃값: Windows 한글판 이름·설명
- 자동 패치: 하지 않음

Windows판 인용부호 코드 `97D7`, `97D8`은 의미가 확인된 `「`, `」`로 정규화했다. 두 글자는 통합 폰트 매핑 수집 대상에 포함된다.

각 레코드는 다음 정보를 보존한다.

- 인덱스와 리소스 ID
- 일본어 이름·설명
- 한국어 이름·설명
- 원본 레코드 SHA-256
- 상태와 메모

## GUI 변경

### 아이템 탭

- 73개 아이템 목록
- ID·일본어·한국어·설명·메모 통합 검색
- 상태 필터
- 한국어 이름 및 여러 줄 설명 편집
- 다중 선택 `override` 전환
- 인코딩 후 이름/설명 바이트 길이 표시
- 저장 전 구조·상태·NUL·고정 영역 길이 검증
- 기본 실행 시 `tools/config/item-translations.json` 자동 로드

### 인물·몬스터명 탭

- 기존 인물명 탭 이름 변경
- `전체 / 인물 / 몬스터` 필터 추가
- `CAST_Mxxx` 76개를 몬스터로 분류
- 다중 선택 `reviewed` 전환 추가
- 몬스터 전체 수와 reviewed 수 표시

현재 실제 작업공간의 몬스터 상태는 76개 중 reviewed 0개다. 기존 번역이 입력된 몬스터 11개도 자동 승인하지 않았다.

## 패치 구현

### `invinfo.dat`

추가된 `ys6_invinfo.py`가 다음 조건을 강제한다.

- 전체 크기 13,448바이트
- 헤더 16바이트
- 184바이트 × 73레코드
- 이름 영역 52바이트
- 메타데이터 24바이트
- 설명 영역 108바이트
- 이름과 설명은 NUL 종단 후 남은 영역을 0으로 채움
- 미선택 레코드 원본 유지
- 24바이트 메타데이터 원본 유지

통합 빌더는 다음 두 위치를 함께 수정한다.

- `PSP_GAME/USRDIR/data/misc/invinfo.dat`
- `PSP_GAME/USRDIR/data/arc/init.bin`의 인덱스 10 `invinfo.dat`

두 원본이 서로 다르거나 작업공간 원본 SHA-256과 다르면 빌드를 중단한다.

### 폰트

아이템 override 이름·설명 및 몬스터 reviewed 이름을 EBOOT 글리프 수집 대상에 포함했다. 아이템 설명 줄바꿈은 저장 시 LF, 게임 삽입 시 CRLF로 변환한다.

### 빌드 화면

다음 수량을 표시하도록 변경했다.

- 대사 override
- 아이템 override / draft
- 인물 reviewed
- 몬스터 reviewed

빌드 결과에는 `item-report.csv`와 manifest의 `items` 항목이 추가된다.

## 검증 결과

### 기본 작업공간

- 대사 override: 4,665개
- 아이템 override: 0개
- 아이템 draft: 73개
- 인물 reviewed: 58개
- 몬스터 reviewed: 0개
- 통합 preflight: 통과
- 기본 상태 item patch 수: 0개

### 아이템 한 개 역테스트

임시 작업공간에서 인덱스 0 `리발트`만 override했다.

- 통합 preflight: 통과
- item patch 수: 1개
- 변경 레코드: 0번만 변경
- 결과 크기: 13,448바이트
- 73개 메타데이터: 전부 원본과 동일
- 독립 `invinfo.dat`와 `init.bin` 내부 결과: 바이트 단위 동일

### 아이템 73개 전체 역테스트

임시 작업공간에서 73개를 전부 override했다.

- 통합 preflight: 통과
- item patch 수: 73개
- 고정 이름 영역 초과: 0개
- 고정 설명 영역 초과: 0개
- 필요한 전체 글리프 매핑: 967개

실제 `tools/config/item-translations.json`의 상태는 변경하지 않고 draft 73개로 유지했다.

### 잘못된 입력 역테스트

- 52바이트 이름 + NUL: 길이 초과로 거부
- 108바이트 설명 + NUL: 길이 초과로 거부
- 이름 내부 NUL: 거부

### 몬스터 역테스트

임시 작업공간에서 `CAST_M450 / ブラックアドル / 블랙아돌` 한 개만 reviewed로 지정했다.

- 통합 preflight: 통과
- castinfo patch 수: 기존 58개에서 59개로 증가
- 실제 `cast-names.json`의 몬스터 상태는 변경하지 않음

### 코드 검증

- 변경 Python 파일 `py_compile` 통과
- `git diff --check` 통과
- GUI 모듈 import 및 네 개 기본 설정 경로 확인

## 함께 수정한 기존 대사 검증 정보

기본 preflight 과정에서 대사 레코드 1012가 `\x1` 플레이어명 토큰을 고정 이름 `아돌`로 바꿨지만 `allow_player_name_expansion` 표시가 없어 검증에 실패하는 상태를 발견했다.

이 프로젝트에서 이미 정한 “플레이어 명칭은 아돌로 고정” 규칙에 맞춰 해당 레코드에 `allow_player_name_expansion: true`를 추가했다. 번역 문구와 override 상태는 변경하지 않았다.

## 추가·변경 파일

### 추가

- `tools/config/item-translations.json`
- `tools/scripts/ys6_invinfo.py`
- `tools/scripts/ys6_item_workspace.py`
- `tools/patchdata/original-invinfo.dat`
- `tools/patchdata/windows-korean-invinfo.dat`
- `docs/result/047-ys6-item-and-monster-editor-build.md`

### 변경

- `tools/ys6_dialogue_viewer.py`
- `tools/scripts/ys6_patch_builder.py`
- `tools/scripts/ys6_integrated_build.py`
- `tools/patchdata/build-config.json`
- `tools/config/dialogue-translations.json`
- `docs/plan/047-ys6-item-and-monster-editor-build.md`

`tools/patchdata`는 저장소의 기존 `.gitignore` 정책에 따라 Git 비추적 영역이지만, 로컬 사용자 빌드에는 배치되어 있고 `build-config.json`의 SHA-256 검증을 받는다.

## 사용 방법

1. `python tools/ys6_dialogue_viewer.py` 실행
2. `아이템` 탭에서 번역 확인·교정
3. 적용할 항목을 선택하고 `선택 항목 override`
4. 저장
5. 필요하면 `인물·몬스터명` 탭에서 `몬스터` 필터 선택
6. 번역된 몬스터를 선택하고 `선택 항목 reviewed`
7. 저장
8. `패치 빌드` 탭에서 사전 검증 후 ISO 생성

## 임시 파일

- `.work/ys6-item-test/`
  - 단일 아이템, 전체 아이템 및 몬스터 reviewed 사전 검증 결과
  - 새 ISO는 포함하지 않음
  - 재현 자료이므로 현재 유지
