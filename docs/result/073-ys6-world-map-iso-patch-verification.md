# 073. Ys VI 월드맵 이미지 ISO 패치 및 검증 결과

## 수행 내용

- 정식 원본 ISO를 입력으로 전체 사전 검증을 실행했다.
- 073 격리 폴더에 전체 한글 패치 ISO를 새로 생성했다.
- 출력 ISO에서 `PSP_GAME/USRDIR/data/menu/map.dds.z`를 다시 읽어 빌드 산출물과
  비교했다.
- ISO 내부 월드맵을 압축 해제하고 `block_offset=1`을 적용해 `320x240` PNG로 다시
  렌더링했다.

## 생성 파일

- `patched/073-world-map-iso-patch-verification/Ys VI (Japan) - 073-world-map-korean-test.iso`
- `patched/073-world-map-iso-patch-verification/world-map-rendered-from-iso.png`

## 검증 결과

- 사전 검증: 통과
- ISO 빌드: 통과
- 전체 override: 5,251개
- 추가 이미지: 43개 / 리소스 11개
- 월드맵 적용 region: `line_01`
- 월드맵 변경 블록: 4,800개
- ISO 내부 `map.dds.z` 컨테이너 검증: 정상
- ISO 내부 컨테이너와 빌드 산출물: 바이트 단위 일치
- ISO에서 재렌더링한 월드맵: 072 한글 이미지 확인
- overflow: 없음

## 해시

- 출력 ISO SHA-256:
  `198D6609E1FB630A21DFCAA8CC1C22296E5ED759AB8173FE86D0D5554730E983`
- ISO 내부 및 빌드 산출 `map.dds.z` SHA-256:
  `BF13BE1E425D359F2BE228AFC398FF4C897D374EED381D1F30895F41F2313435`
- 월드맵 압축 해제 payload SHA-256:
  `4D43BA49017199817FB40773C8338BF2CFC67744F6C7542C3E2FD1293C314005`

## 중요 확인 사항

- 새로 만든 073 ISO의 SHA-256은 기존
  `roms/Ys VI - Korean Patched.iso`와 동일하다.
- 기존 패치 ISO 내부 월드맵 컨테이너도 새 빌드와 동일하다.
- 따라서 기존 ISO에도 072 월드맵 이미지가 이미 들어가 있었으며, ISO 빌드 누락은
  아니다.
- ISO에서 직접 다시 렌더링한 결과는 한글이므로 게임에서 계속 일본어가 보인다면
  다른 ISO 실행, 에뮬레이터의 기존 실행 상태 또는 별도 런타임 로딩 경로를 추가로
  확인해야 한다.

## 보존 및 정리 대상

- 원본 ISO와 기존 패치 ISO는 변경하지 않았다.
- 매니페스트 좌표와 블록 오프셋은 변경하지 않았다.
- 073 테스트 ISO는 검증용으로 유지했으며 확인 완료 후 삭제 가능한 임시 ROM이다.
