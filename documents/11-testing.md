# 11. 테스트 전략

## Unit Test

- chunk offset 보정
- 세그먼트 정렬
- 시간 겹침 검사
- SRT/VTT 생성
- 자막 줄바꿈
- JSON Schema 응답 검증
- retry와 backoff
- idempotency 처리
- 상태 전이 규칙

## Integration Test

- Object Storage 업로드와 signed URL
- PostgreSQL migration
- Queue 등록과 Worker 실행
- OpenAI API mock 응답
- 실패·재시도·중복 메시지
- artifact 생성과 checksum

## End-to-End Test

짧은 다국어 테스트 영상을 사용한다.

```text
업로드
  → 작업 생성
  → 오디오 추출
  → STT
  → 번역
  → SRT 생성
  → 다운로드
  → 번역문 편집
  → 자막 재생성
```

## 품질 평가

- STT: 정답 Transcript가 있는 테스트 세트의 WER/CER
- 번역: 언어별 자연스러움·정확성 사람 평가
- 자막: 시간 누락, 겹침, 줄 길이, 빈 문장 검사
- 비용: 영상 길이별 API 사용량과 작업당 비용

## 장애 테스트

- STT 요청 timeout
- 번역 API 429
- OpenAI 5xx
- Object Storage 일시 오류
- Worker 비정상 종료
- Queue 메시지 중복
- DB 연결 재시도
- 작업 중 사용자 취소

## 테스트 데이터

다음 특성을 가진 고정 fixture를 준비한다.

- 짧은 영어 대화
- 문장 중간의 pause
- 빠른 발화
- 고유명사와 숫자
- 여러 화자
- 긴 문장
- 자막 줄바꿈이 필요한 번역
