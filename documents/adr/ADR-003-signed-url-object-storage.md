# ADR-003: Private Object Storage와 signed URL 사용

- 상태: Accepted
- 결정일: 2026-08-29

## 문맥

영상은 API 서버보다 크고, 업로드와 다운로드를 API 서버가 모두 중계하면 서버 메모리와 네트워크
부하가 커진다. 원본 영상과 자막 artifact도 DB binary로 저장하지 않는 편이 적합하다.

## 결정

원본 영상, 정규화 오디오, 생성 자막은 private MinIO/S3 bucket에 저장한다. API는 제한된 시간의
signed upload/download URL을 발급하고 브라우저는 Storage와 직접 통신한다.

- Storage key는 서버가 생성한다.
- API Key와 Storage credential은 서버 환경변수에 둔다.
- artifact 메타데이터와 소유 관계는 PostgreSQL에 저장한다.

## 고려한 대안

- API 서버를 통한 multipart upload/download: 구현은 쉽지만 큰 파일에 비효율적이다.
- public bucket URL: 사용이 쉽지만 영상과 결과물이 노출된다.
- DB에 파일을 BLOB으로 저장: 데이터 일관성은 단순하지만 용량과 백업 비용이 커진다.

## 결과

대용량 파일 경로와 애플리케이션 요청 경로를 분리하고, private storage 보안 경계를 유지한다.
대신 URL 만료와 upload complete 검증, Storage 장애 처리를 반드시 다뤄야 한다.

## 구현 상태

`backend/app/storage/s3.py`, `backend/app/api/routes/videos.py`,
`backend/app/api/routes/artifacts.py`에 반영되어 있다.
