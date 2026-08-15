# 049. 시스템 메뉴 메시지 위치 조사 중간 기록

> **정정:** 이 문서의 최초 결론이었던 “시스템 안내 문구가 메뉴 이미지에 포함돼 있다”는 판단은 잘못됐다. 사용자가 제시한 실제 화면에서 기존에 교체한 한글 글리프가 시스템 안내 문구 안에 출력되는 것이 확인됐다. 이는 해당 문구가 EBOOT 내장 폰트를 사용하는 동적 텍스트라는 직접 증거다. 아래의 이미지 자원 대응은 배경 자원 후보 기록일 뿐 문구 저장 위치로 확정하지 않는다. 049 조사는 완료되지 않았으며 재개 상태다.

## 결론

조사한 시스템 안내 문구는 EBOOT 내장 폰트로 렌더링되는 동적 텍스트다. 저장 인코딩은 대사에서 사용한 CP932가 아니라 **EUC-JP**다. 장비 메뉴 문구 `装備全般の設定を行います。`는 현재 EBOOT와 ISO에서 원문 바이트열이 확인됐다.

## 장비 메뉴 런타임 추적 결과

- 장비 메뉴 문자열 복사 직전 PC: `0x088D7BE4`
- 메뉴 객체 기준 주소(`s3`): `0x08B4FF20`
- 문자열 필드: `s3 + 0x730 = 0x08B50650`
- 스택 출력 버퍼: `0x09FFA8B0`
- 문자열 인코딩: EUC-JP
- 현재 EBOOT 파일 오프셋: `0x12CF34`
- 원본 ISO 파일 오프셋: `0x33904F34`

EUC-JP 원문 바이트는 `C1 F5 C8 F7 C1 B4 C8 CC A4 CE C0 DF C4 EA A4 F2 B9 D4 A4 A4 A4 DE A4 B9 A1 A3 00`이다. CP932 검색에서 발견되지 않았던 원인은 인코딩 가정이 잘못됐기 때문이다.

| 화면 문구 | 관련 배경 자원 후보(문구 저장 위치로 확정하지 않음) |
| --- | --- |
| `データをセーブします。` | `PSP_GAME/USRDIR/data/menu/savebg00.dds.z` ~ `savebg02.dds.z` |
| `アイテムを使用します。` | `PSP_GAME/USRDIR/data/menu/itembg_s00.dds.z` ~ `itembg_s07.dds.z` |
| `システムの設定を行います。` | `PSP_GAME/USRDIR/data/menu/optionbg00.dds.z` ~ `optionbg02.dds.z` |

이 문구를 번역하려면 실제 시스템 문자열 테이블 또는 조립 코드를 먼저 찾아야 한다. MIG 이미지 교체 대상으로 처리해서는 안 된다.

## 확인한 화면

- 저장 슬롯 화면 하단: `データをセーブします。`
- 아이템 화면 하단: `アイテムを使用します。`
- 옵션 화면 하단: `システムの設定を行います。`
- 옵션 화면에는 `BGMのボリューム`, `効果音のボリューム`, `標準に戻す`, `キーコンフィグ`, `操作説明`, `タイトル画面に戻る`도 함께 이미지 형태로 표시된다.

## 정적 검색 결과

`tools/scripts/ys6_system_string_search.py`로 다음 범위를 검색했다.

- ISO 파일 9,292개
- `.z` 해제 payload 8,458개
- `data/arc/*.bin` 아카이브 222개
- 아카이브 엔트리 6,693개
- CP932, UTF-16LE, UTF-16BE 변형

세 문장 전체는 어느 정적 문자열 영역에서도 발견되지 않았다. 발견된 `セーブ` 단독 문자열은 효과 정의, 장면 목록 및 세이브 포인트 이름이며 화면 하단 안내 문구와 무관했다.

Windows판에서는 저장·확인 문구가 DDS 이미지에 포함된 사례를 확인했다. PSP판도 `data/menu` 아래에 화면별 대응 배경 텍스처 묶음을 갖고 있어 이미지 방식이라는 판단을 뒷받침한다.

## 런타임 확인

`tools/scripts/ys6_runtime_string_diff.py`로 PPSSPP의 PSP RAM 미러와 렌더 버퍼를 덤프했다.

- 저장 화면과 일반 게임 화면 RAM 비교
- 아이템 사용 화면 RAM 및 렌더 버퍼 확보
- 옵션 시스템 설정 화면 RAM 및 렌더 버퍼 확보
- 전체 문장과 구성 단어를 CP932로 검색

전체 문장은 런타임 PSP RAM에도 연속 문자열로 존재하지 않았다. 아이템 화면 렌더러 캐시에서 `アイテムを使用し` 16바이트 조각이 한 번 확인됐지만, 이는 원문 저장소가 아니라 렌더 캐시 키로 판단된다. 옵션 문장 역시 원문 문자열로 남지 않았다.

## 생성·변경 파일

- `tools/scripts/ys6_system_string_search.py`
- `tools/scripts/ys6_runtime_string_diff.py`
- `.work/ys6-system-message-location/exact-search.json`
- `.work/ys6-system-message-location/item-use-static-search.json`
- `.work/ys6-system-message-location/system-settings-static-search.json`
- `.work/ys6-system-message-location/item-use-ram.bin`
- `.work/ys6-system-message-location/item-use-render.bin`
- `.work/ys6-system-message-location/item-other-ram.bin`
- `.work/ys6-system-message-location/item-other-render.bin`

## 재개 조사 항목

1. 시스템 문구가 사용하는 글리프 코드열을 런타임 렌더 호출 직전에서 확보
2. 코드열 또는 포인터를 복호화 EBOOT와 공통 아카이브에 역추적
3. 문자열이 조각 단위라면 문구 ID와 조각 테이블 구조 확인
4. 기존 `font-usage.json`이 누락한 시스템 문구 글리프 사용량 재산정
5. 한글에 배정한 일본어 코드와 시스템 문구의 충돌 목록 작성

## ROM 처리

- 원본 ISO는 읽기만 했으며 수정하지 않았다.
- 새 ISO를 생성하지 않았다.
- 이번 조사에서 정리할 테스트 ROM은 없다.

## 알려진 문제

시스템 문구는 일반 CP932·UTF-16 원문 검색으로 발견되지 않는다. 다음 단계에는 렌더 함수 직전 버퍼 또는 호출 인자를 추적할 수 있는 PPSSPP 디버거 조사가 필요하다.
