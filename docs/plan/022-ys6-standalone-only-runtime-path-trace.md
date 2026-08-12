# Ys VI standalone-only XSO 런타임 경로 조사 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 대기
- 정적 분석: 완료
- PPSSPP 런타임 추적: 미착수
- 결과 문서: `/docs/result/022-ys6-standalone-only-runtime-path-trace.md`

## 배경

계획 020은 원본 ISO의 `/data/arc` 아카이브 222개와 내부 XSO 344개를 전수 분석했다. standalone XSO 1,194개 중 355개는 런타임 XSO와 payload SHA-256으로 대응했지만 839개는 `/data/arc`에서 같은 payload를 찾지 못해 `standalone_only`로 분류됐다.

계획 작성 당시 사용자가 새로 작성한 번역 52개 중 `s_0551`의 29개는 런타임 대응이 확인돼 계획 021에서 ISO에 적용하고 인게임 검증했다. 당시 나머지 23개는 20개 standalone XSO에 속했다. 착수 직전 작업공간을 다시 검사한 결과 번역이 추가돼 현재 조사 대상은 21개 standalone XSO의 35개 번역이다. 이 항목들은 현재 021 빌더가 안전하게 반영할 런타임 대상이 없다.

| 구분 | XSO 수 | 번역 수 |
|---|---:|---:|
| `talkkebin.xso.z` | 1 | 3 |
| `talktokusa.xso.z` | 1 | 2 |
| `oruhamove.xso.z` | 1 | 9 |
| `adolsleep.xso.z` | 1 | 4 |
| `s_hidden1` 인물명 XSO | 17 | 17 |
| 합계 | 21 | 35 |

이 파일들은 실제 standalone 경로에서 직접 로드될 수도 있고, 이름이나 구조가 다른 런타임 데이터에 통합됐을 수도 있으며, 일부는 개발·편집용 또는 미사용 데이터일 수도 있다. 파일명 유사성만으로 패치 대상을 정하면 잘못된 파일을 수정할 위험이 있으므로 정적 증거와 필요한 경우 PPSSPP 런타임 증거를 함께 수집한다.

## 목표

1. 미반영 번역 35개의 정확한 원문 XSO·문자열·역할을 고정한다.
2. 원본 ISO 전체에서 대상 XSO의 압축 데이터, 비압축 payload, 문자열 및 구조적 변형을 찾는다.
3. `/data/arc` 외 디렉터리와 아카이브·컨테이너를 포함해 가능한 로드 위치를 조사한다.
4. 정확한 해시가 다른 후보는 파일명, XSO 명령 영역, 문자열 집합과 원시 바이트로 비교한다.
5. 정적 분석만으로 확정되지 않는 실제 사용 후보는 PPSSPP에서 파일 로그·메모리로 추적한다.
6. 각 대상에 `확정`, `유력`, `미사용 가능`, `미확정` 판정을 부여하고 근거를 기록한다.
7. 확정된 대상만 020 대응표 및 021 통합 빌더에 연결할 후속 구현 범위를 제안한다.

## 범위와 금지 사항

이번 단계는 조사만 수행한다.

- 원본 ISO와 021 패치 ISO를 수정하지 않는다.
- 번역 작업공간의 상태·번역문·메모를 수정하지 않는다.
- 미반영 23개를 ISO에 삽입하지 않는다.
- 파일명만 같은 후보를 확정 대응으로 취급하지 않는다.
- 런타임 확인 없이 메모리 주소나 아카이브 후보를 패치 대상으로 등록하지 않는다.
- 아카이브 재배치, 실행 코드 패치 및 최종 GUI 연결은 수행하지 않는다.
- PPSSPP 설정을 변경해야 할 경우 변경 전 백업하고 조사 후 원복한다.

## 원본 및 작업 경로

- 원본 ISO: `/roms/Ys VI - Napishtim no Hako (Japan).iso`
- 현재 검증용 ISO: `/patched/021-multi-archive-build/Ys VI - multi-archive-korean-build.iso`
- 번역 작업공간: `/.work/ys6-translation-workspace/translations.json`
- 대사 카탈로그: `/.work/ys6-full-dialogue/catalog/dialogue_catalog.json`
- 020 대응표: `/.work/ys6-runtime-archive-map/runtime_archive_xso_map.json`
- 조사 작업 경로: `/.work/ys6-standalone-runtime-trace`
- 비GUI 분석 스크립트: `/tools/scripts/ys6_standalone_runtime_trace.py`
- 테스트: `/tools/scripts/tests/test_ys6_standalone_runtime_trace.py`

원본 ISO SHA-256 `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`를 조사 전후 확인한다.

## 1단계: 대상 manifest 생성

번역 작업공간에서 번역문이 있으면서 020 상태가 `standalone_only`인 레코드만 읽기 전용으로 수집한다.

대상 XSO별로 다음을 기록한다.

- standalone ISO 경로
- 맵 그룹·맵 ID·XSO 이름
- 원본 압축·비압축 SHA-256과 크기
- 문자열 수와 명령 수
- 번역된 문자열 인덱스·역할·원문·원시 바이트
- 번역 상태
- 020 대응 상태

현재 확정 수량은 XSO 21개·번역 35개다. 이후 다시 달라지면 작업공간 변경으로 보고하고 manifest 생성 시점의 SHA-256과 실제 수량을 문서에 남긴다. 번역문은 조사 식별 정보로만 사용하며 검수 상태로 변경하지 않는다.

## 2단계: 원본 ISO 전체 파일 목록과 컨테이너 분류

ISO 9660 디렉터리를 재귀 순회해 모든 파일의 경로, extent, 크기와 SHA-256을 열거한다.

다음 범주를 구분한다.

- standalone `.xso.z`
- `/data/arc/*.bin`
- 기타 `.bin`, `.dat`, `.z` 및 알려지지 않은 컨테이너
- EBOOT·BOOT·PRX 등 실행 파일
- 이미지·음성 등 명백한 비대상 파일

기존 020이 `/data/arc`만 분석한 한계를 보완해, 다른 디렉터리의 아카이브 복사본이나 직접 로드되는 standalone 파일을 후보로 유지한다.

## 3단계: 정확 일치 전수 검색

각 대상에 대해 원본 ISO에서 다음 바이트 패턴을 검색한다.

1. 원본 `.xso.z` 컨테이너 전체
2. 비압축 XSO payload 전체
3. 충분히 긴 고유 문자열 원시 바이트
4. XSO 파일명 ASCII·CP932 표기

각 hit에 대해 ISO 절대 오프셋을 ISO 9660 파일 extent에 역매핑한다. 한 파일 안에서 발견되면 파일 경로와 상대 오프셋을 기록하고, 어떤 파일 extent에도 속하지 않으면 파일시스템 외 영역으로 별도 분류한다.

standalone 파일 자체의 hit와 숨은 복사본 hit를 구분한다. 압축 payload는 압축 방식·레벨 차이로 원시 검색에 잡히지 않을 수 있으므로 “검색 결과 없음”을 미사용 근거로 단독 사용하지 않는다.

## 4단계: 이름 기반 후보 조사

대상 XSO 이름을 ISO 파일명과 모든 알려진 아카이브 엔트리 이름에서 대소문자 무시로 검색한다.

- 완전 일치
- 확장자·접두 `_` 차이
- 대소문자 차이
- 맵 ID가 다른 동일 basename
- `talk*`, `*move`, 인물명 계열의 유사 이름

이름 후보에는 자동 대응 상태를 부여하지 않는다. 정확 payload 또는 구조 비교 결과를 함께 기록해야 한다.

## 5단계: 구조적 유사도 비교

정확 해시가 다른 후보 XSO는 비압축한 뒤 구조적으로 비교한다.

비교 항목:

- XSR 매직과 헤더
- 명령 워드 수와 문자열 수
- 명령 영역 SHA-256
- opcode·argument 시퀀스
- 문자열별 원시 바이트와 CP932 텍스트
- 대상 번역 원문의 포함 여부와 인덱스
- 문자열 집합의 교집합과 순서

판정 예시:

- 명령 영역과 문자열 테이블이 모두 동일: 압축만 다른 정확 대응
- 명령 영역 동일, 일부 문자열만 다름: 지역·상태 변형 후보
- 대상 문자열 원시 바이트와 참조 위치가 일치: 강한 후보
- 이름만 같고 구조가 다름: 비대응

유사도 점수는 후보 정렬에만 사용하고 확정 근거로 단독 사용하지 않는다.

## 6단계: 참조 문자열 및 로더 단서 조사

BOOT/EBOOT/PRX와 관련 스크립트 데이터에서 다음을 읽기 전용으로 검색한다.

- 대상 XSO basename
- 상대 경로 및 `data/map`, `data/arc` 문자열
- 대상 맵 ID
- 인물명 XSO 이름
- 알려진 로더 함수 근처의 파일 확장자 문자열

정적 참조가 발견되면 파일 오프셋과 가능한 실행 주소를 기록한다. 디스어셈블이나 실행 코드 수정은 하지 않는다. 단순 문자열 존재는 실제 실행 경로 확정이 아니므로 런타임 검증 필요 여부를 함께 표시한다.

## 7단계: 대상별 정적 판정

각 XSO에 다음 상태 중 하나를 부여한다.

| 상태 | 의미 |
|---|---|
| `direct_standalone_candidate` | standalone ISO 파일을 직접 읽을 정적 근거가 있음 |
| `embedded_exact` | 다른 파일 안에서 동일 압축 또는 비압축 payload 발견 |
| `embedded_variant` | 이름·명령·문자열 구조가 강하게 일치하는 변형 발견 |
| `reference_only` | 파일명·경로 참조만 발견 |
| `no_static_evidence` | standalone 자체 외 런타임 단서 없음 |
| `invalid` | 입력 또는 후보 구조가 손상돼 비교 불가 |

정적 증거만으로 패치 대상을 확정할 수 있는 항목과 PPSSPP 추적이 필요한 항목을 분리한다.

## 8단계: PPSSPP 런타임 추적 준비

정적 분석 후에도 실제 로드 위치가 불명확한 항목 중 게임에서 접근 가능한 표본을 우선한다.

우선순위:

1. `talkkebin` 선택지 3개
2. `talktokusa` 예/아니요 2개
3. `oruhamove`의 `イーシャについて`
4. `adolsleep`의 추가 이벤트 대사 4개
5. `s_hidden1` 인물명 17개

사용자에게 각 문자열이 나타나는 게임 위치 또는 세이브를 확인받는다. 접근 위치를 모르는 항목은 무리하게 런타임 추적하지 않고 미확정으로 남긴다.

PPSSPP를 사용해야 할 때는 다음을 먼저 수행한다.

- PPSSPP 완전 종료 확인
- 실행 파일·설정·게임 ID·부팅 ISO 확인
- `ppsspp.ini`와 로그 설정 백업
- 파일 로깅·원격 디버거는 필요한 최소 범위만 임시 활성화
- localhost 전용 원격 디버거 유지
- 세이브와 세이브 스테이트 수정 금지

사용자 확인 전에는 PPSSPP 프로세스를 종료하거나 설정을 변경하지 않는다.

## 9단계: PPSSPP 파일·메모리 추적

사용자가 대상 화면에 도달하면 다음 증거를 수집한다.

- 파일 로그의 실제 open/read 경로
- 메모리의 대상 원문 원시 바이트
- 전체 비압축 XSO payload 일치 주소
- 후보 변형 XSO의 메모리 존재 여부
- 로드 전후 메모리 변화와 힙 복사본
- 동일 문자열이 UI 버퍼와 원본 풀에 각각 존재하는지

가능하면 수정 ISO 없이 원본 ISO에서 먼저 추적한다. 위치 확인을 위해 시험 패치가 꼭 필요하면 이 계획을 갱신하고 별도 격리 ISO 생성에 대해 다시 사용자 확인을 받는다.

런타임 확정 기준:

- 파일 로그에서 직접 로드 경로 확인, 또는
- 메모리의 전체 XSO payload와 ISO 내 후보 payload가 일치하고 로드 시점이 대상 화면과 대응, 또는
- 위 두 증거에 준하는 재현 가능한 읽기 경로 확보

화면 출력 문자열 하나만 메모리에 존재하는 것은 원본 파일 위치 확정으로 취급하지 않는다.

## 10단계: 설정 원복과 재검증

- PPSSPP를 종료한 상태에서 임시 설정을 백업값으로 복원한다.
- 파일 로깅과 원격 디버거가 원래 상태인지 확인한다.
- 조사 로그·메모리 덤프는 `/.work/ys6-standalone-runtime-trace`에만 보관한다.
- 원본 ISO와 021 ISO SHA-256이 조사 전후 동일한지 확인한다.
- 세이브·세이브 스테이트가 변경되지 않았음을 기록한다.

## 11단계: 대응 결과와 후속 연결 명세

대상별 최종 상태:

| 상태 | 의미 |
|---|---|
| `confirmed_direct` | standalone 파일 직접 로드 확정 |
| `confirmed_embedded` | 다른 아카이브·파일 내부 런타임 payload 확정 |
| `confirmed_variant` | 변형 payload와 문자열 인덱스 매핑 확정 |
| `likely_unused` | 정적·런타임 조사에서 사용 증거가 없고 대체 데이터가 확인됨 |
| `unresolved` | 접근 위치 또는 증거가 부족해 확정 불가 |

확정 항목마다 021 빌더가 사용할 연결 정보를 정의한다.

- 원본 standalone XSO SHA-256
- 런타임 ISO 파일 경로
- 컨테이너 또는 아카이브 엔트리 식별자
- 원본 런타임 payload SHA-256
- 문자열 인덱스가 동일한지 여부
- 기존 할당 크기와 교체 제약
- 직접 ISO 파일 교체인지 아카이브 엔트리 교체인지

문자열 인덱스가 다르거나 변형 payload인 경우 자동 연결하지 않고 별도 변환 명세와 테스트를 요구한다.

## 산출물

- 대상 manifest: `/.work/ys6-standalone-runtime-trace/targets.json`
- ISO 전체 파일 목록: `/.work/ys6-standalone-runtime-trace/iso-files.csv`
- 정확 검색 결과: `/.work/ys6-standalone-runtime-trace/exact-hits.csv`
- 이름 후보: `/.work/ys6-standalone-runtime-trace/name-candidates.csv`
- 구조 비교: `/.work/ys6-standalone-runtime-trace/structural-candidates.csv`
- 대상별 판정: `/.work/ys6-standalone-runtime-trace/runtime-path-map.json`
- 사람이 읽는 요약: `/.work/ys6-standalone-runtime-trace/summary.md`
- 필요 시 PPSSPP 로그·메모리 덤프 및 설정 백업
- 분석 스크립트: `/tools/scripts/ys6_standalone_runtime_trace.py`
- 테스트: `/tools/scripts/tests/test_ys6_standalone_runtime_trace.py`
- 결과 문서: `/docs/result/022-ys6-standalone-only-runtime-path-trace.md`

CSV는 UTF-8 BOM, JSON과 Markdown은 UTF-8로 저장한다. PowerShell 콘솔 코드페이지와 무관하게 Python 출력을 UTF-8로 명시한다.

이번 단계에서는 `/patched`에 새 ISO를 생성하지 않는다.

## 완료 조건

- 미반영 번역 35개와 대상 XSO 21개가 manifest에 고정된다.
- 원본 ISO 전체 파일과 알려진 컨테이너가 읽기 전용으로 조사된다.
- 대상별 압축·비압축 payload와 고유 문자열 검색 결과가 기록된다.
- 이름 후보와 구조적 변형 후보가 분리돼 기록된다.
- 파일명만으로 확정한 대응이 없다.
- 게임에서 접근 가능한 우선 표본은 정적 또는 PPSSPP 런타임 증거로 판정된다.
- 접근할 수 없는 항목은 근거 없이 확정하지 않고 `unresolved`로 남긴다.
- PPSSPP를 사용했다면 설정이 원복되고 백업과 원복 결과가 기록된다.
- 원본 ISO와 021 ISO가 변경되지 않는다.
- 전체 테스트와 Python 바이트코드 컴파일이 통과한다.
- 확정된 항목을 021 빌더에 연결하기 위한 필드와 제약이 문서화된다.
- 결과 문서에 후속 패치 구현 또는 추가 런타임 추적 범위를 제안한다.

## 중단 및 재확인 조건

다음 상황에서는 임의로 진행하지 않고 계획을 갱신한 뒤 사용자에게 확인받는다.

- 원본 ISO 또는 입력 정본 SHA-256 불일치
- 대상 수가 확정한 21개 XSO·35개 번역과 달라 조사 범위가 다시 크게 변함
- 새 아카이브·압축 포맷 파서 구현이 필요함
- EBOOT 또는 PRX의 본격적인 역공학·디스어셈블이 필요함
- PPSSPP 설정 변경, 프로세스 종료 또는 사용자 게임 조작이 필요함
- 시험 패치 ISO 생성이 필요함
- 메모리 쓰기, 코드 후킹 또는 치트가 필요함
- 세이브·세이브 스테이트 변경이 필요함
- 원본이나 기존 패치 ISO 수정이 필요함

## 후속 작업

확정된 런타임 경로는 별도 계획에서 020 대응 정본과 021 통합 빌더에 추가한다. `standalone_only`가 직접 로드되는 것으로 확인되면 다중 ISO 패처의 일반 파일 교체 대상으로 지원하고, embedded/variant라면 해당 컨테이너 전용 안전 교체 로직을 먼저 구현한다. 미확정 항목은 사용자가 실제 등장 위치를 찾았을 때 런타임 추적을 재개한다.

## 정적 조사 진행 결과 (2026-08-12)

- 조사 대상: standalone XSO 21개, 번역 35개
- ISO 파일: 9,292개
- 전체 테스트: 67건 통과
- Python 바이트코드 컴파일: 통과
- 정확·문자열 hit: 98건
- 이름 후보: 97건
- 구조 비교 후보: 97건
- 정적 상태: `embedded_exact` 11개, `direct_standalone_candidate` 10개

중요 발견:

1. `oruhamove.xso.z`는 `PSP_GAME/USRDIR/data/arc/s_0202.bin`의 엔트리 19 `OruhaMove.xso.z`와 압축 바이트가 완전히 같다.
2. `adolsleep.xso.z`는 `PSP_GAME/USRDIR/data/arc/s_020a.bin`의 엔트리 16 `AdolSleep.xso.z`와 압축 바이트가 완전히 같다.
3. 두 엔트리의 flags는 `0x41000000`이다. 계획 020 파서는 일반 파일 flags `0x01000000`만 XSO로 집계했기 때문에 이 보조 엔트리 71개를 누락했다.
4. `OruhaMove.xso.z`: 오프셋 `0x1A5000`, 크기 1,119바이트, 할당 2,048바이트, 여유 929바이트.
5. `AdolSleep.xso.z`: 오프셋 `0x1D800`, 크기 1,534바이트, 할당 2,048바이트, 여유 514바이트.
6. `s_hidden1` 인물명 XSO 중 9개는 `s_9000` 또는 `s_9002`의 standalone XSO와 압축 바이트가 완전히 같다.
7. 나머지 인물명 XSO는 `s_9000`, `s_9002`, `s_9012` 또는 `s_0550`에 같은 인물명 문자열을 가진 구조 변형 후보가 있다.
8. `talkkebin`과 `talktokusa`에는 동일 번역 원문을 가진 여러 맵 변형 후보가 있으나 전체 XSO 구조와 해시는 다르다.

flags 전체 조사:

- 아카이브 레코드 flags 종류: `0x00000000`, `0x01000000`, `0x40000000`, `0x41000000`
- `0x41000000` 엔트리: 1,050개
- `0x41000000` XSO 엔트리: 71개
- 현재 대상과 정확히 일치하는 보조 XSO: 2개

정적 분석으로 `oruhamove`와 `adolsleep`의 저장 위치는 확정됐지만, 실제 게임 로드 여부까지 판정하려면 해당 이벤트에서 PPSSPP 파일·메모리 추적이 필요하다. standalone 자체만 발견된 10개와 동일 파일 복사본이 있는 인물명 XSO도 어느 경로가 실제 사용되는지 런타임 확인 전에는 패치 대상으로 확정하지 않는다.

산출물 경로: `/.work/ys6-standalone-runtime-trace`

- `runtime-path-map.json`
- `targets.json`
- `iso-files.csv`
- `exact-hits.csv`
- `name-candidates.csv`
- `structural-candidates.csv`
- `auxiliary-arc-xso.csv`
- `summary.md`

원본 ISO와 021 ISO의 SHA-256은 조사 전후 동일하다.

### `AdolSleep` PPSSPP 기준 표본 검증

- 사용자가 `adolsleep` 대사 출력 직전과 출력 후에 각각 게임을 일시정지했다.
- 출력 전후 PPSSPP 프로세스 메모리에서 비압축 `AdolSleep.xso` 전체 3,096바이트가 동일 주소에 완전 일치했다.
- 출력 전후 압축 `AdolSleep.xso.z` 전체 1,534바이트도 동일 주소에 완전 일치했다.
- 정적 위치 `PSP_GAME/USRDIR/data/arc/s_020a.bin`, 엔트리 16 `AdolSleep.xso.z`, flags `0x41000000`과 압축 바이트가 일치한다.
- 따라서 `s_020a.bin#16:AdolSleep.xso.z`를 실제 런타임 대상으로 확정한다.
- 메모리 검색은 읽기 전용으로 수행했으며 쓰기·후킹·치트는 사용하지 않았다.
- PPSSPP 종료 후 설정을 백업본으로 원복했고 원복 파일 SHA-256이 백업과 일치한다.
- 원복 상태: `FileLogging=False`, `RemoteDebuggerOnStartup=False`, `RemoteDebuggerLocal=False`, `FILESYSLevel=2`, `LOADERLevel=2`, `IOLevel=2`.

이 기준 표본으로 `0x41000000`은 단순 패딩이 아니라 로더가 사용하는 보조 데이터 엔트리임이 확인됐다. 동일 형식 71개를 파일마다 반복 추적하지 않고, 020 대응표와 아카이브 파서를 이 flags 유형까지 확장해 정적으로 처리한다. 다만 standalone 직접 로드와 구조 변형 후보는 로딩 방식이 다르므로 유형별 대표 표본만 추가 검증한다.
