# 115. Ys VI SPECIAL VERSION 비대사 텍스트 이식 조사 결과

상태: 완료

## 결론

- 인물·몬스터명과 아이템명·설명은 SPECIAL VERSION에서 압축 컨테이너로 바뀌었지만 내부 고정 레코드 구조가 대부분 유지돼 안전한 이식이 가능하다.
- 시스템 메시지는 원문 대응만으로는 충분하지 않다. SPECIAL VERSION 한글 폰트의 확장 사용자 정의 코드 `F0xx`~`F2xx`가 기존 EUC-JP→Shift-JIS 변환 경로에서 표현되지 않아 별도 실행 코드 대응이 필요하다.
- 따라서 후속 적용은 다음처럼 분리하는 것이 안전하다.
  1. 인물·몬스터명과 아이템 이식
  2. 시스템 메시지 변환 경로 확장 및 전용 작업공간
- 이번 조사에서는 ISO와 배포 패치 데이터를 변경하지 않았다.

## 리소스 및 런타임 구조

### 일반판

- 독립 파일:
  - `PSP_GAME/USRDIR/data/misc/castinfo.dat`
  - `PSP_GAME/USRDIR/data/misc/invinfo.dat`
- 런타임 복사본: `PSP_GAME/USRDIR/data/arc/init.bin`
- `init.bin` 내부 엔트리:
  - `castinfo.dat`, index 8
  - `invinfo.dat`, index 10

### SPECIAL VERSION

- 독립 파일:
  - `PSP_GAME/USRDIR/data/misc/castinfo.dat.z`
  - `PSP_GAME/USRDIR/data/misc/invinfo.dat.z`
- 런타임 복사본: `PSP_GAME/USRDIR/data/arc/init.bin`
- `init.bin` 내부 엔트리:
  - `castinfo.dat.z`, index 7
  - `invinfo.dat.z`, index 9
- 독립 파일과 아카이브 복사본의 해제 payload는 각각 바이트 단위로 일치한다.
- 두 `.z` 컨테이너는 해제→재압축→재해제 payload 왕복 검증을 통과했다.
- 동일 엔트리를 그대로 재삽입한 `init.bin`은 바이트 단위로 보존됐다.

## 인물·몬스터명

- 일반판 레코드: 164개
- SPECIAL VERSION 레코드: 164개
- 식별자와 원문이 모두 일치: 162개
- 승인 번역: 70개
- 승인 번역 중 그대로 대응: 68개
- 이름 영역: 32바이트, 모든 승인 번역 길이 적합
- SPECIAL 전용 또는 누락 식별자: 0개

두 몬스터 ID는 이름이 서로 교환돼 있다.

- `CAST_M720`: 일반판 `セラ`, SPECIAL `ユエ`
- `CAST_M730`: 일반판 `ユエ`, SPECIAL `セラ`

ID 기준으로 그대로 복사하면 이름이 뒤바뀐다. SPECIAL 원문 이름 기준으로 번역을 교차 대응하면 `세라`와 `유에`를 안전하게 적용할 수 있다.

승인된 70개 이름에 필요한 revision 6 미등록 글리프는 `랴`, `쉐` 2자다. 미승인 레코드까지 포함하면 `믹`도 필요하지만 현재 적용 후보에는 포함하지 않는다.

## 아이템명·설명

- 일반판: 73개 × 184바이트, 전체 13,448바이트
- SPECIAL VERSION: 77개 × 184바이트, 전체 14,184바이트
- 공통 필드 경계:
  - 헤더 16바이트
  - 이름 32바이트
  - 메타데이터 44바이트
  - 설명 108바이트
- 기존 73개 중 이름과 설명 모두 일치: 72개
- 72개 승인 번역의 이름·설명 공간 초과: 0개
- revision 6 미등록 글리프: `겸`, `듬`, `똬`, `롱`, `링`, `벅`, `볍`, `뿜`, `클` 9자

`ky_09` 알마의 날개는 이름은 같지만 설명이 달라 수동 검토가 필요하다.

- 일반판: 던전 탈출 및 무제한 사용 설명
- SPECIAL VERSION: 무제한 사용 문구의 위치와 표현이 달라짐
- 현재 한국어 번역은 알마 동상 간 비행 이동을 설명해 두 일본어 원문과 의미가 직접 일치하지 않으므로 자동 이식에서 제외하는 것이 안전하다.

SPECIAL VERSION 전용 아이템은 4개다.

- `ky_20` 레다의 날개 후보
- `ky_21` 동굴의 열쇠 후보
- `ky_22` 봉인의 열쇠 후보
- `ky_23` 라바의 수기 후보

네 항목은 신규 번역 작업공간을 만들어 검수해야 한다.

## 시스템 메시지

- 일반판 작업공간: 318개
- SPECIAL VERSION 추출 후보: 332개
- 원문 바이트 단일 일치: 162개
- 같은 원문이 여러 SPECIAL 위치에 존재: 23개
- 원문 그대로 미발견: 133개
- SPECIAL에서만 추출된 후보: 146개
- 일반판 승인 번역: 161개

승인 번역의 구조 대응은 다음과 같다.

- 단일 위치 정확 대응: 132개
- 중복 위치 대응: 5개
- 원문 변경 또는 미발견: 24개
- 정확 대응 132개는 모두 번역 길이가 SPECIAL 원문 공간 안에 들어간다.
- 형식 토큰 불일치: 0개

미발견 24개 중 저장·불러오기 메시지 다수는 SPECIAL판에서 메모리스틱 표기, 공백, 제어문자와 문장 일부가 변경됐다. 유사도와 주변 범위로 높은 대응 후보를 찾았지만 원시 바이트가 다르므로 전용 작업공간에서 다시 승인해야 한다.

### EUC-JP 변환 제약

시스템 메시지는 실행 파일에 EUC-JP로 저장되고 게임 실행 중 Shift-JIS 코드로 변환된다. SPECIAL revision 6의 확장 글리프는 사용자 정의 Shift-JIS 코드에 있으므로 EUC-JP로 직접 표현할 수 없다.

- 승인 번역 161개 중 현 변환 경로에서 인코딩 차단: 120개
- 현재 EUC 변환까지 가능한 단일 정확 대응: 34개
- 현재 EUC 변환까지 가능한 중복 대응: 3개
- 신규 미등록 글리프: `닝`, `뛸`, `롤`, `롬`, `썬`, `틱` 6자
- 이미 revision 6에 있지만 EUC로 표현할 수 없는 확장 글리프: 58자

따라서 시스템 메시지를 단순 제자리 교체하는 방식으로 전체 이식할 수 없다. 후속 단계에서는 다음 중 하나를 검증해야 한다.

1. EUC-JP 변환 결과가 사용자 정의 코드 영역까지 도달하도록 변환 테이블·루틴을 확장한다.
2. 시스템 메시지만 별도 코드 배정을 사용하되 기존 폰트 매핑 및 다른 문자열과 충돌하지 않게 설계한다.

현재 구조에서는 1번이 기존 전체 매핑을 유지하기에 더 적합하지만, 실행 코드 분석과 별도 시험 ISO가 필요하다.

## 글리프 요구량

- 인물·몬스터 및 기존 아이템의 직접 이식에 필요한 신규 글리프: 총 11자
  - 인물·몬스터: `랴`, `쉐`
  - 아이템: `겸`, `듬`, `똬`, `롱`, `링`, `벅`, `볍`, `뿜`, `클`
- 시스템 메시지까지 포함한 단순 문자 집합의 신규 글리프: 총 17자
- 시스템 메시지는 신규 6자만 추가해도 해결되지 않으며 기존 확장 글리프 58자의 EUC 변환 문제가 함께 해결돼야 한다.

## BOOT/EBOOT 확인

- SPECIAL 원본 `BOOT.BIN` SHA-256: `224F0AE02849521F688C438AFEA096E7081188832312E38B89B6A9D871976C5E`
- 배포 seed BOOT과 seed EBOOT에서 추출한 시스템 메시지 후보는 각각 332개다.
- 두 seed 실행 파일의 `(오프셋, 원문 바이트)` 집합은 전부 일치한다.
- 실제 적용 시 BOOT과 EBOOT 양쪽을 같은 결과로 갱신할 수 있다.

## 생성 파일

- 감사 도구: `tools/scripts/ys6_special_nondialogue_audit.py`
- 전체 보고서: `tools/patchdata/work/current/115-ys6-special-version-nondialogue-text-port-audit/report.json`
- 인물·몬스터 대응표: `tools/patchdata/work/current/115-ys6-special-version-nondialogue-text-port-audit/cast-candidates.csv`
- 아이템 대응표: `tools/patchdata/work/current/115-ys6-special-version-nondialogue-text-port-audit/item-candidates.csv`
- 시스템 메시지 대응표: `tools/patchdata/work/current/115-ys6-special-version-nondialogue-text-port-audit/system-message-candidates.csv`

## 검증

- Python 구문 검사: 통과
- 일반판 cast/item 작업공간 원본 해시: 일치
- 두 판본 cast/item 레코드 구조 파싱: 통과
- SPECIAL 독립 압축 파일과 `init.bin` payload 비교: 일치
- 압축 컨테이너 payload 왕복: 통과
- 아카이브 동일 엔트리 무수정 재삽입: 통과
- 승인 이름·아이템 번역 길이 사전 검증: 초과 0개
- 시스템 메시지 형식 토큰 검증: 불일치 0개
- 원본 ISO 및 배포 패치 데이터 변경: 없음

## 권장 후속 작업

### 116번: SPECIAL 인물·몬스터명 및 아이템 이식

- 신규 글리프 11자 append
- 몬스터 ID 교환 2건을 원문 기준으로 대응
- 안전한 기존 아이템 72개 적용
- `ky_09`와 SPECIAL 전용 아이템 4개는 별도 검수 상태로 생성
- 독립 `.dat.z`와 `init.bin` 런타임 복사본을 함께 교체
- GUI에 SPECIAL판 인물·몬스터·아이템 적용 수 표시

### 이후: SPECIAL 시스템 메시지 변환 경로 확장

- 115번 시스템 메시지 대응표로 전용 작업공간 생성
- EUC-JP→Shift-JIS 변환 루틴과 확장 사용자 정의 코드 처리 분석
- 최소 문구 시험 ISO로 실행 코드 수정 검증
- 검증 후 161개 승인 번역과 SPECIAL 전용 메시지 검수 진행
