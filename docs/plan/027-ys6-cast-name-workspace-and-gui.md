# Ys VI 인물명 번역 작업공간 및 GUI 편집 기능 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 완료
- 구현: 완료
- 정적 검증: 완료
- GUI 검증: 자동 검증 완료, 사용자 조작 확인 대기
- 인게임 검증: 026 바이트 동일 결과로 회귀 확인
- 결과 문서: `/docs/result/027-ys6-cast-name-workspace-and-gui.md`

## 배경

026에서 대화창 인물명은 개별 `talk*.xso.z`가 아니라 공통 캐릭터 테이블 `castinfo.dat`에서 로드되는 것을 확인했다. `CAST_C240`의 이름 필드를 한글 게임 코드로 변경해 standalone과 `init.bin` 내부 사본에 적용했고, PPSSPP에서 `이샤`가 정상 출력됐다.

현재 인물명은 빌드 명령의 `--castinfo-name 이샤` 인자로 직접 지정한다. 기존 대사 GUI는 XSO 문자열만 편집하므로 사용자가 `CAST_*` 인물명을 확인하거나 번역할 수 없다.

앞으로 인물명을 지속적으로 한글화하려면 다음이 필요하다.

- `castinfo.dat` 전체 레코드 추출
- 인물명 전용 번역 작업공간
- 기존 GUI의 인물명 편집 탭
- 원문 변경·필드 길이·한글 매핑 검증
- 누적 빌드 시 두 사본 자동 동시 적용

## 목표

1. `castinfo.dat`의 편집 가능한 캐릭터명 레코드를 전수 추출한다.
2. 인물명 전용 번역 JSON·CSV 작업공간을 생성한다.
3. 기존 사용자용 대사 GUI에 `인물명` 탭을 추가한다.
4. 사용자가 원문, 번역, 상태 및 레코드 정보를 확인하고 저장할 수 있게 한다.
5. 검수된 인물명을 누적 빌더가 standalone과 `init.bin` 내부 사본에 자동 적용하게 한다.
6. 이샤의 기존 성공 결과를 새 작업공간 방식으로 재현한다.

## 도구 배치 및 언어

- 사용자용 GUI: 기존 `/tools/ys6_dialogue_viewer.py`에 Python/Tkinter 탭 추가
- 비GUI 처리: `/tools/scripts/ys6_castinfo.py` 및 `/tools/scripts`의 보조 모듈 확장
- 인물명 작업공간: `/.work/ys6-translation-workspace/cast-names.json`
- CSV 보기·백업: `/.work/ys6-translation-workspace/cast-names.csv`

기존 프로젝트와 같은 Python을 사용하며 신규 Node.js 도구는 만들지 않는다.

## 원본 및 기존 결과 보호

- 원본 ISO는 읽기 전용으로 유지한다.
- 원본 SHA-256 `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`를 전후 확인한다.
- 기존 대사 번역 정본 `translations.json`을 수정하지 않는다.
- 인물명 번역은 별도 `cast-names.json`에 저장한다.
- 기존 026 ISO를 덮어쓰지 않는다.
- 작업 경로는 `/.work/ys6-cast-name-workspace`로 분리한다.
- 027 검증 ISO는 `/patched/027-cast-name-workspace`에 둔다.

## 1단계: castinfo 레코드 전수 분석

`ys6_castinfo.py inspect` 결과를 구조화해 전체 `CAST_*` 레코드를 조사한다.

각 레코드에서 기록할 항목:

- 레코드 식별자
- 식별자 오프셋
- 이름 필드 오프셋
- 원본 32바이트 HEX
- CP932 해석 이름
- 빈 이름 여부
- 중복 이름 여부
- 사람이 읽을 수 있는 이름인지 여부
- 특수 캐릭터·몬스터 가능성

`ブラックアドル`처럼 실제 명칭이지만 일반 대화 화자가 아닌 항목도 목록에는 포함하되 기본 상태를 `excluded`로 둘 수 있게 한다.

구조가 예상과 다른 레코드는 자동 편집 대상으로 포함하지 않고 오류·경고 보고서로 분리한다.

## 2단계: 인물명 작업공간 스키마

예상 JSON 구조:

```json
{
  "schema_version": 1,
  "source": {
    "castinfo_sha256": "..."
  },
  "records": [
    {
      "identifier": "CAST_C240",
      "name_offset": 11552,
      "source": "イーシャ",
      "source_raw_hex": "...",
      "source_sha256": "...",
      "translation": "이샤",
      "status": "reviewed",
      "notes": ""
    }
  ]
}
```

허용 상태:

- `untranslated`
- `draft`
- `reviewed`
- `excluded`
- `conflict`

동기화 규칙:

- 원본 레코드가 같으면 번역·상태·메모 유지
- 원문 또는 32바이트 필드 SHA가 바뀌면 `conflict`
- 신규 레코드는 `untranslated`
- 사라진 레코드는 별도 orphan 보고
- 중복 identifier는 오류

## 3단계: 인물명 검증

검수 상태 `reviewed`에 대해 다음을 검사한다.

- 번역이 비어 있지 않음
- NUL 포함 금지
- 현재 한글 매핑으로 인코딩 가능하거나 새 한글 글리프 배정 가능
- 인코딩 결과 + NUL이 32바이트 이하
- identifier·원문 SHA·필드 오프셋 일치
- 같은 identifier에 번역 중복 없음
- 원문 필드 밖 변경 없음

문장부호 정규화나 말줄임표 보정은 인물명에 자동 적용하지 않는다.

## 4단계: GUI 인물명 탭

기존 `/tools/ys6_dialogue_viewer.py`에 `인물명` 탭을 추가한다.

화면 구성:

- 상단: 인물명 작업공간 경로 및 새로고침
- 좌측 목록:
  - 레코드 ID
  - 일본어 원문
  - 한국어 번역
  - 상태
- 우측 편집:
  - identifier 읽기 전용
  - 원문 읽기 전용
  - 번역 입력
  - 상태 선택
  - 메모 입력
  - 필드 오프셋·원문 HEX·SHA 표시
- 하단:
  - 저장
  - 검증
  - 미번역만 보기
  - 검수 완료만 보기
  - 검색

기존 대사 탭의 저장·필터 동작과 최대한 일관되게 구성한다.

## 5단계: GUI 저장 안전성

- UTF-8 JSON 저장
- 저장 전 전체 작업공간 검증
- 임시 파일 작성 후 원자적 교체
- 기존 파일 백업 선택 또는 자동 백업
- 선택 레코드 이동 시 미저장 변경 경고
- GUI 오류 메시지에 identifier와 필드명을 표시
- PowerShell 출력 인코딩에 의존하지 않음

GUI에서 원본 ISO나 `castinfo.dat`를 직접 수정하지 않는다. GUI는 번역 작업공간만 편집한다.

## 6단계: 누적 빌더 연동

통합 빌더가 단일 `--castinfo-name` 대신 인물명 작업공간을 입력받게 확장한다.

예상 인자:

- `--cast-name-workspace <cast-names.json>`

처리:

1. 작업공간 검증
2. `reviewed` 레코드만 선택
3. 전체 대사와 인물명 번역 문자로 글리프 매핑 확장
4. 원본 `castinfo.dat`에서 모든 승인 인물명을 한 번에 수정
5. standalone과 `init.bin` 내부 사본에 동일 결과 적용
6. 레코드별 원문·번역·인코딩 HEX·변경 바이트 보고

기존 단일 이름 인자는 회귀 테스트를 위해 유지하거나 명시적으로 deprecated 처리한다. 두 입력을 동시에 사용하면 충돌을 막기 위해 중단한다.

## 7단계: 이샤 마이그레이션

026의 성공 항목을 새 작업공간에 이관한다.

- `CAST_C240`
- 원문 `イーシャ`
- 번역 `이샤`
- 상태 `reviewed`
- 메모에 026 인게임 확인 기록

새 작업공간 기반 빌드 결과가 026의 수정 `castinfo.dat`와 바이트 단위로 같은지 확인한다.

`talkisha` 실험 번역은 인물명 정본으로 이관하지 않는다. 대사 번역 정본에서 삭제하지도 않으며, 후속 정리 시 별도 판단한다.

## 8단계: 정적 검증

- 전체 `CAST_*` 레코드 수와 identifier 고유성
- 작업공간 JSON·CSV 일치
- 이샤 작업공간 빌드와 026 수정본 SHA 일치
- 두 `castinfo.dat` 수정 사본 동일
- 이름 필드 밖 변경 0건
- `init.bin` 대상 엔트리 밖 변경 0건
- 기존 누적 번역과 글리프 설정 유지
- 허용 ISO extent 밖 변경 0건
- 자동 테스트 및 Python 컴파일 통과
- 원본 및 기존 026 ISO 보존

## 9단계: GUI 검증

- 작업공간 정상 로드
- 검색·상태 필터
- 번역 및 메모 수정
- 저장 후 재실행 시 값 유지
- 잘못된 빈 reviewed 번역 차단
- 32바이트 초과 번역 차단
- 원문 SHA 충돌 표시
- 기존 대사 탭 기능 회귀 없음
- 한글 Windows 환경에서 경로와 글자가 깨지지 않음

## 10단계: 인게임 검증

027 검증 ISO에서 다음을 확인한다.

- 이샤 인물명 한글 출력 유지
- 대사 본문과 이벤트 진행 정상
- 024부터 적용한 글리프 자간 유지

추가 인물명을 사용자가 번역하면 접근 가능한 대표 캐릭터 하나를 더 확인할 수 있다. 번역하지 않은 이름은 원문을 유지해야 한다.

## 예상 변경 및 산출물

- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정: `/tools/scripts/ys6_castinfo.py`
- 수정 또는 신규: `/tools/scripts/ys6_cast_name_workspace.py`
- 수정: `/tools/scripts/ys6_integrated_build.py`
- 추가·수정: `/tools/scripts/tests`
- 생성: `/.work/ys6-translation-workspace/cast-names.json`
- 생성: `/.work/ys6-translation-workspace/cast-names.csv`
- 작업 경로: `/.work/ys6-cast-name-workspace`
- 검증 ISO: `/patched/027-cast-name-workspace/Ys VI - cast-name-workspace-korean-build.iso`
- 결과 문서: `/docs/result/027-ys6-cast-name-workspace-and-gui.md`

## 완료 조건

- 전체 편집 가능 인물명이 작업공간으로 추출된다.
- 원문 변경 시 충돌을 감지한다.
- GUI에서 인물명 번역·상태·메모를 편집하고 안전하게 저장한다.
- reviewed 인물명만 누적 빌드에 적용된다.
- standalone과 `init.bin` 내부 사본이 자동 동시 수정된다.
- 이샤 결과가 026과 바이트 단위로 재현된다.
- 기존 대사 GUI 기능이 유지된다.
- 허용 범위 밖 ISO 변경이 0건이다.
- PPSSPP에서 이샤 인물명 출력이 유지된다.
- 원본 및 기존 패치 ISO가 보존된다.
- 결과 문서가 작성된다.

## 중단 및 재확인 조건

- `castinfo.dat` 레코드 구조가 항목별로 달라 안전한 전수 추출이 불가능함
- identifier 중복 또는 이름 필드 경계 모호
- 기존 026 이샤 결과를 재현하지 못함
- GUI 변경이 기존 대사 번역 저장에 영향을 줌
- 번역 인코딩이 32바이트 필드를 초과함
- 새 글리프 슬롯 부족
- 아카이브 재배치 또는 ISO extent 이동 필요
- 실행 코드 수정 필요
- 대상 외 데이터 변경
- 인게임 인물명 또는 이벤트 손상

## 후속 작업

027 완료 후 사용자가 GUI에서 필요한 인물명을 번역한다. 여러 이름이 검수되면 resolver와 누적 빌더가 대사·선택지·인물명을 하나의 ISO로 일괄 처리하도록 연결하고, 최종적으로 사용자용 한글 패치 GUI의 빌드 단계에 포함한다.
