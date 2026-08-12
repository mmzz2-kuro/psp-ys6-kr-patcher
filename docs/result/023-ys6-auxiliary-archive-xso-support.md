# Ys VI 보조 아카이브 XSO 및 AskOruha 런타임 대응 결과

## 상태

- 작업 번호: 023
- 구현: 완료
- 정적 검증: 완료
- 인게임 검증: 완료
- 완료일: 2026-08-12

## 결과 요약

아카이브 flags `0x41000000`을 런타임에서 사용하는 보조 데이터 엔트리로 지원했다. 일반 XSO와 보조 XSO를 하나의 통합 빌드에서 처리하고, 명시적으로 확인된 standalone 직접 로드 파일도 같은 수정 컨테이너로 교체할 수 있게 했다.

오르하 선택지는 최초 번역 대상인 `s_0202/OruhaMove` 외에 실제 메뉴용 `s_0203/AskOruha`에도 별도로 저장되어 있었다. 전체 원문과 분기 식별자를 비교해 9개 문장의 1:1 대응을 확인한 뒤, 사용자 승인을 받아 `AskOruha`로 번역을 복사했다. 아카이브와 standalone 사본을 모두 반영한 최종 ISO에서 사용자가 한글 출력을 확인했다.

## 수행 내용

### 아카이브 및 런타임 대응

- 일반 데이터 flags: `0x01000000`
- 보조 데이터 flags: `0x41000000`
- 데이터 엔트리 전체를 기준으로 실제 할당 경계를 계산하도록 수정
- 엔트리 이름뿐 아니라 index·name·flags를 모두 검증해 정확한 대상을 선택
- 런타임 대응표 스키마를 v2로 올리고 보조 XSO를 포함
- 일반 XSO 344개와 보조 XSO 71개, 총 415개 확인
- 대응 분석 오류 0건

### 번역 검수

- `s_0551`: 29개
- `AdolSleep`: 4개
- `s_0202/OruhaMove`: 9개
- `s_0203/AskOruha`: 대응 복사 9개
- 최종 검수 레코드: 51개
- 일본어 후리가나용 ruby 마크업 제거 3건은 사용자 승인 후 해당 레코드에만 예외 기록
- `s_0551` index 56은 기존에 승인된 두 줄 보정 적용
- 사용자 번역 정본 `.work/ys6-translation-workspace/translations.json`은 변경하지 않음

### 오르하 선택지 원인

다음 두 XSO에 같은 표시 문자열과 분기 식별자가 저장되어 있었다.

- `s_0202/OruhaMove`: 선택지 인덱스 16, 18, 20, 22, 24, 26, 27, 29, 31
- `s_0203/AskOruha`: 대응 인덱스 1, 3, 5, 7, 9, 11, 12, 14, 16

`AboutTail`, `AboutReda`, `AboutEresia`, `AboutKanan`, `AboutIsha`, `AboutMan`, `AboutOdo`, `EndTalk` 순서까지 일치했다. `OruhaMove`만 수정한 ISO에서는 일본어였고 `AskOruha`까지 수정한 ISO에서 한글 출력이 확인됐다.

## 최종 ISO

- 경로: `/patched/023-auxiliary-xso-support/Ys VI - ask-oruha-runtime-korean-build.iso`
- SHA-256: `754DD1A6A123C2DF6EAB97975FD58CD83B47044BEEAE125529FD3B91F48511A0`
- 크기: 원본 ISO와 동일

교체된 ISO 내부 파일 7개:

1. `PSP_GAME/SYSDIR/EBOOT.BIN`
2. `PSP_GAME/USRDIR/data/arc/s_0202.bin`
3. `PSP_GAME/USRDIR/data/arc/s_0203.bin`
4. `PSP_GAME/USRDIR/data/arc/s_020a.bin`
5. `PSP_GAME/USRDIR/data/arc/s_0551.bin`
6. `PSP_GAME/USRDIR/data/map/s_02/s_0202/oruhamove.xso.z`
7. `PSP_GAME/USRDIR/data/map/s_02/s_0203/askoruha.xso.z`

## 용량 검증

| XSO | 압축 크기 | 할당 크기 | 잔여 공간 |
|---|---:|---:|---:|
| `s_0551` | 1,877 | 2,048 | 171 |
| `OruhaMove` | 1,132 | 2,048 | 916 |
| `AdolSleep` | 1,559 | 2,048 | 489 |
| `AskOruha` | 397 | 2,048 | 1,651 |

모든 대상이 기존 할당 범위 안에 들어가며 아카이브 재배치나 ISO extent 이동은 발생하지 않았다.

## 검증 결과

- 자동 테스트 73개 통과
- Python 바이트코드 컴파일 통과
- 수정 컨테이너 압축 해제 및 XSO 재파싱 통과
- 아카이브와 standalone 수정 payload 해시 일치
- 허용된 extent 및 ISO 길이 필드 밖 변경 0건
- 원본 ISO SHA-256 유지: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 기존 023 ISO 보존

사용자 인게임 확인:

- `s_0551`: 한글 정상 출력
- `AdolSleep`: 한글 정상 출력
- 오르하 선택지(`AskOruha`): 한글 정상 출력
- 확인된 이벤트 진행 이상 없음

## 생성·변경 파일

- 수정: `/tools/scripts/ys6_arc.py`
- 수정: `/tools/scripts/ys6_runtime_archive_map.py`
- 수정: `/tools/scripts/ys6_integrated_build.py`
- 수정: `/tools/scripts/ys6_translation_workspace.py`
- 수정: 관련 자동 테스트
- 생성: `/.work/ys6-runtime-archive-map-v2`
- 생성: `/.work/ys6-auxiliary-xso-support`
- 생성: `/.work/ys6-auxiliary-xso-standalone`
- 생성: `/.work/ys6-ask-oruha-runtime`
- 생성: 최종 ISO

## 알려진 사항 및 정리 대상

- PPSSPP 메모리 추적은 최종 패치 검증에 필요하지 않았으며 설정은 기존 원복 상태를 유지했다.
- 아래 ISO는 원인 분리용 중간 검증본이며 최종본이 아니다. 필요 없으면 후속 정리 시 삭제할 수 있다.
  - `/patched/023-auxiliary-xso-support/Ys VI - auxiliary-xso-korean-build.iso`
  - `/patched/023-auxiliary-xso-support/Ys VI - auxiliary-and-standalone-korean-build.iso`
- 이번 결과 문서 작성 시에는 추적 가능성을 위해 중간 ISO를 삭제하지 않았다.
- `s_0203/OruhaMove`의 이벤트 대사 21개는 아직 번역 대상에 포함되지 않았다.
