# 2. 제약사항

## 기술 제약

| 제약 | 영향 |
|---|---|
| STT와 번역은 OpenAI API 사용 | 네트워크, 모델 가용성, provider 오류를 고려해야 한다. |
| 영상 처리는 FFmpeg 사용 | 실행 환경에 FFmpeg가 설치되어야 한다. |
| PostgreSQL, Redis, MinIO는 로컬 Docker로 실행 | MVP 설치와 시연을 단순하게 유지한다. |
| API Key는 서버 환경변수에만 존재 | 브라우저에 provider credential을 전달하지 않는다. |
| 포트폴리오 MVP | 인증, quota, 장시간 chunking, 운영 대시보드는 범위 밖이다. |

## 제품 제약

- 기본 사용자는 개발자 한 명이며 현재 사용자 인증은 구현하지 않는다.
- 현재 파이프라인은 MVP 범위에 맞춰 짧은 영상과 단일 로컬 실행 환경을 우선한다.
- 모델명과 연결 정보는 환경변수로 바꿀 수 있어 provider 변경 여지를 남긴다.

운영 서비스로 확장할 때 필요한 제약과 부채는 [위험과 기술 부채](./11-risks-and-technical-debt.md)에
정리한다.
