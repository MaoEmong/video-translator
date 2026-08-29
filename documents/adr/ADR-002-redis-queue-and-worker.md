# ADR-002: Redis Queue와 별도 Worker로 비동기 처리

- 상태: Accepted
- 결정일: 2026-08-29

## 문맥

영상 업로드 후 FFmpeg, STT, 번역, 자막 생성은 수 초 이상 걸릴 수 있다. 이를 API 요청 안에서
동기 처리하면 timeout이 발생하고, 사용자는 작업 진행률을 확인할 수 없다.

## 결정

FastAPI API는 작업과 단계를 PostgreSQL에 기록한 후 Redis Queue에 메시지를 넣고 `202 Accepted`
성격으로 응답한다. 별도 Python Worker가 메시지를 소비해 한 단계씩 처리한다.

- Job Step 상태를 `queued/running/completed/failed`로 저장한다.
- 단계 완료 후 다음 메시지를 enqueue한다.
- UI는 현재 polling으로 상태를 조회한다.
- API와 Worker는 같은 코드베이스지만 별도 프로세스로 실행한다.

## 고려한 대안

- API 프로세스의 background task: 초기 코드는 짧지만 프로세스 재시작 시 작업을 잃고 확장하기
  어렵다.
- Celery/RabbitMQ: 운영 기능은 풍부하지만 포트폴리오 MVP의 인프라 복잡도가 커진다.
- 완전 동기 API: 구현은 단순하지만 장시간 미디어 작업에 맞지 않는다.

## 결과

요청 응답과 미디어 처리 시간을 분리하고, 단계별 상태를 UI와 DB에서 확인할 수 있다. Redis는
메시지 전달을 담당하고, 영속적인 작업 상태의 기준은 PostgreSQL로 유지한다. 현재 자동 재시도와
Dead Letter Queue는 후속 작업이다.

## 구현 상태

`backend/app/queue/client.py`, `worker/main.py`, `worker/pipeline.py`에 반영되어 있다.
