# 075. Ys VI 월드맵 한글 가독성 및 일본어 잔존 수정 결과

## 최종 적용본

- 사용자가 직접 수정한 다음 파일을 최종 정본으로 사용했다.
  - `tools/patchdata/ys6_additional_images/edited_parts/world_map/line_01.png`
- 사용자의 최종 PNG는 수정하거나 재생성하지 않고 그대로 ISO 패치 입력에 사용했다.
- 앞선 자동 생성·블러 처리 미리보기는 최종 ISO에 사용하지 않았다.

## 이미지 사전 확인

- 형식: RGBA PNG
- 크기: `320x240`
- 알파 범위: `255..255`
- 원본 대비 변경 픽셀: 6,703개
- 이미지 단계 변경 4x4 블록: 528개
- 변경 경계: `(84, 50) .. (288, 220)`

## 수행 내용

- 정식 원본 ISO를 입력으로 전체 사전 검증을 실행했다.
- 사용자 수정본의 월드맵 DXT1 컨테이너를 재구성했다.
- 기존 ISO를 덮어쓰지 않고 075 전용 ISO를 생성했다.
- 출력 ISO에서 `PSP_GAME/USRDIR/data/menu/map.dds.z`를 다시 읽어 빌드 산출물과
  비교했다.
- ISO 내부 payload를 `block_offset=1`로 다시 렌더링해 검증 PNG를 만들었다.

## 생성 파일

- `patched/075-world-map-readable-korean-label-redo/Ys VI (Japan) - 075-world-map-user-edited-test.iso`
- `patched/075-world-map-readable-korean-label-redo/world-map-rendered-from-iso.png`

## 검증 결과

- 사전 검증: 통과
- ISO 빌드: 통과
- 월드맵 적용 region: `line_01`
- 실제 DXT1 변경 블록: 527개
- 월드맵 컨테이너 크기: 35,510바이트
- ISO 할당 공간: 36,864바이트
- 남은 공간: 1,354바이트
- overflow: 없음
- ISO 내부 컨테이너와 빌드 산출물: 바이트 단위 일치
- 컨테이너 압축 해제 검증: 정상
- ISO 재렌더링 크기: `320x240`
- ISO 재렌더링 알파 범위: `255..255`
- ISO 재렌더링에서 사용자 수정 한글 월드맵 확인

## 해시

- 075 출력 ISO SHA-256:
  `1229F1465E2B1ED085FDDF1E1BDC8125830D667BDBA39E88FB54C30C619E23BB`
- ISO 내부 `map.dds.z` SHA-256:
  `F8D283282BEECE31DE2B61B4BB832A92992BB6935E0D0A99ABDA2F9B19D26561`
- 월드맵 payload SHA-256:
  `4614B0EF2D407C7263C4E5E93D4EC47E1DE57D6D7873F34F31C7C000F6C1F08A`

## 보존 및 정리 대상

- 사용자가 수정 중인 시스템 메시지와 기타 번역 데이터는 직접 변경하지 않았다.
- 원본 ISO와 기존 073·074 ISO는 변경하지 않았다.
- 073·074 테스트 ISO는 이전 방식의 임시 ROM으로 삭제 가능하다.
- 075 ISO는 사용자 최종 이미지 적용 확인용 ROM이다.
- `tools/scripts/ys6_world_map_localize.py`는 자동 시안 생성용이며 사용자가 수정한 최종
  `line_01.png`을 재현하지 않는다. 최종 이미지를 유지하려면 이 스크립트로 해당 파일을
  다시 생성하지 않아야 한다.
