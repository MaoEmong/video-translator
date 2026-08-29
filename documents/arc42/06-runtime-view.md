# 6. 런타임 뷰

## 번역 작업 흐름

```mermaid
sequenceDiagram
    actor User as 사용자
    participant UI as Web UI
    participant API as FastAPI API
    participant DB as PostgreSQL
    participant Q as Redis Queue
    participant W as Worker
    participant OAI as OpenAI
    participant S3 as MinIO/S3

    User->>UI: 영상 선택 및 목표 언어 입력
    UI->>API: 업로드 세션 요청
    API->>S3: signed upload URL 생성
    API-->>UI: video_id 및 upload URL
    UI->>S3: 영상 직접 업로드
    UI->>API: 업로드 완료
    API->>DB: video ready 저장
    UI->>API: 번역 작업 생성
    API->>DB: job 및 step 저장
    API->>Q: validate 메시지 등록
    API-->>UI: 202 Accepted
    Q->>W: 단계 메시지 전달
    W->>S3: 원본 다운로드 및 오디오 저장
    W->>OAI: STT 요청
    OAI-->>W: timed segments
    W->>OAI: 번역 요청
    OAI-->>W: 구조화된 번역 JSON
    W->>DB: 세그먼트와 상태 저장
    W->>S3: SRT artifact 저장
    UI->>API: 작업 상태 polling
    API-->>UI: progress 및 artifact
```

## 편집과 export 흐름

1. UI가 `GET /translation-jobs/{job_id}/segments`로 번역 세그먼트를 조회한다.
2. 사용자가 번역문 또는 표시 시간을 수정한다.
3. API가 `PATCH`로 DB의 translation segment를 갱신한다.
4. 사용자가 export를 요청하면 기존 버전의 세그먼트로 SRT/VTT를 생성한다.
5. artifact는 Storage에 저장하고 API는 만료되는 signed download URL을 반환한다.

## 실패 흐름

Worker가 오류를 내부 오류 코드로 변환하고 현재 step과 job을 실패 상태로 기록한다. 이미 성공한
artifact를 다시 export하는 요청은 동일 artifact를 재사용해 중복 파일 생성을 피한다.
