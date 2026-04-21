const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const ANALYSIS_TIMEOUT_MS = 180000;

export async function analyzeSong({ youtubeUrl, audioFile }) {
  const normalizedYoutubeUrl = youtubeUrl?.trim() ?? "";
  if (!audioFile && !normalizedYoutubeUrl) {
    throw new Error("Please upload an audio file or paste a YouTube URL.");
  }

  const formData = new FormData();
  if (audioFile) {
    formData.append("file", audioFile);
  } else if (normalizedYoutubeUrl) {
    formData.append("youtube_url", normalizedYoutubeUrl);
  }

  let response;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ANALYSIS_TIMEOUT_MS);

  try {
    response = await fetch(`${API_BASE_URL}/analyze`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
  } catch (networkError) {
    if (networkError.name === "AbortError") {
      throw new Error(
        "Analysis timed out after 3 minutes. Try a shorter clip or check backend logs.",
      );
    }

    throw new Error(
      `Cannot reach backend at ${API_BASE_URL}. Start FastAPI and try again.`,
    );
  } finally {
    clearTimeout(timeoutId);
  }

  const payload = await response
    .json()
    .catch(async () => ({ detail: (await response.text()) || "Unexpected response from backend." }));

  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : payload.error;
    throw new Error(detail || "Unable to analyse the song.");
  }

  return payload;
}
