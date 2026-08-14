# 046. 대사 외 시스템·아이템·이미지 자원 전수 조사 결과

> 정정: 후속 048 검증에서 `invinfo.dat` 이름 영역은 52바이트가 아니라 32바이트이며, 뒤의 20바이트는 가격·능력치 데이터로 확인됐다. 최종 구조는 이름 32바이트, 메타데이터 44바이트, 설명 108바이트다. 자세한 내용은 `docs/result/048-ys6-invinfo-price-field-boundary-fix.md`를 따른다.

## 결론

다음 구현 대상으로는 **아이템·장비 이름과 설명**이 가장 적합하다. PSP판과 Windows 한글판 `invinfo.dat`는 레코드 크기와 개수가 같고, 73개 레코드의 비문자 메타데이터가 모두 바이트 단위로 일치한다. Windows판의 한국어 이름·설명을 PSP용 글자 코드로 변환하는 방식으로 재사용할 수 있다.

이미지는 PSP 메뉴 폴더에서 166개, ISO 전체에서 MIG 텍스처 1,373개를 찾았다. 다만 Windows판 메뉴 이미지 58개와 파일명이 정확히 같은 것은 `map.dds` 하나뿐이며, PSP판은 `MIG.00.1PSP`, Windows판은 일반 DDS이므로 직접 복사는 불가능하다. 화면 의미 매핑과 MIG 재인코더가 필요하다.

시스템 메시지는 암호화된 `BOOT.BIN`/EBOOT에 단순 CP932 검색을 적용하면 오탐이 대부분이다. 런타임 메모리 덤프나 실행 코드의 문자열 참조 추적을 별도 단계로 진행해야 한다.

원본 ISO와 기존 패치 ISO는 수정하지 않았다.

## ISO 인벤토리

- 원본: `roms/Ys VI - Napishtim no Hako (Japan).iso`
- SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 파일: 9,292개
- `.z`: 8,459개
- `.vag`: 305개
- `.bin`: 227개
- `.dds`: 201개
- MIG 텍스처: 1,373개
- 해제 오류: 1개
  - `PSP_GAME/USRDIR/data/map/s_90/s_9021/s_9021__w.yco.z`
  - 일반 Ys VI zlib 래퍼와 다른 예외 파일이며 이번 핵심 대상에는 영향이 없다.

단순 CP932 탐색으로 2,993개 파일에서 140,983개 후보가 나왔으나 모델·맵 바이너리의 우연한 바이트열이 다수 포함된다. 이 수치는 번역 문자열 수로 사용할 수 없다.

## 아이템·장비 테이블

### 위치와 구조

- ISO 경로: `PSP_GAME/USRDIR/data/misc/invinfo.dat`
- 파일 크기: 13,448바이트
- 헤더: 16바이트
- 레코드: 184바이트 × 73개
- 레코드 배치:
  - `0x00..0x33` (52바이트): 표시 이름 영역
  - `0x34..0x4B` (24바이트): 리소스 ID, 가격·능력치 등 메타데이터
  - `0x4C..0xB7` (108바이트): 표시 설명 영역

Windows판 `misc/invinfo.dat`도 파일 크기·레코드 크기·개수가 정확히 같다. 73개 레코드의 24바이트 메타데이터 비교 결과 불일치는 0개다. 차이는 헤더 일부와 이름·설명 영역에만 있다.

따라서 인덱스와 리소스 ID 기준 대응이 가능하다. 확인된 예시는 다음과 같다.

| 인덱스 | ID | 일본어 | Windows 한글판 |
|---:|---|---|---|
| 0 | `sw_00` | リヴァルト | 리발트 |
| 1 | `sw_01` | ブリランテ | 브릴란테 |
| 2 | `sw_02` | エリクシル | 에릭실 |
| 3 | `sw_03` | ロングソード | 롱 소드 |
| 67 | `ky_19` | カナンの地図 | 카난 지도 |

Windows판 문자열은 첫 NUL 이후에 원래 일본어 잔여 바이트가 남는 레코드가 있다. 표시 문자열은 반드시 첫 NUL까지만 읽어야 한다.

73개 중 72개는 현재 Windows 한글 문자표로 완전히 해독된다. 인덱스 64 `姉の威光` 설명의 인용부호 코드 `97D7`, `97D8`만 미해결이다. PSP에서 이미 지원하는 유사 인용부호로 치환하거나 문자표에 의미를 확정하면 된다.

산출물:

- `.work/ys6-non-dialogue-inventory/items/items.json`
- `.work/ys6-non-dialogue-inventory/items/items.csv`
- `tools/scripts/ys6_invinfo_inventory.py`

`enemyinfo.dat`는 264바이트 × 70레코드지만 의미 있는 일본어 이름 문자열이 없고 수치 데이터 중심이다. 적 이름은 기존 `castinfo.dat` 계열에서 처리하는 것이 맞다. `gameinfo.dat`와 `eex.dat`도 현재 확인 범위에서는 설정·수치 데이터이며 번역 우선 대상이 아니다.

## 이미지 자원

### 확인된 구조

`.dds`라는 확장자와 달리 PSP 자산의 실제 매직은 `MIG.00.1PSP`이다. `title_000.dds` 분석에서 다음을 확인했다.

- 텍스처 크기: 512×256
- 픽셀 형식: 8비트 인덱스
- 팔레트: RGBA8888, 256색
- 이미지와 팔레트가 별도 MIG 하위 섹션으로 구성됨

파서와 시험 렌더러를 `tools/scripts/ys6_mig_texture.py`에 작성했다. 다만 시험 PNG에는 반복 줄무늬와 색상 오염이 남아 있어 PSP 스위즐/CLUT 배열을 완전히 해석한 상태는 아니다. 현재 PNG는 구조 진단용이며 편집 원본으로 사용하면 안 된다.

진단 산출물:

- `.work/ys6-non-dialogue-inventory/images/title_000.png`
- `.work/ys6-non-dialogue-inventory/images/title_000.json`

우선 확인할 이미지 후보:

- `data/image/title_000.dds(.z)` — 타이틀
- `data/image/gameover.dds` — 게임 오버
- `data/image/placename00.dds.z`
- `data/image/placename01.dds.z`
- `data/image/placename02.dds.z` — 지역명 계열
- `data/menu/map.dds.z` — Windows판과 파일명이 같은 유일한 메뉴 자산
- `data/menu/` 아래 166개 — 메뉴 및 장비 UI 후보

Windows판 `menu`에서 추출한 DDS는 58개다. 파일명 정확 일치는 `map.dds` 하나뿐이고 해상도도 다르다. 예를 들어 Windows `map.dds`는 2,097,280바이트인 반면 PSP의 해제 payload는 38,604바이트다. 번역 문구와 레이아웃은 참고할 수 있지만 바이트 단위 이식은 불가능하다.

Windows 이미지 산출물:

- `.work/ys6-non-dialogue-inventory/windows-menu/menu/`

## 시스템 메시지

원본 ISO의 `BOOT.BIN` 및 보관된 `original-eboot.bin`에서 단순 CP932 후보를 조사했으나, 실행 코드와 압축·암호화 데이터가 일본어처럼 우연히 해독된 오탐이 대부분이었다. 신뢰할 수 있는 시스템 문구 테이블은 이번 정적 검색만으로 확인하지 못했다.

다음 조사에서는 아래 중 하나가 필요하다.

1. 시스템 문구가 화면에 뜬 시점의 메모리 덤프 전후 차분
2. 이미지 로드 경로와 텍스트 렌더 함수의 호출 참조 추적
3. Windows판 시스템 문구를 기준으로 PSP 메모리에서 인코딩 변형 검색

단순 후보 2,583개를 번역 목록으로 노출하는 방식은 오탐 위험이 커서 채택하지 않는다.

## 추가·변경 파일

- 추가: `tools/scripts/ys6_non_dialogue_inventory.py`
- 추가: `tools/scripts/ys6_invinfo_inventory.py`
- 추가: `tools/scripts/ys6_mig_texture.py`
- 갱신: `docs/plan/046-ys6-non-dialogue-resource-inventory.md`
- 추가: `docs/result/046-ys6-non-dialogue-resource-inventory.md`

## 검증

- ISO 전체 스트리밍 SHA-256 및 9,292개 파일 순회 완료
- `.z` payload 해제 및 SHA-256 기록 완료
- `invinfo.dat` 양쪽 73개 레코드 경계 검증 완료
- 아이템 메타데이터 불일치 0개 확인
- Windows 한글 아이템 73개 추출, 미해결 문자 포함 항목 1개 확인
- MIG 섹션, 크기, 픽셀 형식 및 팔레트 구조 확인
- 원본·패치 ISO 쓰기 없음

## 후속 작업 권장 순서

1. **아이템 작업공간 및 빌더 구현**
   - 73개 이름·설명을 GUI에서 검토하고 PSP 글자 코드로 변환
   - 고정 영역 길이 초과 검사
   - `invinfo.dat` 독립 파일과 런타임 아카이브 복사본 동시 반영 여부 확인
2. **MIG 디코더/인코더 완성**
   - 스위즐과 CLUT 순서를 확정
   - decode→encode 무변경 round-trip 해시 검증
   - 1,373개 썸네일 시트 생성 및 일본어 포함 이미지 선별
3. **시스템 메시지 런타임 추적**
   - 저장·불러오기, 옵션, 확인창 등 접근 쉬운 화면부터 메모리 차분
4. **이미지 번역**
   - Windows판을 레이아웃 참고 자료로 사용해 PSP 해상도에 맞게 재제작

## 임시 파일 정리

`.work/ys6-non-dialogue-inventory/`에는 ISO 인벤토리, Windows 비교 파일, 시험 PNG가 있다. 후속 아이템 및 MIG 작업의 입력이므로 현재 유지한다. 새 테스트 ISO는 생성하지 않았다.
