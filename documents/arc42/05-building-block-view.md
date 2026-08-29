# 5. 구성 블록 뷰

## 레벨 1: 시스템

Video Translator는 Web UI, FastAPI API, 비동기 Worker, 데이터 저장소, OpenAI Platform으로
구성된다. 전체 관계는 [C4 시스템 컨텍스트](../c4/01-system-context.md)에 있다.

## 레벨 2: 컨테이너

| 컨테이너 | 책임 | 현재 구현 |
|---|---|---|
| Web UI | 업로드, 작업 상태, 세그먼트 편집, export | `frontend/` |
| FastAPI API | HTTP API, DB 기록, signed URL, Queue 등록 | `backend/app/api/` |
| Redis Queue | 작업 메시지 전달 | `backend/app/queue/` |
| Worker | 단계별 미디어·AI·자막 처리 | `worker/` |
| PostgreSQL | 영상, 작업, 세그먼트, 버전, 호출 기록 저장 | `backend/app/db/` |
| MinIO/S3 | 원본, 오디오, 자막 artifact 저장 | `backend/app/storage/` |
| OpenAI Platform | STT 및 번역 모델 실행 | `backend/app/providers/` |

상세 관계는 [C4 컨테이너 뷰](../c4/02-container.md)를 참조한다.

## 레벨 3: 주요 컴포넌트

- API: `videos` 라우트, `jobs` 라우트, `artifacts` 라우트, DB/Queue/Storage 의존성
- Worker: 단계 dispatcher, FFmpeg 처리, OpenAI Adapter, 자막 builder, 실패 처리

컴포넌트 간 흐름은 [C4 컴포넌트 뷰](../c4/03-component.md)에 정리한다.
