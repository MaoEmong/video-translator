# 02. 처리 파이프라인

현재 MVP 코드는 업로드된 영상을 하나의 16 kHz mono WAV로 정규화한 뒤 처리한다. `ffprobe`
메타데이터 검증과 장시간 영상 chunk 분할은 다음 안정화 단계에서 추가한다.

## 전체 단계

```text
VALIDATE
  → EXTRACT_AUDIO
  → TRANSCRIBE
  → NORMALIZE_SEGMENTS
  → TRANSLATE
  → BUILD_SUBTITLE
  → QUALITY_CHECK
  → FINALIZE
```

## 1. 파일 검증

- Object Storage에 파일이 실제로 존재하는지 확인한다.
- 확장자, MIME 타입, 파일 크기를 검증한다.
- `ffprobe`로 컨테이너, 길이, 오디오 트랙, 코덱을 확인한다.
- 오디오 트랙이 없으면 사용자 오류로 종료한다.

## 2. 오디오 추출과 분할

- FFmpeg로 오디오 트랙을 추출한다.
- STT 입력에 적합한 표준 오디오 포맷으로 정규화한다.
- 긴 오디오는 설정된 기준에 따라 chunk로 나눈다.
- 각 chunk에는 `chunk_index`와 `offset_ms`를 부여한다.
- STT 결과의 상대 시간을 `offset_ms`를 더해 전체 영상 시간으로 변환한다.
- chunk 경계에서 중복된 텍스트가 생기면 후처리로 제거한다.

## 3. STT

- `OpenAISttAdapter`가 각 오디오 chunk를 처리한다.
- source language는 자동 감지를 기본값으로 한다.
- 도메인 용어가 있으면 keyword hint 옵션으로 전달할 수 있게 한다.
- 원문, 시간 정보, provider metadata를 Transcript로 저장한다.
- 모든 chunk가 성공한 뒤에만 Transcript를 `completed`로 전환한다.
- Translation Job의 `transcript_id`를 완료된 Transcript에 연결한다.

## 4. 원문 세그먼트 정리

- 문장부호와 pause를 기준으로 자막 단위를 정리한다.
- 각 세그먼트에 `sequence_no`를 부여한다.
- `start_ms`, `end_ms`는 정수 밀리초로 저장한다.
- 원문 세그먼트 ID는 번역 언어와 무관하게 유지한다.

## 5. 번역

- 세그먼트 여러 개를 문맥 묶음으로 구성한다.
- 요청에는 `segment_id`와 `source_text`를 포함한다.
- 목표 언어, 말투, 용어집 설정을 함께 전달한다.
- LLM은 `segment_id`와 `translated_text`만 반환한다.
- 시간 정보는 원문 세그먼트에서 복사한다.
- 응답의 누락·중복·알 수 없는 ID를 검증한다.

## 6. 자막 생성과 품질 검사

- 기본 시간은 원문 세그먼트의 `start_ms`, `end_ms`를 사용한다.
- 사용자가 수정한 표시 시간이 있으면 이를 우선한다.
- 빈 자막, 음수 시간, 시간 역전, 비정상적으로 긴 줄을 검사한다.
- SRT 또는 VTT를 생성하고 checksum을 저장한다.

## 실패와 재시작

각 단계의 결과는 완료 즉시 DB와 Object Storage에 저장한다. 실패하면 전체 파이프라인이 아니라 해당 단계부터 재시작한다.
