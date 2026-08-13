# Ys VI 검수 인물명 14개 일괄 적용 결과

## 상태

- 작업 번호: 029
- 구현 및 ISO 적용: 완료
- 정적 검증: 완료
- 인게임 검증: 완료
- 작업일: 2026-08-13

## 결과 요약

`/tools/config/cast-names.json`에서 `reviewed`로 지정된 인물명 14개를 기존 대사 115개와 함께 누적 빌드했다. 번역만 입력되고 상태가 `untranslated`인 항목은 적용하지 않았다.

두 `castinfo.dat` 사본을 자동으로 동일하게 수정했으며, 인물명에 필요한 신규 한글 글리프 6개를 추가했다.

## 적용 인물명

- 오르하 (`CAST_C220`)
- 이샤 (`CAST_C240`)
- 오드족장 (`CAST_C250`)
- 로로 (`CAST_C620`)
- 토쿠사 (`CAST_C630`)
- 마브 (`CAST_C650`)
- 소라 (`CAST_C670`)
- 라고 (`CAST_C690`)
- 실바 (`CAST_C700`)
- 카말라 (`CAST_C730`)
- 고양이 (`CAST_C740`)
- 미하일 (`CAST_C750`)
- 구엔 (`CAST_C760`)
- 니스 (`CAST_C770`)

## 최종 ISO

- 경로: `/patched/029-reviewed-cast-name-batch/Ys VI - reviewed-cast-names-korean-build.iso`
- SHA-256: `65E543AA91E03D2FF31BA55EAF875D1305B69516CC32B8A2B77C7FF3DED31F9D`
- 크기: 866,254,848바이트

원본 ISO:

- SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 원본은 변경되지 않았다.

## 정적 검증

- 대사 reviewed: 115개
- 적용 인물명: 14개
- XSO 그룹: 31개
- 대사 아카이브: 4개
- standalone XSO: 38개
- 글리프: 198개, 기존 192개에서 6개 증가
- 할당 초과: 0건
- ISO 교체 파일: 45개
- 허용 ISO 범위 밖 변경: 0건
- 자동 테스트: 88개 통과
- standalone과 `init.bin` 내부 `castinfo.dat`: 바이트 동일
- 최종 `castinfo.dat` SHA-256: `51D865AD03F54D539E382F4E74811627875C7850BE7BADD5B7A9F2A72DBF59CC`

레코드별 원문, 번역, 인코딩 HEX와 변경 SHA는 다음 보고서에 기록했다.

- `/.work/ys6-reviewed-cast-name-batch/build/castinfo-report.csv`
- `/.work/ys6-reviewed-cast-name-batch/build/build-manifest.json`
- `/.work/ys6-reviewed-cast-name-batch/build/preflight-report.json`

## 인게임 검증 결과

사용자가 PPSSPP에서 `reviewed`로 적용한 인물명 전체가 정상 출력되는 것을 확인했다.

- reviewed 인물명 14개 정상 출력
- 한글 깨짐이나 이름 필드 잘림 없음
- 기존 대사 출력 정상

이에 `/tools/config/cast-names.json`의 `reviewed` 상태부터 통합 빌드까지의 인물명 일괄 적용 경로를 검증 완료로 확정한다.
