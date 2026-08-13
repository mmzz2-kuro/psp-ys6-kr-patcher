# 038. 전체 draft 한글패치 적용 위험 분석 계획

## 목적

현재 `/tools/config/dialogue-translations.json`의 모든 `draft`를 `override`로 승인하여 한글패치에 적용한다고 가정했을 때 발생할 수 있는 기술적·데이터적 문제를 실제 빌드 파이프라인으로 점검한다.

분석 단계에서는 실제 번역 상태, 원본 ISO 및 패치 ISO를 변경하지 않는다.

## 현재 기준

- 전체 작업공간 레코드: 7,424개
- 번역이 입력된 `draft`: 4,628개
- `override`: 0개
- Windows판과 정확 대응하여 교체된 기존 번역: 4,585개
- 정확 대응 조건을 충족하지 않아 기존 내용이 보존된 번역: 43개
- Windows/PSP 구조 검토 또는 미대응 문자열: 총 537개

## 분석 범위

### 1. 전체 draft 가상 승격

- 현재 번역 작업공간 전체를 `.work/ys6-all-drafts-risk-analysis`에 복사한다.
- 복사본에서 번역이 입력된 `draft`만 `override`로 변경한다.
- 실제 `/tools/config/dialogue-translations.json`은 수정하지 않는다.
- 가상 승격 전후 상태 수량과 SHA-256을 기록한다.

### 2. 데이터 안전성 분석

각 적용 대상에 대해 다음을 검사한다.

- 번역문이 비어 있지 않은지
- PSP 원문 해시가 현재 카탈로그와 일치하는지
- Windows판과 PSP판의 경로·인덱스 대응 상태
- `exact`, `review`, `unmatched` 분류
- 대사·선택지·화자 이외 리소스가 섞였는지
- 색상, 크기, 변수, 제어 코드 및 줄바꿈 구조 차이
- 플레이어명 변수 `\x1`이 고정 문자열 `아돌`로 바뀐 사례
- Windows판에서 루비 태그가 제거되거나 본문으로 풀린 사례
- 비정상적으로 길어진 번역과 한 줄 길이 증가
- 번역문에 남은 일본어, 전용 코드 표식 또는 미지원 문자가 있는지
- 중복 XSO 경로 및 런타임 대응이 불확실한 항목

### 3. 전체 빌드 사전 검증

가상 작업공간으로 실제 통합 빌더의 `preflight`를 실행한다.

- 한글 문자 집합 및 게임 코드 매핑 생성
- 필요한 글리프 수와 EBOOT 폰트 슬롯 수 확인
- 한글 글리프 생성 및 EBOOT 작업본 생성 검증
- 모든 대상 XSO 문자열 재조립
- `.z` 재압축 및 라운드트립 검증
- 런타임 아카이브별 할당 공간과 남은 여유 확인
- 독립 XSO의 ISO 할당 공간 확인
- 원본 ISO 해시와 런타임 payload 일치 확인

`preflight`는 `.work`에 중간 산출물을 만들지만 패치 ISO는 생성하지 않는다.

### 4. 용량 및 위험도 집계

다음 지표를 보고서로 만든다.

- 적용 대상 문자열 및 XSO 수
- 수정되는 런타임 아카이브 수
- 필요한 글리프 수
- 원문 대비 번역 바이트 증가량 최대·평균·상위 항목
- 압축 후 남은 공간이 가장 적은 XSO·아카이브
- 할당 공간 초과 항목
- 구조 불일치 및 자동 대응 불확실 항목
- 화면 폭을 넘길 가능성이 높은 문장
- 줄 수 증가와 선택지 길이 위험 항목

위험도는 다음처럼 분류한다.

- `blocker`: 빌드 실패, 할당 공간 초과, 매핑·폰트 용량 초과, 원문 해시 불일치
- `high`: 잘못된 인덱스 대응, 필수 제어 코드 손실, 선택지 진행 문제 가능성
- `medium`: 화면 넘침, 줄바꿈·루비·플레이어명 표현 차이, 문맥 불일치 가능성
- `low`: 띄어쓰기, 문체, 구두점 및 번역 품질 문제

### 5. 표본 검토

다음 범주의 대표 항목을 사람이 읽을 수 있는 표로 추출한다.

- 가장 긴 번역
- 바이트 증가가 큰 번역
- 줄 수가 증가한 번역
- 제어 토큰이 달라진 번역
- Windows판 exact 대응이 아닌 기존 번역 43개
- 선택지와 선택지 질문
- 플레이어명 및 루비 관련 문장

## 검증 방법

- 가상 작업공간에 대해서 `ys6_translation_workspace.py validate` 실행
- 통합 빌더 `preflight` 성공 여부 확인
- 생성한 각 XSO와 `.z`의 재파싱·라운드트립 확인
- `preflight-report.json`, `translation-report.csv`, `xso-report.csv`, `archive-report.csv` 분석
- 분석 전후 실제 번역 작업공간과 원본 ISO SHA-256 동일 확인
- Python 구문 및 JSON 유효성 검사

## 예상 산출물

- `.work/ys6-all-drafts-risk-analysis/dialogue-translations.all-override.json`
- `.work/ys6-all-drafts-risk-analysis/preflight/`
- `.work/ys6-all-drafts-risk-analysis/risk-report.json`
- `.work/ys6-all-drafts-risk-analysis/risk-samples.csv`
- `/docs/result/038-ys6-all-drafts-patch-risk-analysis.md`

## 안전 원칙

- 실제 번역 작업공간의 상태를 변경하지 않는다.
- 원본 ISO를 수정하지 않는다.
- `/patched`에 새 ISO를 만들지 않는다.
- 문제를 발견해도 이번 분석 단계에서 번역문이나 빌더를 고치지 않는다.
- 수정이 필요하면 결과를 바탕으로 별도 계획을 작성한다.

## 분석 한계

- `preflight`는 파일 구조, 용량, 압축 및 문자 매핑 문제를 잡을 수 있지만 실제 화면의 자연스러운 줄바꿈과 문맥 품질을 완전히 보장하지 못한다.
- 모든 이벤트 진행과 선택지를 인게임에서 자동 재생하지 않으므로 런타임 의미 문제는 대표 표본 및 후속 플레이 테스트가 필요하다.

## 상태

- 계획 작성 완료
- 사용자 확인 완료
- 분석 완료
- 결과 문서: `/docs/result/038-ys6-all-drafts-patch-risk-analysis.md`
