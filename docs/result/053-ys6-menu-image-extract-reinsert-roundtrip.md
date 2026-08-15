# 053. Ys VI 메뉴 이미지 리소스 추출·재삽입 왕복 검증 결과

## 상태

- 완료
- 사용자 PPSSPP 화면 검증 완료
- 최종 확인 ISO: `optionselect-marker-v11-dxt1-correct.iso`

## 결론

시스템 설정 화면의 일본어 메뉴 이미지를 포함하는 실제 런타임 리소스와 안전한 재삽입 경로를 확인했다.

- 실제 ISO 파일: `PSP_GAME/USRDIR/data/arc/init.bin`
- 아카이브 엔트리: index 29, `static_tex.dds.z`
- 아카이브 내부 엔트리 오프셋: `0x89000`
- 엔트리 할당 크기: 665,600바이트
- 해제 payload 안 런타임 아틀라스 시작: `0x106130`
- 런타임 아틀라스 포맷: PSP DXT1
- 크기: 256×256
- 압축 데이터 크기: 32,768바이트
- DXT1 블록 크기: 8바이트
- 블록 행 폭: 64

논리 4×4 블록 `(x, y)`의 payload 위치는 다음과 같다.

`0x106130 + (y * 64 + x) * 8`

독립 파일 `data/menu/optionselect.dds.z`, `data/image/_static_tex.dds.z`, `data/image/static_tex.dds.z`에도 관련 데이터가 있지만 게임은 설정 화면에서 `init.bin` 내부 사본을 사용한다.

## 최종 화면 검증

`효과음のボリューム` 행의 논리 픽셀 좌표 `x=40..55`, `y=28..43`을 16×16 마젠타 사각형으로 교체했다.

- 변경 DXT1 블록: 16개
- 변경 payload 바이트: 128바이트
- 대상 밖 변경: 0바이트
- 재압축 컨테이너 크기: 665,036바이트
- 할당 잔여: 564바이트
- 사용자 확인: 효과음 행에 16×16 정사각형으로 정상 출력
- 메뉴 화면 및 나머지 UI: 정상 출력

최종 테스트 ISO:

- 경로: `/patched/053-menu-image-roundtrip/Ys VI (Japan) - optionselect-marker-v11-dxt1-correct.iso`
- SHA-256: `CD9E7FC510B95334ECB246DE593A9FADFB908F92AAA7FF2CE13A79D64E6EA0D0`

## 조사 과정에서 폐기한 가설

### 독립 `optionselect.dds.z`

이미지 내용은 화면과 대응하지만 개별 파일을 수정해도 런타임 출력은 바뀌지 않았다.

### `_static_tex.dds.z`

독립 optionselect DXT 데이터의 완전 사본이 있었지만 정확한 오프셋으로 수정한 v6에서도 런타임 메모리에는 원본 블록만 올라왔다. 비사용 사본으로 판정했다.

### 독립 `static_tex.dds.z`

PPSSPP 메모리에서 추출한 고유 데이터와 일치했지만 v7에서 수정 블록이 런타임에 올라오지 않았다. ISO 검색으로 `init.bin` 내부 원본 컨테이너를 추가 발견했다.

### DXT3 해석

16바이트를 DXT3 한 블록으로 해석한 v8·v9는 표식이 격자 또는 세로 줄무늬로 출력됐다. v10에서 각 16바이트에 고유 ID를 넣자 앞 8바이트는 색 블록, 뒤 8바이트는 투명 블록으로 나타났다. 이를 통해 실제 런타임 포맷이 8바이트 PSP DXT1임을 확정했다.

## 생성·변경 도구

- `/tools/scripts/ys6_menu_image_roundtrip.py`
  - option 계열 리소스 추출, 미리보기, 초기 표식 및 왕복 분석
- `/tools/scripts/ys6_menu_image_runtime_search.py`
  - 독립 파일 및 아카이브 후보 유사도 검색
- `/tools/scripts/ys6_texture_dump_inventory.py`
  - PPSSPP 텍스처 덤프 목록 및 접촉 시트 생성
- `/tools/scripts/ys6_iso_binary_needle_search.py`
  - ISO 파일과 `.z` 해제 payload의 바이너리 조각 검색
- `/tools/scripts/ys6_static_texture_embed_patch.py`
  - `_static_tex` 가설 검증용 선택 블록 패처
- `/tools/scripts/ys6_psp_texture_memory.py`
  - 런타임 메모리 텍스처 렌더링 진단
- `/tools/scripts/ys6_texture_block_mapping.py`
  - PPSSPP 덤프와 저장 블록 대응 분석
- `/tools/scripts/ys6_runtime_static_atlas_marker.py`
  - 검증된 PSP DXT1 런타임 아틀라스 표식 및 컨테이너 생성
- `/tools/scripts/ppsspp_memory_search.py`
  - 읽기 가능한 대형 메모리 영역 목록 기능 추가

## 주요 작업 자료

- 추출 및 레이아웃 자료: `/.work/ys6-menu-image-roundtrip/`
- 실제 런타임 원본: `/.work/ys6-menu-image-roundtrip/runtime-memory/runtime-atlas-source/`
- v10 블록 맵: `/.work/ys6-menu-image-roundtrip/marker-v10-block-map/`
- v11 DXT1 결과: `/.work/ys6-menu-image-roundtrip/marker-v11-dxt1-layout/`
- 계획 문서: `/docs/plan/053-ys6-menu-image-extract-reinsert-roundtrip.md`

## 알려진 제약

- 이번 단계는 이미지 추출·재삽입 경로 검증이며 최종 한글 메뉴 디자인은 아직 제작하지 않았다.
- 최종 패치 빌더에서는 독립 `data/image/static_tex.dds.z`와 `init.bin` 내부 사본을 같은 결과로 유지하는 편이 안전하다.
- 전체 `static_tex` payload를 재인코딩하지 않고 대상 DXT1 블록만 교체해야 다른 이미지의 손실을 막을 수 있다.

## 테스트 ISO 정리 대상

다음 진단 ISO는 최종 v11보다 이전 가설 또는 실패한 좌표 검증본이므로 결과 확인 후 삭제할 수 있다.

- `optionselect-marker-test.iso`
- `optionselect-marker-v1`~`v6` 계열
- `optionselect-marker-v7-runtime-static.iso`
- `optionselect-marker-v8-init-runtime.iso`
- `optionselect-marker-v9-correct-layout.iso`
- `optionselect-v10-block-map.iso`

파일 삭제는 별도 사용자 확인 후 수행한다. v11은 검증 증거로 당분간 보존한다.

## 다음 단계

검증된 DXT1 아틀라스를 PNG로 추출하고, 시스템 설정 메뉴의 일본어 문구를 한글 이미지로 편집한 뒤 선택된 블록만 다시 DXT1로 인코딩하는 작업을 별도 계획으로 진행한다. GUI 빌드 과정에서는 standalone과 `init.bin` 내부 사본을 함께 갱신한다.
