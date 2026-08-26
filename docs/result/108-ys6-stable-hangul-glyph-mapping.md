# 108. Ys VI 한글 글리프 매핑 영구 고정 결과

상태: 완료

## 수행 내용

- 102번 정상 동작 EBOOT의 글리프 비트맵을 기준으로 현재 978개 한글 매핑을 역추적했다.
- 기존 동적 매핑과 다른 179개 배정을 102번 기준 코드·폰트 인덱스로 복원했다.
- `hangul-mapping-uljm05009.json`을 schema v2, mapping revision 1의 canonical 매핑으로 확정했다.
- 일반 사전 검증 및 ISO 빌드가 canonical 매핑을 읽도록 변경했다.
- 번역 순서에 따라 빈 슬롯을 다시 배정하던 동작을 제거했다.
- 미등록 한글이 있으면 빌드를 중단하고 canonical 매핑 갱신을 요구하도록 변경했다.
- GUI에 `글리프 매핑 갱신` 버튼과 revision·전체 글자 수·미등록 글자 수 표시를 추가했다.
- 명시적 갱신은 기존 배정을 그대로 보존하고, Unicode 순으로 정렬된 새 문자만 안전한 미사용 슬롯에 추가한다.
- 사전 검증 보고서와 빌드 manifest에 매핑 revision 및 SHA-256을 기록한다.

## 생성·변경 파일

- `tools/patchdata/hangul-mapping-uljm05009.json`
- `tools/scripts/ys6_hangul_mapping_lock.py`
- `tools/scripts/ys6_hangul_codec.py`
- `tools/scripts/ys6_integrated_build.py`
- `tools/scripts/ys6_patch_builder.py`
- `tools/ys6_dialogue_viewer.py`
- `tools/patchdata/build-config.json`
- `tools/patchdata/work/current/108-stable-hangul-mapping/baseline-audit.json`
- `tools/patchdata/work/current/108-stable-hangul-mapping/glyph-compatibility.json`

## 검증 결과

- Python 구문 검사: 통과
- canonical 매핑 유일성 검사: 978자 모두 문자·게임 코드·폰트 인덱스 중복 없음
- 현재 번역 데이터 미등록 글자 검사: 0자
- 번역 입력 순서 역전 검사: 기존 978개 배정 불변
- 격리 신규 글자 추가 검사: 기존 978개 불변, 신규 1개만 추가
- 신규 글자 제거 후 재검사: 추가된 배정이 축소·재사용되지 않음
- 102번 기준 EBOOT 대비 978개 글리프 비트맵 불일치: 0개
- 전체 옵션 및 아날로그 스틱을 포함한 실제 사전 검증: 통과
- 사전 검증 결과: 대사 5,288, XSO 563, 아카이브 79, 독립 XSO 555, 인물·몬스터명 70, 아이템 73, 시스템 메시지 161, 글리프 978, overflow 0
- canonical 매핑 SHA-256: `C911999AADDBC82738C554570ACB20C77D49338650884719035EA6A437311FEB`
- 생성 EBOOT SHA-256: `9ABBCC83C717259FA6F1791E270A23618E8B34C2254AAB2C301D94FFAA81C0A5`

## 동작 방식

- 평상시 `사전 검증`과 `패치 ISO 만들기`는 매핑을 수정하지 않는다.
- 새 한글이 발견되면 미등록 문자 오류로 중단한다.
- GUI에서 `글리프 매핑 갱신`을 누르면 추가 문자 목록을 확인한 뒤에만 revision을 올리고 append-only로 저장한다.
- 기존 번역에서 글자가 사라져도 그 글자의 매핑은 삭제하지 않는다. 따라서 기존 세이브의 코드 해석이 유지된다.

## 알려진 문제 및 정리 대상

- 실제 PSP 세이브 파일 자체를 자동 변환하지 않는다. 이번 변경은 이후 빌드에서 기존 코드 배정을 유지해 추가 손상을 막는 방식이다.
- canonical 파일과 검증 자료는 현재 저장소의 `tools/patchdata` ignore 정책 대상이므로 배포 묶음 생성 시 반드시 포함해야 한다.
- 이번 작업에서 새 테스트 ISO는 생성하지 않았다. 정리할 임시 ROM은 없다.
