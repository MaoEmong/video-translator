# 10. 품질 요구사항

포트폴리오 MVP는 모든 운영 품질 목표를 달성하는 것이 아니라, 핵심 품질 속성을 코드와 검증
결과로 설명할 수 있는 상태를 목표로 한다.

| 품질 속성 | 목표 | 현재 증거 |
|---|---|---|
| 비동기성 | 영상 처리 중 API 요청을 오래 점유하지 않는다. | API가 `202`와 Queue 메시지를 반환한다. |
| 추적성 | 작업과 단계별 실패 위치를 확인한다. | Job, Job Step, AI API Call 모델과 상태 polling |
| 정확성 | STT 시간축을 번역 결과에 보존한다. | timed segment adapter 및 subtitle builder 테스트 |
| 변경 용이성 | provider 교체가 API/Worker 전체 변경으로 번지지 않는다. | OpenAI Adapter 인터페이스 |
| 보안 | 브라우저에 API Key와 Storage key를 노출하지 않는다. | 서버 환경변수, signed URL |
| 재현성 | 로컬에서 같은 구성으로 실행할 수 있다. | Docker Compose, Alembic, README 실행 절차 |

현재 자동 테스트 19개가 통과했고, 실제 Docker·MinIO·FFmpeg·OpenAI 연결 smoke test도 완료했다.
장시간 영상 성능과 비용은 MVP 이후 측정 항목으로 남겨둔다.
