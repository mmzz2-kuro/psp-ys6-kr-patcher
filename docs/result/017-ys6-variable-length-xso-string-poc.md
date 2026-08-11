# Ys VI XSO 가변 길이 문자열 재조립 PoC 결과

## 상태

- 구현: 완료
- 정적 검증: 완료
- PPSSPP 인게임 검증: 성공

## 결론

XSR/XSO 문자열 하나의 바이트 길이를 변경하면서 문자열 풀과 뒤쪽 상대 오프셋을 재계산하는 방식을 구현했다. 22바이트 일본어 첫 대사를 26바이트 한글 시험문으로 늘린 결과, PPSSPP에서 시험문 전체와 다음 대사가 모두 정상 출력됐다.

이 결과로 문자열 인덱스와 명령 영역을 유지하는 조건에서는 XSO 문자열 길이가 원문과 같을 필요가 없으며, 수정 압축 파일이 아카이브의 기존 할당 공간에 들어가는 동안 가변 길이 번역문을 적용할 수 있음을 확인했다.

## 구현

`/tools/scripts/ys6_xso.py`를 다음과 같이 확장했다.

- 기존 기본 동작은 동일 길이 교체만 허용
- `--allow-length-change`를 명시한 경우에만 길이 증가·감소 허용
- 변경 후 모든 문자열 상대 오프셋 재계산
- 교체 바이트에 NUL이 포함되면 거부
- 원본·교체 문자열 길이와 증감량 출력
- 원본·교체 XSO 전체 크기 출력
- 기존 `--raw-hex`, 덮어쓰기 보호 및 재파싱 검증 유지

명령 예시:

```powershell
python tools\scripts\ys6_xso.py replace input.xso 35 HEX output.xso --raw-hex --allow-length-change --json
```

## XSO 변경

- 대상: `s_0551.xso.z` 내부 XSO
- 문자열 인덱스: 35
- 원문: `どうしたの、イーシャ？`
- 시험문: `한글출력테스트입니다입니다`
- 원문 길이: 22바이트
- 시험문 길이: 26바이트
- 길이 증가: 4바이트
- XSO 크기: 4,516 → 4,520바이트
- 문자열 개수: 66개로 동일

시험 바이트:

`98FC98FB98FA98F998F898F798F698F598F498F398F598F498F3`

검증 결과:

- XSO 헤더와 명령 영역 전체 동일
- 문자열 인덱스 0~34의 오프셋·원시 바이트 동일
- 문자열 인덱스 35만 22 → 26바이트로 변경
- 문자열 인덱스 36~65의 상대 오프셋이 모두 +4바이트
- 문자열 인덱스 36~65의 원시 바이트 동일
- 재조립 XSO 재파싱 성공
- 수정 XSO SHA-256: `EACA56324A451CCC2A794BEBE8B80140B55893705ACAE6F5D3947101EE91468C`

## 압축 및 아카이브

- 수정 `.xso.z` 크기: 1,959바이트
- 원본 `.xso.z` 크기: 1,946바이트
- 아카이브 할당 공간: 2,048바이트
- 수정 후 여유: 89바이트
- `.z` 비압축 크기: 4,520바이트
- `.z` payload CRC32: `8CF60FBC`
- 수정 `.xso.z` SHA-256: `B23D13A841855E2A9725EC13CA533695B56146E3FC27876B3CBC6B8467BA997F`
- 수정 `s_0551.bin` SHA-256: `55C211027EF6405A64EC92DFAEA27846A98FBA185087A8894BC0C66541CBC24A`

수정 압축 파일은 기존 할당 공간 안에 들어갔다. 아카이브 크기와 다른 파일의 오프셋은 변경하지 않았으며, 대상 엔트리의 크기 필드와 기존 할당 영역만 수정했다.

## 최종 ISO

- 경로: `/patched/017-variable-length-xso-poc/Ys VI - variable-length-dialogue-poc.iso`
- 크기: 866,254,848바이트
- SHA-256: `A47ECA37E393208F532370FE880840BEEC46424E0A218737974838CAB94CA3EF`

내부 파일:

| 파일 | SHA-256 |
|---|---|
| 수정 `EBOOT.BIN` | `DAB8C59FCC0913EF6A7D2FEB4A62DF0ABC5728B8F0BDDA7EA0581A695484970D` |
| 수정 `s_0551.bin` | `55C211027EF6405A64EC92DFAEA27846A98FBA185087A8894BC0C66541CBC24A` |

원본 ISO는 변경하지 않았다.

- 원본 SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 원본 대비 허용 범위 밖 변경: 0건

## 테스트

추가 검증:

- 기본 모드의 길이 변경 거부
- 명시적 길이 증가 성공 및 뒤쪽 오프셋 증가
- 명시적 길이 감소 성공 및 뒤쪽 오프셋 감소
- 대상 앞·뒤 문자열 원시 바이트 보존
- 명령 영역 보존
- NUL 포함 교체 거부
- 재조립 결과 재파싱

전체 결과:

- 단위 테스트 47개 통과
- `python -m compileall -q tools/scripts` 통과
- ISO 내부 파일 재추출 SHA-256 일치
- 원본 대비 허용 범위 밖 변경 0건
- 사용자 PPSSPP 새 게임에서 26바이트 시험문 전체 출력 확인
- 시험문 다음 대사 정상 출력 확인

## 생성·변경 파일

- 갱신: `/tools/scripts/ys6_xso.py`
- 갱신: `/tools/scripts/tests/test_ys6_xso.py`
- 갱신: `/docs/plan/017-ys6-variable-length-xso-string-poc.md`
- 추가: `/docs/result/017-ys6-variable-length-xso-string-poc.md`
- 생성: `/patched/017-variable-length-xso-poc/Ys VI - variable-length-dialogue-poc.iso`

분석 및 중간 자료는 `/.work/ys6-variable-length-xso-poc`에 두었다. 생성 과정의 중간 ISO는 최종 검증 후 삭제했다.

## 남은 범위와 제약

- 현재 `ys6_arc.py`는 수정 압축 파일이 기존 엔트리 할당 공간 안에 있을 때만 교체할 수 있다.
- 전체 번역에서는 한 아카이브 안의 여러 XSO가 각자 할당 공간을 넘을 가능성이 높다.
- 다음 단계에는 번역 CSV를 여러 XSO에 일괄 반영하는 체계와, 할당 초과 파일이 있을 때 아카이브 전체를 안전하게 재배치하는 방식을 분리해 설계해야 한다.
- 문자열 추가·삭제, 문자열 인덱스 변경 및 실행 명령 스트림 수정은 아직 지원하지 않는다.
