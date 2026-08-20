# 059. Ys VI placename02 런타임 아카이브 사본 동기화 결과

## 결과

- 독립 `placename02.dds.z`에 적용하던 사용자 편집 이미지 2개를 14개 맵
  아카이브 내부 런타임 사본에도 자동으로 동기화하도록 통합 빌더를 수정했다.
- 059 테스트 ISO에서 독립 파일 1개와 런타임 사본 14개가 모두 같은 수정
  컨테이너, payload 및 렌더 결과를 갖는 것을 확인했다.

## 변경 내용

- `tools/patchdata/ys6_additional_images/manifest.json`
  - `place_names_02`에 14개 맵 아카이브 경로, 엔트리 index, 이름, flags를 기록했다.
- `tools/scripts/ys6_integrated_build.py`
  - 원본 런타임 사본이 독립 원본 컨테이너와 같은지 확인한다.
  - 경로·index·이름·flags가 모두 일치하는 엔트리만 선택한다.
  - 독립 파일에 사용한 수정 컨테이너를 아카이브 작업 캐시에 누적 적용한다.
  - 누락, 중복, 원본 불일치 및 할당 초과 시 빌드를 중단한다.
  - 사본별 교체 결과와 아카이브별 추가 이미지 변경 수를 보고서에 기록한다.
- `tools/scripts/tests/test_ys6_integrated_build.py`
  - 런타임 사본 동기화와 원본 불일치 차단 검사를 추가했다.
- 058 계획·결과 문서
  - 게임에서 일본어가 표시된 직접 원인이 런타임 사본 누락이었음을 정정했다.

## 검증

- 관련 단위 및 통합 빌더 테스트 9개 통과.
- 통합 사전검사 통과:
  - 편집 이미지: 2개
  - 추가 이미지 리소스: 1개
  - 변경 DXT3 블록: 547개
  - 런타임 사본 대상: 14개
  - 런타임 사본 교체 성공: 14개
  - 할당 공간 초과: 0개
- 각 런타임 엔트리:
  - 할당 공간: 8,192바이트
  - 수정 컨테이너: 6,200바이트
  - 남은 공간: 1,992바이트
- 생성 ISO 재추출 검사:
  - 독립 파일과 컨테이너가 같은 사본: 14/14
  - 독립 파일과 payload가 같은 사본: 14/14
  - 독립 파일과 렌더 결과가 같은 사본: 14/14
- 원본 ISO SHA-256은 빌드 후에도
  `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`로 유지됐다.

## 생성 파일

- 테스트 ISO:
  `patched/059-placename02-runtime-copy-sync/Ys VI (Japan) - 059-placename02-runtime-copy-sync-test.iso`
- 테스트 ISO SHA-256:
  `74A70C4D19116F837C53D757F8328EBF1AE43124DB25B699ED5A05E5383BB1A7`
- 검증 보고서:
  `tools/patchdata/work/current/additional-images/059-runtime-copy-verification.json`
- ISO 재추출 이미지:
  `tools/patchdata/work/current/additional-images/059-place_names_02-from-generated-iso.png`

## 알려진 문제 및 정리 대상

- 에뮬레이터 또는 실기에서 실제 지역 진입 시의 표시는 아직 확인하지 않았다.
- 059 테스트 ISO는 런타임 확인이 끝난 뒤 불필요하면 삭제할 수 있다.
- 058 테스트 ISO는 런타임 사본이 교체되지 않은 실패 작업본이므로 정리 대상이다.
- 원본 ISO와 원본 이미지 작업 공간은 수정하지 않았다.
