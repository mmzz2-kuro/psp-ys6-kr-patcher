# 055. Ys VI 추가 이미지 리소스 탐색 결과

## 상태

- 완료
- 이미지 번역 및 ISO 적용은 다음 단계로 분리

## 핵심 결과

### 로드 확인 문구

`このデータをロードしますか？`는 512×128 PSP DXT1 이미지에 세이브·로드·삭제
확인 문구와 함께 들어 있다.

- 독립 파일: `PSP_GAME/USRDIR/data/menu/saveicon2.dds.z`
- 런타임 컬렉션: `PSP_GAME/USRDIR/data/arc/init.bin`
- 아카이브 엔트리: index 29 `static_tex.dds.z`
- 컬렉션 그림: index 69, 그림 오프셋 `0xE3F50`
- 독립 파일과 내장 그림의 디코딩 RGBA: 완전 동일

### 지역명

`クアテラの樹海`는 다음 파일의 여섯 지역명 중 다섯 번째 행에 있다.

- `PSP_GAME/USRDIR/data/image/placename02.dds.z`
- 크기: 256×256
- 형식: PSP DXT3

`placename00`~`02`에서 총 22개의 지역명 이미지가 확인됐다.

## 추가 한글화 대상

- `saveicon2.dds.z`: 세이브·로드·삭제 확인 문구
- `placename00.dds.z`~`placename02.dds.z`: 지역명 22개
- `map.dds.z`: 월드맵에 직접 그려진 일본어 지명
- `itemcursor.dds.z`: 아이템 사용 확인 및 선택 안내
- `itemwin.dds.z`: 문자를 이해할 수 없다는 아이템 메시지
- `emeparts0.dds.z`: 에메라스 부족·레벨 최대 메시지
- `emeparts1.dds.z`: 검 강화 확인 메시지
- `shopp0.dds.z`: 구매·판매·취소 선택지
- `shopp1.dds.z`: 구매·판매 확인 및 Gold 부족 메시지

`itemcursor.dds.z`와 `itemwin.dds.z`는 각각 `static_tex` 그림 index 62와 61에
완전히 같은 내장 사본이 있다. 옵션 화면은 기존 작업의 그림 index 73이다.

## 이미지 컬렉션 분석

`static_tex.dds.z`는 단일 그림이 아니라 367개의 그림 섹션이 들어 있는 MIG
컬렉션이다. 새 분석 도구로 235개 지원 형식 이미지를 정상 렌더링했다.

- 지원: 팔레트 8bpp, PSP DXT1, PSP DXT3
- 전체 UI 범위 스캔: 1,170개 그림 레코드
- 렌더 성공: 880개
- 확인용 접촉 시트: 28개
- 메뉴·타이틀 축소 범위: 렌더 154개, 접촉 시트 6개

## 왕복 검증

선정한 독립 리소스 11개는 수정 없이 컨테이너를 다시 만들었을 때 다음 조건을
모두 만족했다.

- 해제 payload 동일
- 재압축 크기 원본과 동일
- ISO 할당 공간 이내

원본 ISO SHA-256도 작업 전후 다음 값으로 유지됐다.

`0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`

## 생성 파일

- `/tools/scripts/ys6_mig_collection_extract.py`
- `/tools/scripts/ys6_image_resource_inventory.py`
- `/tools/patchdata/ys6_additional_images/manifest.json`
- `/tools/patchdata/ys6_additional_images/source_images/`
- `/tools/patchdata/work/current/image-discovery/`

## 다음 단계

선정된 PNG를 항목 또는 문구 단위로 분리하고 `edited_images` 편집 작업 공간을
만든다. 이후 원본 블록 보존형 DXT1/DXT3 재삽입과 GUI 패치 빌드 연동을 별도
계획으로 진행한다.
