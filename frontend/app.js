const API = "/api/v1";
const state = { videoId: null, jobId: null, pollTimer: null, segments: [] };

const byId = (id) => document.getElementById(id);
const setHidden = (id, hidden) => byId(id).classList.toggle("hidden", hidden);

function showError(message) {
  const element = byId("error-message");
  element.textContent = message;
  element.classList.remove("hidden");
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `요청에 실패했습니다. (${response.status})`);
  return body;
}

function setProgress(progress, status) {
  const value = Math.max(0, Math.min(100, Number(progress) || 0));
  byId("progress-value").textContent = `${value}%`;
  byId("progress-bar").style.width = `${value}%`;
  byId("job-status").textContent = status;
}

function formatTime(ms) {
  return (Math.max(0, Number(ms) || 0) / 1000).toFixed(2);
}

async function pollJob() {
  if (!state.jobId) return;
  try {
    const job = await request(`/translation-jobs/${state.jobId}`);
    setProgress(job.progress, `${job.current_step || "queued"} · ${job.status}`);
    if (job.status === "COMPLETED") {
      clearInterval(state.pollTimer);
      await loadSegments();
      setHidden("editor-panel", false);
      byId("segments").scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (["FAILED", "CANCELLED"].includes(job.status)) {
      clearInterval(state.pollTimer);
      showError(`작업이 종료되었습니다: ${job.error_code || job.status}`);
    }
  } catch (error) {
    clearInterval(state.pollTimer);
    showError(error.message);
  }
}

async function loadSegments() {
  state.segments = await request(`/translation-jobs/${state.jobId}/segments`);
  const container = byId("segments");
  container.replaceChildren();
  state.segments.forEach((segment) => {
    const row = document.createElement("div");
    row.className = "segment";
    const number = document.createElement("div");
    number.className = "segment-number";
    number.textContent = String(segment.sequence_no).padStart(2, "0");
    const textLabel = document.createElement("label");
    const textTitle = document.createElement("span");
    textTitle.textContent = "번역문";
    const text = document.createElement("textarea");
    text.value = segment.translated_text;
    textLabel.append(textTitle, text);
    const timesLabel = document.createElement("label");
    const timesTitle = document.createElement("span");
    timesTitle.textContent = "표시 시간 (초)";
    const times = document.createElement("div");
    times.className = "time-fields";
    const start = document.createElement("input");
    start.type = "number";
    start.step = "0.01";
    start.min = "0";
    start.value = formatTime(segment.display_start_ms);
    const end = document.createElement("input");
    end.type = "number";
    end.step = "0.01";
    end.min = "0.01";
    end.value = formatTime(segment.display_end_ms);
    times.append(start, end);
    timesLabel.append(timesTitle, times);
    const save = document.createElement("button");
    save.className = "save-button";
    save.type = "button";
    save.textContent = "저장";
    save.addEventListener("click", async () => {
      save.disabled = true;
      try {
        const updated = await request(
          `/translation-jobs/${state.jobId}/segments/${segment.id}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              translated_text: text.value,
              display_start_ms: Math.round(Number(start.value) * 1000),
              display_end_ms: Math.round(Number(end.value) * 1000),
            }),
          },
        );
        segment.version = updated.version;
        save.textContent = "저장됨";
        setTimeout(() => { save.textContent = "저장"; }, 1200);
      } catch (error) {
        showError(error.message);
      } finally {
        save.disabled = false;
      }
    });
    row.append(number, textLabel, timesLabel, save);
    container.append(row);
  });
}

async function exportSubtitle() {
  const button = byId("export-button");
  button.disabled = true;
  setHidden("download-area", true);
  try {
    const format = byId("export-format").value;
    const created = await request(`/translation-jobs/${state.jobId}/exports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format }),
    });
    let artifact;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      artifact = await request(`/artifacts/${created.artifact_id}`);
      if (artifact.status === "completed") break;
      if (artifact.status === "failed") throw new Error(artifact.error_code || "파일 생성 실패");
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    if (!artifact || artifact.status !== "completed") throw new Error("파일 생성 시간이 초과되었습니다.");
    const area = byId("download-area");
    area.replaceChildren();
    const link = document.createElement("a");
    link.href = artifact.download_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = `${format.toUpperCase()} 자막 다운로드 →`;
    area.append(link);
    area.classList.remove("hidden");
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
}

byId("video-file").addEventListener("change", (event) => {
  const file = event.target.files[0];
  byId("file-label").textContent = file ? `${file.name} (${Math.ceil(file.size / 1024 / 1024)} MB)` : "영상 파일을 선택하세요";
});

byId("job-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = byId("video-file").files[0];
  if (!file) return;
  const button = byId("submit-button");
  button.disabled = true;
  setHidden("error-message", true);
  setHidden("progress-panel", false);
  setProgress(0, "업로드 세션을 준비하고 있습니다.");
  try {
    const upload = await request("/videos/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, content_type: file.type || "video/mp4", size_bytes: file.size }),
    });
    state.videoId = upload.video_id;
    setProgress(2, "영상 파일을 업로드하고 있습니다.");
    const uploaded = await fetch(upload.upload_url, { method: "PUT", headers: { "Content-Type": file.type || "video/mp4" }, body: file });
    if (!uploaded.ok) throw new Error("영상 업로드에 실패했습니다.");
    await request(`/videos/${state.videoId}/complete`, { method: "POST" });
    const job = await request("/translation-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_id: state.videoId,
        source_language: byId("source-language").value,
        target_language: byId("target-language").value,
        translation_style: byId("translation-style").value,
      }),
    });
    state.jobId = job.id;
    byId("job-id").textContent = `JOB ${job.id.slice(0, 8)}`;
    setProgress(job.progress, "번역 작업을 시작했습니다.");
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(pollJob, 1500);
    await pollJob();
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});

byId("export-button").addEventListener("click", exportSubtitle);
