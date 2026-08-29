# 09. 관측성과 운영

## 로그 상관관계

모든 로그에 다음 필드를 포함한다.

```text
request_id
video_id
job_id
job_step_id
ai_api_request_id
```

로그는 구조화된 JSON으로 출력한다.

## 주요 지표

### 제품 지표

- 업로드 성공·실패율
- 번역 작업 완료율
- 작업당 처리 시간
- 사용자 편집 비율
- 결과 다운로드 수

### 파이프라인 지표

- 단계별 처리 시간
- Queue 대기 시간
- 재시도 횟수
- Dead Letter Queue 크기
- 단계별 실패율
- 자막 품질 검사 실패율

### OpenAI 지표

- STT 호출 수
- 번역 호출 수
- 429 횟수
- Timeout 횟수
- 입력·출력 사용량
- 작업당 예상 비용
- API 지연 시간

## 추적

하나의 사용자 요청에서 다음 계층을 연결한다.

```text
HTTP Request
  → Translation Job
  → Job Step
  → Queue Message
  → OpenAI API Call
```

## 알림

- Queue 적체 증가
- 특정 단계의 연속 실패
- OpenAI 오류율 급증
- 429 증가
- Storage 용량 부족
- DB 연결 실패
- 자동 삭제 작업 실패

## 운영 화면

초기에는 로그와 DB 조회만으로 시작하고, 이후 다음 화면을 추가한다.

- 전체 작업 상태
- 실패 작업과 재시도 버튼
- 사용자별 사용량
- API 비용 추정
- 단계별 평균 처리 시간
