# 074. Ys VI 월드맵 글자 영역 한정 현지화 수정 결과

## 수행 내용

- 072의 전체 화면 생성 이미지를 폐기하고 원본 월드맵을 기준으로 다시 제작했다.
- `imagegen` 글자 제거 결과는 영역과 배경 복원 참고에만 사용했으며, 생성된 전체
  지도는 최종 파일에 사용하지 않았다.
- 일본어 지명 13개의 사각 영역만 OpenCV 국소 복원한 뒤 굴림 7px 글꼴과 1px 어두운
  외곽선으로 확정 한글을 합성했다.
- 영역 밖 픽셀과 원본 알파 채널을 그대로 유지했다.
- 재현 가능한 비GUI 스크립트를 `tools/scripts`에 추가했다.
- 새 이미지로 사전 검증과 074 격리 ISO 빌드를 실행했다.
- 출력 ISO 내부 월드맵을 다시 추출·렌더링했다.

## 변경 및 생성 파일

- `tools/scripts/ys6_world_map_localize.py`
- `tools/patchdata/ys6_additional_images/edited_parts/world_map/line_01.png`
- `patched/074-world-map-text-only-localization-fix/Ys VI (Japan) - 074-world-map-text-only-test.iso`
- `patched/074-world-map-text-only-localization-fix/world-map-rendered-from-iso.png`
- `tools/patchdata/work/current/074-world-map-localize-report.json`

## 이미지 검증

- 크기: `320x240`
- 한글 지명: 13개
- 원본 대비 변경 픽셀: 8,282개
- 이미지 단계 변경 4x4 블록: 675개
- 글자 상자 밖 변경 픽셀: 0개
- 원본 알파 채널 보존: 예
- ISO 재렌더링 알파 범위: `255..255`

## 패치 검증

- 사전 검증: 통과
- ISO 빌드: 통과
- 월드맵 적용 region: `line_01`
- 실제 DXT1 변경 블록: 671개
- 072 대비: 전체 4,800개 변경 문제 해소
- 월드맵 컨테이너 크기: 35,440바이트
- ISO 할당 공간: 36,864바이트
- 남은 공간: 1,424바이트
- overflow: 없음
- ISO 내부 컨테이너와 빌드 산출물: 바이트 단위 일치
- ISO 내부 컨테이너 검증: 정상

## 해시

- 074 출력 ISO SHA-256:
  `397503961E1EA676FA7A3BEBFF96DD858B61C042A0540A5EF3C7878A37E54E2F`
- ISO 내부 `map.dds.z` SHA-256:
  `E5A258824F8694D119B12A08E359541F928A2E3694E293E22FC2C41D7782F7FD`
- 월드맵 payload SHA-256:
  `9378020009050DD18F62A267DF84A805B1F591C371D81D6E5623888774941AB0`

## 보존 및 알려진 사항

- 원본 월드맵, 매니페스트 좌표 및 `block_offset=1`은 변경하지 않았다.
- 기존 073 ISO와 사용자의 기존 패치 ISO는 변경하지 않았다.
- 사용자가 작업 중인 시스템 메시지 및 기타 번역 데이터는 변경하지 않았다.
- ISO 내부 재렌더링에서는 월드맵이 정상 표시되지만 실제 PSP/에뮬레이터 화면 표시
  여부는 사용자의 콜드 부팅 테스트가 필요하다.
- 073 테스트 ISO는 이전 방식의 임시 ROM이며 삭제 가능하다. 074 테스트 ISO는 이번
  방식의 확인용 ROM이다.
