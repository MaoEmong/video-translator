# 10. 배포와 인프라

## 초기 구성

현재 로컬 MVP에서는 FastAPI가 정적 Web UI도 함께 제공하므로 Frontend와 Backend API를 별도
서비스로 나누지 않는다. 아래의 독립 Frontend 서비스 구성은 운영 확장안이다.

```text
Frontend
Backend API  ───── PostgreSQL
     │             Redis / Queue
     │             Object Storage
     └──── Worker ─ OpenAI API
```

## 배포 단위

- API와 정적 Web UI 서비스 1개
- Worker 서비스 1개
- PostgreSQL
- Redis 또는 Queue 서비스
- S3 호환 Object Storage

## 환경

```text
local
staging
production
```

환경별로 다음을 분리한다.

- DB
- Object Storage bucket
- Queue
- OpenAI API key/project
- 로그와 모니터링

## 확장

- API는 stateless 수평 확장
- Worker는 Queue 종류별로 수평 확장
- Media Worker와 OpenAI Worker의 동시성을 별도 설정
- OpenAI 호출은 rate limit에 맞춰 제한
- 장시간 작업은 CPU와 메모리 기준으로 별도 autoscaling

## DB 운영

- migration은 코드로 관리한다.
- 운영 배포 전 migration을 검증한다.
- 정기 백업과 복구 테스트를 수행한다.
- 큰 세그먼트 조회에는 cursor pagination을 사용한다.
- 원본 영상과 DB 백업의 보존 기간을 별도로 관리한다.

## 파일 운영

- 원본 영상, 오디오, 결과 파일을 prefix로 분리한다.
- 파일명 대신 서버 생성 key를 사용한다.
- checksum으로 업로드와 결과 파일 무결성을 확인한다.
- 만료된 임시 오디오와 chunk는 scheduler가 삭제한다.

## CI/CD

```text
lint
  → unit test
  → integration test
  → migration check
  → build image
  → staging deploy
  → smoke test
  → production deploy
```
