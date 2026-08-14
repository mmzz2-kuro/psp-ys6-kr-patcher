# 044. 전체 4,628개 대사 테스트 ISO 빌드 결과

## 결과

전체 draft 4,628개를 임시 작업공간에서 override로 승격하여 완전판 대사 테스트 ISO를 생성했다. 공유 payload 충돌과 many-to-many 대상까지 모두 포함되었다.

## 생성 ISO

- 경로: `/patched/044-full-dialogue-test/Ys VI - full-4628-dialogues-korean-test.iso`
- 크기: 866,254,848바이트
- SHA-256: `5D3CA4BCD5ED4519D0CB6FB4FE71BB8AD2CB73C35BE942311CC95C11C840B80F`
- 원본 ISO SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`

## 반영 범위

- 대사 override: 4,628개
- XSO payload: 460개
- 아카이브: 49개
- 독립 XSO: 448개
- 인물명: 14개
- 한글 및 추가 글리프: 945개
- 공간 초과: 0개

## many-to-many 검증

- 런타임 아카이브 대상: 5개
- many-to-many 독립 XSO 대상: 5개
- `ridepedestal`: 아카이브 3개, 독립 XSO 3개
- `talkgasshu`: 아카이브 2개, 독립 XSO 2개
- 각 대상의 원본 payload 해시와 할당 공간 검증 통과

standalone 보고서에는 위 5개 외에도 기존 별도 설정으로 처리되는 `talkgasshu` 독립 경로 3개가 존재한다. 이 3개는 many-to-many 그룹이 아니라 기존 standalone 대상이다.

## 검증 결과

- 임시 작업공간 override: 4,628개
- 임시 작업공간 검증 오류: 0개
- build manifest: `valid: true`
- XSO 및 아카이브 공간 초과: 없음
- 출력 ISO 존재, 크기 및 SHA-256 확인
- 출력 ISO와 원본 ISO의 SHA-256이 다름
- 원본 ISO SHA-256 유지
- 원본 작업공간 SHA-256 유지: `2C318B22401DFD56015BE1AE175AB0865CCA102F19FD7DEC40E71DB3A7D405F2`
- 원본 작업공간 상태: draft 4,628개, conflict 0개, override 0개

## 빌드 보고서

- `/.work/ys6-full-dialogue-test/build/build-manifest.json`
- `/.work/ys6-full-dialogue-test/build/preflight-report.json`
- `/.work/ys6-full-dialogue-test/build/translation-report.csv`
- `/.work/ys6-full-dialogue-test/build/xso-report.csv`
- `/.work/ys6-full-dialogue-test/build/archive-report.csv`
- `/.work/ys6-full-dialogue-test/build/standalone-report.csv`
- `/.work/ys6-full-dialogue-test/build/castinfo-report.csv`
- `/.work/ys6-full-dialogue-test/build/glyph-report.json`

## 알려진 제한

- 번역 데이터와 구조 검증은 완료했지만 전체 게임 플레이 검증은 아직 수행하지 않았다.
- 화면 폭, 문맥, 표현 및 이벤트 진행 문제는 실제 플레이 중 추가로 발견될 수 있다.
- 이 ISO는 최종 배포판이 아니라 전체 대사 검증용 테스트판이다.

## 정리 대상

- 044 테스트가 안정적이면 `/patched/042-safe-subset-test/Ys VI - 4462-dialogues-korean-test.iso`는 삭제 후보다.
- 최종 배포판 생성 후 044 테스트 ISO와 `/.work/ys6-full-dialogue-test`도 정리할 수 있다.

## ROM 처리

- 원본 ISO는 변경하지 않았다.
- 기존 패치 ISO는 덮어쓰지 않았다.
- 새 테스트 ISO 한 개만 생성했다.
