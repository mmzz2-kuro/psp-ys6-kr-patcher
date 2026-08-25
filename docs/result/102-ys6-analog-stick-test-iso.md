# 102. Ys VI 아날로그 스틱 테스트 ISO 생성 결과

상태: 완료

## 수행 내용

- 현재 한글 패치 전체와 이미지, 엔딩 영상, XMB 이미지를 포함한 테스트 ISO를 생성했다.
- 한글 폰트와 시스템 메시지가 반영된 최종 EBOOT에 8개 아날로그 모드 명령을 적용했다.
- `ys6_patch_builder.py`에 기본값이 비활성인 `--analog-stick` 테스트 옵션을 추가했다.
- SPECIAL VERSION의 반경형 데드존 보정은 이번 ISO에 포함하지 않았다.

## 생성·변경 파일

- `patched/102-analog-stick-test/Ys VI (Japan) - 102-analog-stick-test.iso`
- `tools/scripts/ys6_analog_mode_patch.py`
- `tools/scripts/ys6_integrated_build.py`
- `tools/scripts/ys6_patch_builder.py`
- `tools/patchdata/work/current/102-analog-stick-test/EBOOT.BIN`
- `tools/patchdata/work/current/102-analog-stick-test/analog-stick-report.json`
- `tools/patchdata/work/current/102-analog-stick-test/preflight-report.json`
- `tools/patchdata/work/current/102-analog-stick-test/build-manifest.json`

## 검증 결과

- Python 문법 검사: 통과
- `--analog-stick` 입력 검사: 활성 확인
- 사전 검증: 통과, 할당 공간 초과 0건
- ISO 크기: 866,254,848 bytes
- ISO SHA-256: `E7CB03A294836D98C20842DCD4F3FB2745A5CDAC37C756FAD78703AA8E7E655D`
- ISO에서 재추출한 EBOOT SHA-256: `9ABBCC83C717259FA6F1791E270A23618E8B34C2254AAB2C301D94FFAA81C0A5`
- 작업 EBOOT와 ISO 내 EBOOT 바이트 일치: 통과
- 8개 대상 명령: 모두 `0x24040001` 확인
- EBOOT 전체 크기: 1,935,840 bytes로 유지

## 알려진 제약

- 실제 PSP 또는 PPSSPP에서의 이동 감도와 대각선 입력은 실기 테스트가 필요하다.
- 데드존 보정이 없으므로 스틱 중립 편차가 큰 기기에서는 캐릭터가 미세하게 이동할 수 있다.

## 정리 대상

- 원본 ISO는 변경하지 않았다.
- 새로 생성한 임시 ROM은 없으며, 삭제 대상은 없다.
