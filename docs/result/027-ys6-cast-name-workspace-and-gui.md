# Ys VI 인물명 작업공간 및 GUI 편집 기능 결과

## 상태

- 작업 번호: 027
- 구현: 완료
- 정적 검증: 완료
- GUI 코드 및 저장 로직 검증: 완료
- 사용자 GUI 조작 확인: 대기
- 인게임 회귀: 026과 바이트 동일 결과로 확인
- 완료일: 2026-08-13

## 결과 요약

`castinfo.dat`의 인물명 164개를 별도 JSON·CSV 작업공간으로 추출하고 기존 대사 GUI에 `인물명` 탭을 추가했다. GUI에서 ID·일본어 원문·한국어 번역·상태·메모·오프셋·원문 HEX·SHA를 확인하고 검색, 필터, 검증, 원자적 저장 및 CSV 내보내기를 할 수 있다.

통합 빌더는 `--cast-name-workspace`를 받아 `reviewed` 인물명만 적용하고, 번역에 필요한 한글 글리프를 대사 글리프 매핑과 함께 생성한다. standalone `castinfo.dat`와 `init.bin` 내부 사본은 자동으로 같은 결과로 수정된다.

## 작업공간

- JSON: `/.work/ys6-translation-workspace/cast-names.json`
- CSV: `/.work/ys6-translation-workspace/cast-names.csv`
- 전체 레코드: 164개
- identifier: 164개, 중복 없음
- 초기 reviewed: 1개
  - `CAST_C240`: `イーシャ` → `이샤`
  - 메모: 026 PPSSPP 인게임 출력 확인 완료

동기화 시 32바이트 원문 필드 SHA가 같으면 번역·상태·메모를 유지하고, 달라지면 `conflict`로 전환한다. reviewed 빈 번역, NUL, 잘못된 상태, 원문 SHA 오류, 필드 길이 초과를 차단한다.

## GUI

수정한 사용자용 도구:

- `/tools/ys6_dialogue_viewer.py`

기존 대사 화면을 `대사` 탭으로 유지하고 `인물명` 탭을 추가했다. 인물명 탭은 작업공간만 편집하며 ISO나 `castinfo.dat`를 직접 수정하지 않는다. 저장 시 전체 검증 후 UTF-8 JSON을 임시 파일에 기록하고 원자적으로 교체하며 기존 파일을 `.bak`으로 백업한다.

## 빌더 연동

추가 인자:

```text
--cast-name-workspace <cast-names.json>
```

기존 `--castinfo-name`은 회귀 호환을 위해 유지했다. 두 인자를 함께 지정하면 빌드를 중단한다. 빌드 보고서에는 레코드별 identifier, 원문, 번역, 인코딩 HEX, 변경 바이트와 전후 SHA가 기록된다.

## 검증 결과

- Python 컴파일 통과
- 자동 테스트 87개 통과
- `python tools/ys6_dialogue_viewer.py` 직접 실행 import 경로 검증 통과
- JSON 레코드 164개와 CSV 행 164개 일치
- identifier 고유성 확인
- standalone과 `init.bin` 내부 수정 사본 동일
- 새 작업공간 방식 `castinfo.dat` SHA-256:
  - `89FA96CB785AAC59B55E2179C5DA0EFFF548025A3C65697DF04CCDE414AD3572`
- 026 수정 `castinfo.dat`와 바이트 단위 동일
- 027 ISO SHA-256:
  - `92BDAC735A0271BF013E86AAB2EA57659D9563D43910F1C1AC8E4C7AB7FDFF94`
- 026 최종 ISO와 바이트 단위 동일
- 원본 ISO SHA-256 유지:
  - `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`

027 ISO가 사용자가 이미 PPSSPP에서 이샤 인물명과 이벤트 진행을 확인한 026 ISO와 완전히 동일하므로 인게임 회귀가 없음을 확인했다.

## 생성·변경 파일

- 추가: `/tools/scripts/ys6_cast_name_workspace.py`
- 추가: `/tools/scripts/tests/test_ys6_cast_name_workspace.py`
- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정: `/tools/scripts/ys6_integrated_build.py`
- 생성: `/.work/ys6-translation-workspace/cast-names.json`
- 생성: `/.work/ys6-translation-workspace/cast-names.csv`
- 생성: `/.work/ys6-cast-name-workspace`
- 생성: `/patched/027-cast-name-workspace/Ys VI - cast-name-workspace-korean-build.iso`

## 사용 방법

1. `python tools/ys6_dialogue_viewer.py`를 실행한다.
2. `인물명` 탭을 선택한다.
3. `작업공간 열기`에서 `/.work/ys6-translation-workspace/cast-names.json`을 연다.
4. 번역과 상태를 입력하고 적용한다.
5. 빌드에 넣을 이름은 상태를 `reviewed`로 지정한다.
6. `검증` 후 `저장`한다.

## 알려진 사항

- GUI의 실제 클릭·입력 체감은 사용자가 한 번 확인해야 한다.
- 인물명 작업공간에는 특수 캐릭터와 몬스터 가능성이 있는 항목도 원본 조사 보존을 위해 포함되어 있다. 번역하지 않을 항목은 `excluded`로 지정할 수 있다.
- 새 인물명을 reviewed로 추가한 뒤에는 접근 가능한 장면에서 별도 인게임 확인이 필요하다.

## 후속 수정

- GUI를 파일 경로로 직접 실행할 때 `tools` 패키지를 찾지 못하던 import 경로를 수정했다.
- `tools` 디렉터리 기준 직접 실행과 저장소 루트 기준 패키지 import를 모두 검증했다.
