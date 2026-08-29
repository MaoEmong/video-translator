# 11. 위험과 기술 부채

| 위험 또는 부채 | 현재 대응 | 다음 확장 |
|---|---|---|
| provider 모델별 응답 형식 차이 | Adapter와 실제 smoke test로 검증 | 모델 capability matrix와 contract test |
| 긴 영상의 메모리·timeout 증가 | 짧은 영상 MVP로 범위 제한 | chunk 분할, offset 보정, 단계별 재시도 |
| Queue 중복/재시작 | DB step과 artifact 재사용 로직 | 명시적 idempotency key, DLQ |
| 사용자 데이터 접근 통제 부재 | 로컬 단일 사용자 전제 | 인증과 리소스 소유권 검사 |
| OpenAI 비용 증가 | 사용량 모델과 설정 분리 | quota, 비용 상한, 사용자별 rate limit |
| 원본 영상 보관 정책 부재 | 개발용 로컬 Storage | lifecycle rule, 자동 삭제, 보존 동의 |
| 실시간 운영 가시성 부족 | DB에 단계/호출 정보 기록 | 구조화 로그, metrics, trace, alert |

이 표의 항목은 MVP가 실패했다는 뜻이 아니라, 포트폴리오 범위를 의도적으로 제한한 결과와
운영 확장 시의 작업 순서를 공개하는 기록이다.
