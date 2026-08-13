# 035. Ys VI Windows 한국어 대사 추출기 및 PSP draft 연계 계획

## 목적

Windows판 한국어 패치의 `data_us.ni/.na`에서 전체 XSO를 추출하고, 전용 한글 문자 코드를 Unicode로 복원하여 PSP판 번역 검수에 사용할 수 있는 대사 JSON을 만든다.

Windows 번역은 곧바로 패치에 반영하지 않는다. PSP 원문과 안전하게 대응되는 항목만 기존 번역 작업공간의 `draft` 후보로 가져오고, 사용자가 `override`로 승인한 항목만 실제 패치 빌드에 포함하는 현재 절차를 유지한다.

## 선행 분석

계획 034에서 다음을 확인했다.

- Windows 아카이브에는 총 1,343개 항목과 1,182개 XSO가 있다.
- Windows와 PSP의 XSO 경로 및 내부 `XSR\0` 구조가 대응한다.
- `map/s_02/s_020a/adolsleep.xso.z`는 양쪽 모두 문자열 35개이며 인덱스 순서도 같다.
- Windows판 한글 바이트는 UTF-8·UTF-16·CP949·CP932 평문이 아니라 전용 문자 매핑이다.
- `im04.dt`에는 완성형 한글 글리프가 포함돼 있어 문자 코드 복원의 근거로 사용할 수 있다.

## 구현 범위

### 1. Windows NNI/NA 읽기 전용 추출기

`/tools/scripts`에 Python 비GUI 스크립트를 작성한다.

- `data_us.ni` 헤더와 난독화된 파일 색인을 해석한다.
- `data_us.na`에서 선택 항목 또는 전체 항목을 추출한다.
- `.z` 항목의 CRC32·원본 크기·zlib 스트림을 검증한다.
- 기본 출력은 `.work/ys6-windows-korean-extraction`으로 제한한다.
- 경로 이탈과 절대 경로 항목을 거부한다.
- 원본 `windowVersion` 파일은 읽기 전용으로 취급한다.

예상 파일:

- `/tools/scripts/ys6_windows_archive.py`

### 2. 전용 한글 문자 매핑 복원

다음 근거를 함께 사용해 XSO 바이트와 Unicode 문자의 관계를 찾는다.

1. `im04.dt`의 cmap, glyph order, post 이름 및 글리프 구조
2. Windows XSO에서 반복되는 문자열과 문맥
3. PSP판 동일 경로·인덱스의 일본어 원문
4. 화자명, 고유명사, 짧은 문장처럼 대응이 명확한 표본
5. 동일 코드가 전체 XSO에서 같은 문자로 쓰이는지에 대한 빈도·충돌 검사

복원한 문자표는 생성 결과가 아니라 재사용 가능한 패치 데이터로 관리한다.

예상 파일:

- `/tools/patchdata/windows-korean-code-map.json`
- `/tools/scripts/ys6_windows_korean_codec.py`

문자 매핑은 각 코드에 대해 근거와 신뢰도를 기록한다. 하나의 코드가 여러 문자로 해석되거나 근거가 부족한 경우 임의로 확정하지 않고 미해결 코드로 남긴다.

### 3. Windows 전체 대사 JSON 추출

전체 XSO를 순회하여 다음 정보를 기록한다.

- Windows 아카이브 경로와 XSO 이름
- 문자열 인덱스
- 원시 바이트와 원시 바이트 해시
- 변환한 Unicode 한국어
- 제어 태그와 줄바꿈
- 미해결 코드 목록
- 변환 신뢰도와 경고

예상 출력:

- `/tools/patchdata/windows-korean-dialogues.json`
- `.work/ys6-windows-korean-extraction/report.json`

완전하게 해석되지 않은 문자열도 원시 바이트와 미해결 위치를 보존한다.

### 4. PSP판과 자동 대응 및 검증

다음 조건을 단계별로 확인한다.

1. 정규화된 Windows 경로와 PSP `iso_path`가 일치한다.
2. XSO 문자열 수와 대상 인덱스가 유효하다.
3. PSP 원문 역할이 `dialogue`, `choice` 또는 대사에 포함되는 화자 리소스인지 확인한다.
4. 제어 태그·변수·줄바꿈 구조가 호환되는지 확인한다.
5. 플랫폼별 추가·삭제 문자열이 감지되면 해당 XSO의 자동 대응을 보류한다.

대응 결과에는 `exact`, `review`, `unmatched` 상태와 사유를 기록한다.

예상 파일:

- `/tools/scripts/ys6_windows_dialogue_match.py`
- `.work/ys6-windows-korean-extraction/psp-match-report.json`

### 5. 기존 번역 작업공간 연계

Windows 번역이 안전하게 대응되더라도 다음 원칙을 적용한다.

- 기존 `override`는 절대 변경하지 않는다.
- 사용자가 작성하거나 교정한 기존 `draft`도 기본적으로 덮어쓰지 않는다.
- `untranslated`이며 정확 대응된 대사만 Windows 번역으로 `draft` 전환할 수 있다.
- 자동 등록 전 미리보기와 변경 수량을 출력한다.
- 실제 등록은 명시적인 적용 옵션으로 분리한다.
- `notes`에는 Windows 패치 출처, 대응 방식 및 작업 번호 035를 기록한다.
- 실제 패치 빌드는 `override`만 반영하는 기존 정책을 유지한다.

## 검증 계획

### 아카이브 검증

- 1,343개 색인 항목을 오류 없이 읽는다.
- 전체 `.z` 항목의 압축 해제 크기와 CRC32를 검증한다.
- 추출 경로가 지정 출력 폴더 밖으로 벗어나지 않는지 시험한다.
- 분석 전후 `data_us.na`, `data_us.ni`, `im04.dt`, `im04.fot`의 SHA-256이 동일한지 확인한다.

### 문자 변환 검증

- `adolsleep` 35개 문자열을 첫 기준 표본으로 사용한다.
- 명확한 화자명과 대사 표본이 자연스러운 한글로 복원되는지 확인한다.
- 같은 코드가 서로 다른 한글로 충돌하지 않는지 전체 코퍼스에서 검사한다.
- 변환→역변환이 가능한 코드에 대해서는 바이트 라운드트립을 확인한다.
- 미해결 코드를 대체 문자로 조용히 숨기지 않고 보고서에 표시한다.

### PSP 대응 및 작업공간 검증

- 경로·인덱스 정확 대응 수와 보류·미대응 수를 집계한다.
- 제어 태그가 달라진 표본은 자동 등록되지 않는지 확인한다.
- 기존 `override`와 기존 번역 `draft`가 보존되는지 확인한다.
- 시험용 복사본에서 Windows 번역 draft 등록을 실행하고 차이를 검토한다.
- 프로젝트의 관련 Python 구문 검사와 기존 검증 명령을 실행한다.

## 안전 및 저작물 취급

- `/windowVersion` 원본은 수정하지 않는다.
- 외부 실행 파일을 내려받거나 실행하지 않고 Python으로 필요한 형식을 구현한다.
- 추출한 Windows 번역은 이 프로젝트의 PSP 패치 제작을 위한 내부 참고 데이터로만 관리한다.
- 원본 패치 파일이나 전체 추출물을 별도 배포물로 만들지 않는다.
- 대규모 `draft` 병합 전에 통계와 표본을 사용자에게 먼저 제시한다.

## 범위 제외

- 이번 단계에서 Windows 아카이브를 재구축하지 않는다.
- Windows 게임 파일을 수정하거나 실행하지 않는다.
- PSP ISO를 새로 빌드하지 않는다.
- Windows 번역을 `override`로 자동 승인하지 않는다.
- 이미지·아이템 설명·인물명 등 XSO 대사 이외 자산은 후속 범위로 둔다.

## 예상 산출물

- Windows NNI/NA 읽기 전용 추출기
- Windows 전용 한글 코덱 및 코드 매핑 JSON
- Windows 전체 대사 JSON
- PSP 대응 보고서
- 안전한 `draft` 가져오기 기능
- `/docs/result/035-ys6-windows-korean-dialogue-extractor.md`

## 중단 조건

다음 상황에서는 임의 처리를 하지 않고 분석 결과와 선택지를 보고한다.

- 전용 한글 코드가 폰트 및 반복 표본만으로 유일하게 복원되지 않는 경우
- Windows와 PSP의 문자열 순서가 대규모로 다른 경우
- 하나의 코드가 문맥에 따라 여러 문자로 사용되는 경우
- 외부 바이너리 실행이나 게임 실행 없이는 매핑을 확정할 수 없는 경우

## 상태

- 계획 작성 완료
- 사용자 확인 완료
- 구현 및 사용자 확인 후 draft 적용 완료
- 결과 문서: `/docs/result/035-ys6-windows-korean-dialogue-extractor.md`
