# 096. Ys VI 한글 엔딩 PMF 재구성·ISO 통합 결과

상태: 완료

## 수행 내용

- 095번에서 확정한 한글 화자명·대사·마스크 위치를 두 엔딩 영상에 반영했다.
- 원본 PMF의 `0x800` PSMF 헤더, MPEG-PS/PES 구조, PTS, private stream을 보존하고 H.264 영상 payload만 교체했다.
- 교체 구간의 각 H.264 AU를 원본 AU와 같은 길이로 패딩하여 PMF 크기와 ISO extent를 변경하지 않았다.
- 빌드 도구와 GUI에 `엔딩 영상 적용` 선택을 추가했다. 선택 상태는 사전 검증과 ISO 빌드에 동일하게 적용된다.
- 원본 ISO는 변경하지 않고 096 테스트 ISO를 `/patched` 아래에 생성했다.

## 생성·변경 파일

- `tools/scripts/ys6_pmf_rebuild.py`: PMF 구조 검사와 고정 길이 H.264 AU 교체 도구
- `tools/patchdata/ys6_ending_movies/im03a_kaizoku.pmf`
- `tools/patchdata/ys6_ending_movies/im03b_kazaminooka.pmf`
- `tools/patchdata/ys6_ending_movies/manifest.json`
- `tools/scripts/ys6_integrated_build.py`: 원본·자산 해시, PMF 구조, 프레임 수, ISO 할당 크기 검증과 교체 추가
- `tools/scripts/ys6_patch_builder.py`: 엔딩 영상 자산 검증·선택적 빌드 연결, `--no-ending-movies` 추가
- `tools/ys6_dialogue_viewer.py`: 기본 선택된 `엔딩 영상 적용` 체크박스 추가
- `patched/096-korean-ending-movie/Ys VI (Japan) - 096-korean-ending-movie-test.iso`

## 검증 결과

- Python 문법 검사: 관련 스크립트와 GUI 모두 통과
- PMF 전체 FFmpeg 디코딩: 두 파일 모두 오류 없이 통과
- `im03a_kaizoku.pmf`: 11,786,240 bytes, 2,458 frames, SHA-256 `2178AF0D62819423E37B94BDE07380D005BDE77A206B9FD0DED443C425688D58`
- `im03b_kazaminooka.pmf`: 10,774,528 bytes, 2,278 frames, SHA-256 `A84E7D2CA8E779457C9D047FA9B43173229F3040490CB1A5C42F491A95166E56`
- 포함 사전 검증: `ending_movies_enabled=true`, `ending_movie_count=2`, overflow 없음
- 제외 사전 검증: `ending_movies_enabled=false`, `ending_movie_count=0`, valid
- 테스트 ISO: 866,254,848 bytes, SHA-256 `986C0E2FF4DBC8EAF8EE41F87D8EC0DFD189E9AB8C7FC69D274B15E3E7331011`
- 테스트 ISO에서 두 PMF를 다시 읽어 자산 파일과 크기·SHA-256가 일치함을 확인했다.
- ISO 빌드 차이 검증에서 허용 범위 밖 변경은 없었다.

## 알려진 사항

- 정적 구조 검증과 PC FFmpeg 디코딩은 완료했지만, PSP/PPSSPP 게임 내 실제 재생은 사용자 테스트가 필요하다.
- 096 작업에서 생성한 테스트 ISO는 위 경로의 1개이며, 게임 내 확인 후 불필요하면 삭제할 수 있다.
