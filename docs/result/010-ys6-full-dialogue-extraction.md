# Ys VI 전체 대사 추출 및 GUI 뷰어 결과

## 상태

- 계획 및 사용자 확인: 완료
- 전체 XSO 추출·해제·파싱: 완료
- 카탈로그 및 GUI 구현: 완료
- 정적 검증: 완료
- 인게임 위치 검증: 미수행

## 결론

원본 ISO의 `.xso.z` 1,194개를 전부 추출하고 7,424개 문자열을 CP932 손실 없이 카탈로그화했다. 대사 본문 4,754개를 비롯해 화자, 선택지, 프롬프트, 경로 및 미참조 문자열을 역할별로 검색할 수 있다. 별도 패키지가 필요 없는 Python Tkinter GUI와 JSON·CSV·HTML 결과를 함께 만들었다.

이번 단계에서는 ISO를 수정하거나 새 작업 ISO를 만들지 않았다.

## 실행 방법

저장소 루트에서 다음 명령을 실행한다.

```powershell
python tools\ys6_dialogue_viewer.py
```

기본 카탈로그가 존재하면 자동으로 열린다. 다른 위치의 카탈로그는 GUI의 `카탈로그 열기` 버튼으로 선택할 수 있다.

GUI에서 일본어 문구, 맵 ID, XSO 파일명 및 ISO 내부 경로를 통합 검색할 수 있으며 역할 필터를 함께 적용할 수 있다. 행을 선택하면 문자열 인덱스, CP932 바이트 길이, 파일 오프셋, opcode 참조, 토큰과 마크업을 표시한다. 읽기 전용 뷰어이므로 원본이나 카탈로그를 수정하지 않는다.

## 전체 추출 결과

| 항목 | 개수 |
|---|---:|
| ISO 내 `.xso.z` | 1,194 |
| 추출 파일 | 1,194 |
| 정상 해제·파싱 | 1,194 |
| 오류 | 0 |
| 전체 문자열 | 7,424 |

### 역할별 문자열

| 역할 | 개수 |
|---|---:|
| 대사 본문 `dialogue` | 4,754 |
| 화자 `speaker` | 53 |
| 선택지 `choice` | 280 |
| 선택 프롬프트 `choice_prompt` | 139 |
| 선택 심볼 `choice_symbol` | 279 |
| 이벤트 심볼 `event_symbol` | 13 |
| 리소스명 `resource_name` | 637 |
| 스크립트 경로 `script_path` | 194 |
| 미참조 `unreferenced` | 1,607 |

한 문자열이 여러 opcode에서 사용되면 역할을 중복 보존하므로 역할 합계는 전체 문자열 수와 일치하지 않을 수 있다.

### 제어 토큰

| 토큰 | 발견 횟수 |
|---|---:|
| `\\n` | 3,743 |
| `\\s` | 217 |
| `\\x1` | 313 |
| `\\x3` | 8 |
| `\\x4` | 16 |

색상, 루비 및 글자 배율 마크업도 원문 그대로 보존했다. `\\x3`, `\\x4`의 정확한 동작 의미는 아직 미확정이다.

## 산출물

- 추출 스크립트: `/tools/scripts/ys6_dialogue_extract.py`
- GUI: `/tools/ys6_dialogue_viewer.py`
- 테스트: `/tools/scripts/tests/test_ys6_dialogue_extract.py`
- 압축 원본 트리: `/.work/ys6-full-dialogue/compressed`
- 해제 XSR 트리: `/.work/ys6-full-dialogue/decompressed`
- 기준 카탈로그: `/.work/ys6-full-dialogue/catalog/dialogue_catalog.json`
- Excel 호환 UTF-8 BOM CSV: `/.work/ys6-full-dialogue/catalog/dialogue_catalog.csv`
- 브라우저용 단일 HTML: `/.work/ys6-full-dialogue/catalog/dialogue_catalog.html`

카탈로그 해시:

| 파일 | SHA-256 |
|---|---|
| JSON | `40D708B7BE0F33F30EDCFF7639B7A755828258CDD546C6032C8F586DF5571624` |
| CSV | `D7F1C0CB21FB35A3D7C6933889FC5A7A7BB5F6BBA843FBC193ED01DDA295B61C` |
| HTML | `8B0FBEAD7EFB725AE065C5074D78DD204A44484E5AE4E2D3887E307B9B5E7302` |

## 검색 및 확인 표본

기존 PoC 원문 `ここで何をしているかだって？`를 대사 역할로 검색했을 때 정확히 한 건이 검출됐다.

- 경로: `PSP_GAME/USRDIR/data/map/s_00/s_0000/talkkebin.xso.z`
- 문자열 인덱스: 4
- CP932 길이: 28바이트

초반 지역으로 추정되는 `s_00/s_0000`에서 토큰과 마크업이 없는 짧은 대사 후보도 확인했다.

| XSO | 인덱스 | 바이트 | 원문 |
|---|---:|---:|---|
| `selno` | 0 | 32 | `兄弟、俺とお前の仲じゃないか……` |
| `seltalk` | 6 | 34 | `いやいや、吊り橋が直ったそうだね。` |
| `seltalk` | 18 | 26 | `リモージュには着けたかい？` |
| `talkkebin` | 4 | 28 | `ここで何をしているかだって？` |
| `talkkuvaru` | 9 | 36 | `ささやかだが、これは私からのお礼だ。` |
| `talkmavu` | 1 | 22 | `もう知らないんだから！` |

맵 번호와 파일명에 따른 초반 접근 가능성은 정적 추정이다. 실제 표시 시점과 NPC는 PPSSPP 또는 사용자 플레이로 확인해야 한다.

## 검증

- 7,424개 문자열의 `raw_hex`를 CP932로 디코드한 뒤 재인코딩하여 전부 원시 바이트와 일치함을 확인했다.
- 1,194개 `.z` 모두 CRC32, 비압축 크기, zlib 스트림 종료와 XSR 구조 검사를 통과했다.
- JSON 파일 수 1,194, 오류 수 0을 확인했다.
- CSV UTF-8 BOM과 HTML 일본어 포함 여부를 확인했다.
- 동일 입력 재실행 후 JSON·CSV·HTML 해시가 재현됐다.
- GUI 실제 카탈로그 로딩 결과 7,424개 레코드를 확인했다.
- GUI에서 기존 PoC 원문과 `dialogue` 역할 필터 조합이 한 건을 정확히 반환했다.
- GUI 모듈 import, Tkinter 8.6 및 Python 바이트코드 컴파일을 확인했다.
- 전체 단위 테스트 30개가 통과했다.

## 원본 보호

- 원본 ISO SHA-256은 작업 전후 동일하다: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`.
- 원본 ISO는 읽기만 했고 변경하지 않았다.
- 이번 단계에서 `/patched` 아래 새 ISO를 생성하지 않았다.
- 추출한 원본 게임 데이터는 `/.work`에만 두었으며 Git 대상이 아니다.

## 한계 및 다음 단계

- PPSSPP가 없어 GUI가 아닌 게임 화면에서 대사 위치를 확인하지 못했다.
- 정적 카탈로그만으로 이벤트 발생 조건과 정확한 NPC 위치를 확정할 수 없다.
- 다음 단계에서는 사용자가 GUI에서 접근 가능한 대사를 고르거나, PPSSPP 환경을 준비해 후보를 직접 확인한다.
- 확인할 대사가 정해지면 기존 `/patched/009-talkkebin-string-poc` 작업 ISO를 불필요하게 늘리지 않고 같은 이슈 작업본을 갱신하는 별도 계획을 작성한다.
