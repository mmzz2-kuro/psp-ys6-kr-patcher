# Ys VI 대사 override·draft 인게임 역테스트 결과

## 상태

- 작업 번호: 031
- ISO 생성: 완료
- 정적 역테스트: 완료
- 인게임 검증: 사용자 확인 대기
- 작업일: 2026-08-13

## 결과 요약

`s_020a/adolsleep.xso.z`에서 인덱스 29~32는 `override`, 33은 번역문이 존재하는 `draft` 상태로 빌드했다.

재구축 XSO를 직접 파싱한 결과:

- 29: 한글 raw bytes로 변경
- 30: 한글 raw bytes로 변경
- 31: 한글 raw bytes로 변경
- 32: 한글 raw bytes로 변경
- 33: 원본 CP932 raw bytes와 완전히 동일

번역 적용 보고서에도 인덱스 32까지만 포함되고 33은 존재하지 않는다. 따라서 draft 번역이 패치에 포함되지 않는 정적 역테스트가 통과했다.

## 검증 ISO

- 경로: `/patched/031-dialogue-override-draft-runtime-test/Ys VI - dialogue-override-draft-test.iso`
- SHA-256: `754DE4463A7902588C2F028E63B0383BBC1503DFB65B719E25316D835893CE08`
- 크기: 866,254,848바이트

## 빌드 결과

- 대사 override: 142개
- 제외된 draft: 19개
- 인물명 reviewed: 14개
- XSO 그룹: 31개
- 대사 아카이브: 4개
- standalone XSO: 38개
- 글리프: 257개
- 할당 초과: 0건
- ISO 교체 파일: 45개
- 허용 범위 밖 변경: 0건
- 자동 테스트: 92개 통과

원본 ISO SHA-256은 다음과 같이 유지됐다.

- `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`

## 인게임 기대 결과

`adolsleep` 이벤트 후반에서:

1. 29~32번은 한글 출력
2. 33번은 일본어 원문 출력
   - `……とにかく今は`
   - `ゆっくりお休みになってください。`
3. 대사창과 이벤트 진행 정상

사용자 확인 후 override·draft 분리 흐름을 최종 확정한다.
