# 076. Ys VI 보스명 이미지 조사 및 패치 작업공간 계획

상태: 사용자 확인 대기

## 목적

- `boss00.dds.z`, `boss01.dds.z`에 포함된 보스명과 이명을 정확히 분할한다.
- 독립 파일 외에 게임이 실제로 읽는 런타임 아카이브 사본이 있는지 조사한다.
- `place_names_00~02`와 같은 방식으로 원본 조각·수정 조각 및 GUI 추가 이미지 패치
  경로에 등록한다.
- 한국어 이미지 제작 전 보스명과 이명의 확정 번역표를 사용자에게 제시한다.

## 현재 확인 사항

| 리소스 | ISO 경로 | 크기 | 형식 | ISO 할당 공간 |
|---|---|---:|---|---:|
| `boss00` | `PSP_GAME/USRDIR/data/image/boss00.dds.z` | 256×256 | DXT3 | 8,192바이트 |
| `boss01` | `PSP_GAME/USRDIR/data/image/boss01.dds.z` | 256×256 | DXT3 | 8,192바이트 |

- 두 이미지에는 총 8개의 보스명과 각 보스의 이명이 배치돼 있다.
- 확인된 이름:
  - `デミガルヴァ`
  - `ゾンプラス`
  - `ウド＝メイユ`
  - `オージュガン`
  - `ラーナルーナ`
  - `ガルヴァロア`
  - `エルンスト`
  - `ナピシュテム`
- 현재 대사 정본에서 확인되는 표기:
  - `존프라스`, `오쥬간`, `라나루나`, `갈바로아`, `에른스트`, `나피쉬팀`
- `デミガルヴァ`, `ウド＝メイユ`는 기존 정본의 직접 대응 표기가 없어 별도 확정이
  필요하다.

## 1단계: 이미지 구조 조사

1. 원본 ISO에서 두 컨테이너를 다시 추출하고 payload·MIG 정보를 검증한다.
2. 알파 채널을 보존한 원본 PNG와 어두운 배경 확인용 PNG를 생성한다.
3. 보스명과 이명의 실제 픽셀 경계를 조사한다.
4. 텍스처 상단·하단을 가로질러 이어지는 항목이 있는지 확인한다.
5. 4×4 블록 오프셋 또는 행 회전이 필요한지 무수정 왕복 검증으로 판정한다.
6. 각 편집 조각은 보스명과 해당 이명을 함께 편집할 수 있도록 충분한 투명 여백을
   포함한다.

## 2단계: 런타임 사본 조사

1. 원본 ISO의 모든 `data/arc/*.bin` 엔트리를 검색한다.
2. 파일명, 컨테이너 SHA-256 및 압축 해제 payload SHA-256으로 `boss00.dds.z`,
   `boss01.dds.z`의 동일 사본을 찾는다.
3. 발견한 각 사본의 아카이브 경로, 엔트리 index, flags, 할당 공간을 기록한다.
4. 독립 파일만 존재하는지 또는 런타임 사본 동기화가 필요한지 판정한다.

## 3단계: 번역표 확인

1. 보스명 8개와 이명 8개의 일본어 원문을 목록으로 정리한다.
2. 기존 대사·시스템·몬스터명 정본과 대조해 프로젝트 표기를 우선한다.
3. 직접 대응 표기가 없는 이름과 이명은 번역 후보를 제시한다.
4. 사용자가 전체 표기를 확인하기 전에는 한글 이미지를 제작하지 않는다.

## 4단계: 추가 이미지 작업공간 등록

사용자 번역표 확인 후 다음을 수행한다.

1. `tools/patchdata/ys6_additional_images/manifest.json`에 `boss_names_00`,
   `boss_names_01` 리소스를 추가한다.
2. 원본 이미지를 `source_images`에 두고 분할 조각을 다음 경로에 생성한다.
   - `source_parts/boss_names_00/`
   - `source_parts/boss_names_01/`
3. 사용자 편집 경로를 생성한다.
   - `edited_parts/boss_names_00/`
   - `edited_parts/boss_names_01/`
4. 런타임 사본이 확인되면 매니페스트의 `runtime_copies`에 정확한 메타데이터를
   등록한다.
5. GUI의 기존 `추가 이미지 적용` 체크박스가 두 리소스의 사전 검증과 ISO 적용을
   함께 제어하는지 확인한다.

## 검증

1. 원본 조각을 무수정 재조립했을 때 payload가 원본과 동일한지 확인
2. 각 조각의 크기·모드·알파 및 경계 확인
3. 단일 조각 변경 시 예상 영역의 DXT3 블록만 변경되는지 확인
4. 독립 파일과 모든 확인된 런타임 사본의 컨테이너·payload 일치 검증
5. GUI 추가 이미지 활성화/비활성화에 따른 사전 검증 및 패치 포함 여부 확인
6. 할당 공간 초과 여부 확인

## 변경 및 생성 대상

- `tools/patchdata/ys6_additional_images/manifest.json`
- `tools/patchdata/ys6_additional_images/source_images/boss00.png`
- `tools/patchdata/ys6_additional_images/source_images/boss01.png`
- `tools/patchdata/ys6_additional_images/source_parts/boss_names_00/`
- `tools/patchdata/ys6_additional_images/source_parts/boss_names_01/`
- 필요 시 런타임 사본 조사 보고서
- 사용자 번역표 승인 후 `edited_parts/boss_names_00~01/`
- `docs/result/076-ys6-boss-name-image-discovery-and-patch-workspace.md`

## 보존 사항

- 사용자 번역표 확인 전에는 한글 이미지와 ISO를 생성하지 않는다.
- 원본 ISO와 기존 패치 ISO는 수정하지 않는다.
- 기존 추가 이미지 좌표·블록 오프셋·런타임 사본 정의는 변경하지 않는다.
- 조사 과정의 테스트 산출물은 `tools/patchdata/work/current` 아래에 둔다.

## 완료 기준

- 보스명과 이명 8세트의 원문 및 정확한 이미지 경계가 확인된다.
- 독립 파일과 런타임 사본 구성이 확정된다.
- 사용자 확인 가능한 번역표가 작성된다.
- 승인 후 두 리소스가 추가 이미지 작업공간과 GUI 빌드 경로에 등록된다.
- 결과 문서에 변경 파일, 검증 결과와 정리 대상 임시 ROM을 기록한다.

## 완료 기록

- 사용자 번역안 확인 후 4단계 작업공간 등록과 한글 이미지 생성을 완료했다.
- GUI 공통 빌더 사전검증 및 런타임 복제본 8개 교체 검증을 통과했다.
- 상세 결과는 `docs/result/076-ys6-boss-name-image-discovery-and-patch-workspace.md`에 기록했다.
