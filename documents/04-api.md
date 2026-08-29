# 04. 외부 API

기본 경로:

```text
/api/v1
```

## Endpoint 목록

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/videos/uploads` | 업로드 세션 생성 |
| POST | `/videos/{video_id}/complete` | 업로드 완료 통지 |
| GET | `/videos/{video_id}` | 영상 정보 조회 |
| POST | `/translation-jobs` | 번역 작업 생성 |
| GET | `/translation-jobs/{job_id}` | 작업 상태 조회 |
| POST | `/translation-jobs/{job_id}/cancel` | 작업 취소 |
| GET | `/translation-jobs/{job_id}/segments` | 세그먼트 조회 |
| PATCH | `/translation-jobs/{job_id}/segments/{segment_id}` | 번역문·표시 시간 수정 |
| POST | `/translation-jobs/{job_id}/retranslate` | 새 번역 버전 생성 |
| POST | `/translation-jobs/{job_id}/exports` | 자막 파일 생성 |
| GET | `/artifacts/{artifact_id}` | 결과 파일 정보·다운로드 URL 조회 |

## 업로드

### 요청

```http
POST /api/v1/videos/uploads
```

```json
{
  "filename": "lecture.mp4",
  "content_type": "video/mp4",
  "size_bytes": 104857600
}
```

### 응답

```json
{
  "video_id": "vid_123",
  "upload_url": "https://storage.example/signed-url",
  "expires_at": "2026-08-29T12:00:00Z"
}
```

## 번역 작업 생성

```http
POST /api/v1/translation-jobs
Idempotency-Key: <unique-key>
```

```json
{
  "video_id": "vid_123",
  "source_language": "auto",
  "target_language": "ko",
  "translation_style": "natural"
}
```

응답:

```json
{
  "id": "job_456",
  "video_id": "vid_123",
  "transcript_id": null,
  "status": "QUEUED",
  "current_step": "validate",
  "progress": 0,
  "target_language": "ko",
  "translation_style": "natural",
  "source_language": null,
  "created_at": "2026-08-29T12:00:00Z",
  "completed_at": null,
  "error_code": null
}
```

## 상태 조회

```http
GET /api/v1/translation-jobs/{job_id}
```

```json
{
  "id": "job_456",
  "video_id": "vid_123",
  "transcript_id": "tr_789",
  "status": "TRANSLATING",
  "current_step": "translate",
  "progress": 63,
  "source_language": "en",
  "target_language": "ko",
  "translation_style": "natural",
  "created_at": "2026-08-29T12:00:00Z",
  "completed_at": null,
  "error_code": null
}
```

## 세그먼트 수정

```http
PATCH /api/v1/translation-jobs/{job_id}/segments/{segment_id}
```

```json
{
  "translated_text": "어디 가는 중이야?",
  "display_start_ms": 1200,
  "display_end_ms": 4300
}
```

현재 버전은 요청 본문의 `version`을 받지 않으며, 수정할 때마다 서버가 세그먼트
`version`을 1 증가시킨다. 동시 편집 제어는 다음 단계에서 `If-Match` 또는 version 필드로
강화한다.

## Export

```http
POST /api/v1/translation-jobs/{job_id}/exports
```

```json
{
  "format": "srt"
}
```

Export는 비동기로 처리하며, 완료 후 signed download URL을 반환한다.

## 공통 규칙

- 장시간 작업 생성은 `202 Accepted` 성격으로 처리한다.
- 작업 생성, 재번역, export 요청의 Idempotency-Key 처리는 후속 작업으로 남겨 둔다.
- 모든 리소스에 사용자 소유권 검사를 적용한다.
- Object Storage key는 외부에 반환하지 않는다.
- 초기에는 Polling을 사용하고, 이후 필요하면 SSE로 확장한다.
- 수정 요청에는 version 또는 `If-Match`를 사용한다.
