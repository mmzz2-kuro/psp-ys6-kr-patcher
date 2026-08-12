# Ys VI 전체 런타임 아카이브 및 XSO 대응 분석 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 완료
- 구현: 완료
- 정적 검증: 완료
- 결과 문서: `/docs/result/020-ys6-runtime-archive-xso-mapping.md`

## 배경

계획 010에서 standalone 맵 데이터의 XSO 1,194개와 문자열 7,424개를 추출했고, 계획 018에서는 이를 번역 작업공간과 GUI에서 관리할 수 있게 했다. 계획 019에서는 `s_0551.xso.z`가 실제 실행 중에는 standalone 경로가 아니라 `PSP_GAME/USRDIR/data/arc/s_0551.bin` 내부 복사본에서 읽힌다는 사실을 바탕으로 사용자 번역 9개를 정상 적용했다.

현재 검증된 런타임 대응 관계는 `s_0551` 한 건뿐이다. 게임 전체 번역을 안전하게 빌드하려면 카탈로그의 각 standalone XSO가 어느 `/data/arc` 아카이브와 내부 엔트리에 대응하는지, 동일 payload가 여러 위치에 존재하는지, 각 엔트리에 얼마의 할당 여유가 있는지를 먼저 파악해야 한다.

## 목표

1. 원본 ISO의 `PSP_GAME/USRDIR/data/arc` 아래 런타임 아카이브를 모두 열거한다.
2. 각 아카이브의 파일 테이블과 내부 엔트리를 읽기 전용으로 분석한다.
3. 내부 `.xso.z`를 검증·해제하고 비압축 payload SHA-256을 계산한다.
4. 계획 010의 standalone XSO 카탈로그와 payload 해시로 대응시킨다.
5. 일대일·일대다·다대일·미대응·해시 충돌 가능성을 구분한다.
6. 각 내부 엔트리의 실제 크기, 할당 크기, 여유 공간과 다음 엔트리 경계를 기록한다.
7. 후속 다중 아카이브 빌더가 직접 읽을 수 있는 JSON 정본과 사람이 검토할 CSV·요약 보고서를 만든다.

## 범위

이번 단계는 읽기 전용 분석이다.

- 원본 ISO, 기존 패치 ISO, EBOOT 및 아카이브를 수정하지 않는다.
- 번역문을 새로 작성하거나 기존 번역을 ISO에 반영하지 않는다.
- 할당 공간을 초과하는 아카이브의 재배치·확장은 구현하지 않는다.
- 사용자 GUI는 변경하지 않는다. 분석은 `/tools/scripts`의 Python 비GUI 스크립트로 수행한다.
- 이미지, 메뉴, 아이템명 및 실행 파일 내 시스템 문자열 분석은 별도 계획으로 남긴다.

## 원본 및 작업 경로

- 원본 ISO: `/roms/Ys VI - Napishtim no Hako (Japan).iso`
- 기준 대사 카탈로그: `/.work/ys6-full-dialogue/dialogue_catalog.json`
- 번역 작업공간: `/.work/ys6-translation-workspace/translations.json`
- 분석 작업 경로: `/.work/ys6-runtime-archive-map`
- 비GUI 분석 스크립트: `/tools/scripts/ys6_runtime_archive_map.py`
- 테스트: `/tools/scripts/tests/test_ys6_runtime_archive_map.py`

원본 ISO의 SHA-256 `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`를 분석 시작 전에 확인한다.

## 1단계: 입력 자료 검증

- 원본 ISO의 크기와 SHA-256을 확인한다.
- 대사 카탈로그의 스키마, 레코드 수, XSO 경로 수와 중복 키를 확인한다.
- 카탈로그가 참조하는 standalone `.xso.z` 또는 해제 XSO가 현재 작업공간에 존재하는지 확인한다.
- standalone XSO마다 비압축 payload SHA-256을 계산하거나 기존 기록을 검증한다.
- 누락된 입력이 있으면 ISO에서 읽기 전용으로 다시 읽되 원본 추출물은 `/.work`에만 둔다.

## 2단계: `/data/arc` 전체 열거

ISO 9660 디렉터리를 읽어 `PSP_GAME/USRDIR/data/arc`의 파일을 전수 열거한다.

아카이브별로 다음을 기록한다.

| 필드 | 의미 |
|---|---|
| `iso_path` | ISO 내부 아카이브 경로 |
| `filename` | 아카이브 파일명 |
| `extent_lba` | ISO extent 시작 LBA |
| `file_size` | 아카이브 파일 크기 |
| `sha256` | 원본 아카이브 SHA-256 |
| `parse_status` | 정상·미지원·손상·비대상 상태 |
| `entry_count` | 내부 파일 테이블 엔트리 수 |

기존 `ys6_arc.py`가 처리할 수 없는 변형이 발견되면 즉시 일반화하지 않고 구조 차이를 보고한다.

## 3단계: 아카이브 엔트리 분석

각 정상 아카이브에서 내부 파일 테이블을 파싱하고 다음 정보를 수집한다.

- 엔트리 인덱스와 이름
- flags 및 레코드 오프셋
- 데이터 오프셋과 실제 크기
- 다음 엔트리까지의 할당 크기
- 남은 여유 공간
- 원시 데이터 SHA-256
- `.z` 컨테이너 여부와 무결성
- `.xso.z` 여부

다음 조건을 오류로 검사한다.

- 중복 또는 역행 오프셋
- 아카이브 범위를 벗어나는 크기
- 엔트리 데이터 중첩
- 이름 테이블 손상
- 할당 크기보다 큰 실제 크기
- `.z` 헤더, zlib EOF, 비압축 크기 또는 CRC32 불일치

## 4단계: XSO payload 지문 생성

정상 `.xso.z` 엔트리는 메모리 또는 임시 작업 파일에서 해제해 다음을 기록한다.

- 압축 컨테이너 SHA-256
- 비압축 XSO SHA-256
- XSO 크기
- 문자열 수
- XSO 구조 검증 결과
- 압축 크기, 할당 크기 및 현재 여유 공간

대용량 데이터를 한꺼번에 메모리에 보관하지 않고 아카이브 단위로 순차 처리한다. 임시 payload가 필요하면 `/.work/ys6-runtime-archive-map/tmp`에 두고 성공 시 정리한다.

## 5단계: standalone XSO 대응

카탈로그 XSO와 런타임 엔트리를 비압축 payload SHA-256으로 연결한다. 파일명만 같은 경우는 확정 대응으로 취급하지 않는다.

대응 상태:

| 상태 | 의미 |
|---|---|
| `exact_one_to_one` | standalone 1개와 런타임 엔트리 1개가 해시로 일치 |
| `runtime_duplicate` | 하나의 standalone payload가 여러 런타임 엔트리에 존재 |
| `standalone_duplicate` | 여러 standalone 경로가 동일 payload를 공유 |
| `many_to_many` | 양쪽에 동일 payload 중복이 존재 |
| `standalone_only` | 카탈로그에는 있으나 런타임 아카이브에서 찾지 못함 |
| `runtime_only` | 런타임에는 있으나 카탈로그에 대응 XSO가 없음 |
| `invalid` | 압축 또는 XSO 구조 검증 실패로 대응 불가 |

파일명·맵 ID·경로 유사성은 보조 정보로만 기록하며, 해시가 다른 항목을 자동 확정하지 않는다.

계획 018에서 확인한 `s_0551`의 payload SHA-256 `1BA1D501FEF350045691CA15F3A4F99205623C829F3B916FEA566E3978175614`가 동일한 대응으로 다시 검출되는지를 기준 회귀 검증으로 사용한다.

## 6단계: 산출물 스키마

JSON 정본 `runtime_archive_xso_map.json`에는 최소한 다음 최상위 항목을 둔다.

- `schema_version`
- 원본 ISO 경로·크기·SHA-256
- 생성 시각과 도구 버전
- `summary`
- `archives`
- `runtime_entries`
- `standalone_xso`
- `mappings`
- `unmatched`
- `errors`

CSV는 다음 세 파일로 나눈다.

- `archive_inventory.csv`: 아카이브별 요약
- `xso_runtime_mapping.csv`: standalone XSO와 런타임 엔트리 대응
- `xso_allocation_report.csv`: 실제 크기·할당 크기·여유 공간 및 대응 상태

모든 CSV는 PowerShell과 Windows 스프레드시트에서 한글 경로가 깨지지 않도록 UTF-8 BOM으로 저장한다. JSON은 UTF-8로 저장하고 콘솔 출력도 UTF-8로 명시한다.

## 7단계: 요약 및 위험도 분류

후속 빌드 설계를 위해 다음 통계를 계산한다.

- 전체 아카이브 수와 정상 파싱 수
- 전체 엔트리 및 `.xso.z` 엔트리 수
- 카탈로그 XSO 1,194개 중 확정 대응 수
- 중복·미대응·오류 수
- 여유 공간 0바이트인 엔트리 수
- 여유 공간 구간별 분포
- 현재 압축 크기가 할당 공간의 90% 이상인 고위험 엔트리
- 아카이브별 XSO 수와 누적 여유 공간

여유 공간은 현재 일본어 원본 기준일 뿐 번역 후 수용 가능성을 보장하지 않는다고 명시한다. 번역문을 실제 적용한 압축 크기 예측은 후속 통합 빌더 범위다.

## 8단계: 검증

- 동일 입력으로 두 번 실행했을 때 경로·해시·대응 결과가 동일한지 확인한다.
- 모든 아카이브 엔트리가 정확히 하나의 아카이브 범위 안에 있는지 확인한다.
- `.xso.z`로 분류된 모든 정상 엔트리의 압축 해제와 XSO 파싱을 검증한다.
- `s_0551` 기준 대응이 기존 결과와 일치하는지 확인한다.
- 카탈로그의 XSO 수와 대응 상태 합계가 일치하는지 확인한다.
- 런타임 XSO 수와 대응 상태 합계가 일치하는지 확인한다.
- JSON을 다시 읽어 스키마 필수 필드와 참조 키 무결성을 검사한다.
- CSV 행 수가 JSON 대응 배열과 일치하는지 확인한다.
- 단위 테스트와 Python 바이트코드 컴파일을 실행한다.
- 분석 전후 원본 ISO SHA-256이 동일한지 다시 확인한다.

## 예상 변경 및 생성 파일

- 새 스크립트: `/tools/scripts/ys6_runtime_archive_map.py`
- 새 테스트: `/tools/scripts/tests/test_ys6_runtime_archive_map.py`
- 분석 JSON: `/.work/ys6-runtime-archive-map/runtime_archive_xso_map.json`
- 아카이브 CSV: `/.work/ys6-runtime-archive-map/archive_inventory.csv`
- 대응 CSV: `/.work/ys6-runtime-archive-map/xso_runtime_mapping.csv`
- 할당 CSV: `/.work/ys6-runtime-archive-map/xso_allocation_report.csv`
- 요약 보고서: `/.work/ys6-runtime-archive-map/summary.md`
- 결과 문서: `/docs/result/020-ys6-runtime-archive-xso-mapping.md`

이번 단계에서는 `/patched` 아래에 새 ISO를 만들지 않는다.

## 완료 조건

- `/data/arc`의 모든 파일이 열거되고 파싱 상태가 기록된다.
- 모든 정상 `.xso.z` 엔트리의 압축·XSO 무결성과 payload 해시가 기록된다.
- 카탈로그 XSO 1,194개가 빠짐없이 대응 상태 중 하나로 분류된다.
- 모든 런타임 XSO 엔트리가 대응 상태 중 하나로 분류된다.
- 중복과 미대응 항목을 숨기지 않고 별도 목록으로 제공한다.
- 각 XSO 엔트리의 실제 크기·할당 크기·여유 공간이 기록된다.
- `s_0551` 대응이 기존 검증 결과와 일치한다.
- JSON·CSV·요약 보고서의 합계와 참조 무결성이 일치한다.
- 전체 테스트와 Python 바이트코드 컴파일이 통과한다.
- 원본 ISO가 변경되지 않았음을 SHA-256으로 확인한다.
- 결과 문서에 후속 통합 빌더 및 아카이브 재배치 작업의 우선순위를 제안한다.

## 중단 및 재확인 조건

다음 상황에서는 구조를 추정해 계속하지 않고 계획을 갱신한 뒤 사용자에게 확인받는다.

- 기존 `ys6_arc.py`와 다른 아카이브 포맷이 발견되어 새 파서가 필요함
- 암호화 또는 알 수 없는 압축 방식 때문에 payload를 검증할 수 없음
- 해시만으로 구분할 수 없는 수정·변형 XSO가 대량으로 발견됨
- 원본 ISO의 예상 SHA-256이 일치하지 않음
- 분석을 위해 원본 또는 패치 ISO 수정이 필요함
- 대규모 임시 추출로 예상 저장 공간이 현저히 증가함
- 아카이브 재배치·확장 또는 실행 코드 분석이 필요함

## 후속 작업

020 결과를 기반으로 별도 계획에서 다음을 진행한다.

1. 검수 번역을 여러 XSO와 런타임 아카이브에 일괄 적용하는 통합 빌더
2. 빌드 전 압축 크기와 엔트리 할당 초과를 보고하는 사전 검사
3. 기존 할당을 초과한 엔트리가 있는 아카이브의 안전한 전체 재배치
4. 이벤트 또는 챕터 단위 번역·검증 및 최종 사용자용 GUI 패치 도구 연계
