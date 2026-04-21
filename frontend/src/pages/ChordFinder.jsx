import { useMemo, useState } from "react";
import { analyzeSong } from "../api";

function ChordFinder() {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const canAnalyse = useMemo(
    () => Boolean(audioFile || youtubeUrl.trim()),
    [audioFile, youtubeUrl],
  );

  async function handleAnalyse() {
    if (!canAnalyse) {
      setError("Please choose an audio file or paste a YouTube URL.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const payload = await analyzeSong({
        youtubeUrl: youtubeUrl.trim(),
        audioFile,
      });
      setResult(payload);
    } catch (requestError) {
      setResult(null);
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  function formatSeconds(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "--";
    }
    const minutes = Math.floor(value / 60);
    const seconds = Math.floor(value % 60)
      .toString()
      .padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <h1 style={styles.title}>AI Chord Finder</h1>
        <p style={styles.subtitle}>
          Upload a song file or paste a YouTube link to analyse the track and
          generate chords aligned with transcribed lyric lines.
        </p>

        <div style={styles.inputSection}>
          <div style={styles.inputBox}>
            <label style={styles.label}>YouTube Link</label>
            <input
              type="text"
              placeholder="Paste a YouTube URL here"
              style={styles.input}
              value={youtubeUrl}
              onChange={(event) => setYoutubeUrl(event.target.value)}
            />
            <small style={styles.helperText}>
              Paste a YouTube link to analyse directly from the video audio.
            </small>
          </div>

          <div style={styles.orText}>OR</div>

          <div style={styles.inputBox}>
            <label style={styles.label}>Upload Audio File</label>
            <input
              type="file"
              accept="audio/*"
              style={styles.fileInput}
              onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        <button
          style={{
            ...styles.button,
            ...(isLoading || !canAnalyse ? styles.buttonDisabled : {}),
          }}
          onClick={handleAnalyse}
          disabled={isLoading || !canAnalyse}
        >
          {isLoading ? "Analysing..." : "Analyse Song"}
        </button>

        {error ? <p style={styles.errorText}>{error}</p> : null}

        <div style={styles.resultsSection}>
          <h2 style={styles.resultsTitle}>Analysis Results</h2>
          {!result ? (
            <p style={styles.resultsText}>
              The detected chords and song structure will appear here once the
              song has been analysed.
            </p>
          ) : (
            <>
              <p style={styles.resultsText}>
                Title: <strong>{result.title || "Untitled"}</strong>
              </p>
              <p style={styles.resultsText}>
                Key: <strong>{result.key || "Unknown"}</strong> | Duration:{" "}
                <strong>{formatSeconds(result.duration)}</strong>
              </p>

              <div style={styles.chordPreview}>
                <h3 style={styles.previewHeading}>Chord Progression</h3>
                <p style={styles.previewText}>
                  {[...new Set((result.lines || []).flatMap((line) => line.chords || []))].join(
                    " - ",
                  ) || "No chords detected yet."}
                </p>
              </div>

              <div style={styles.lyricsPreview}>
                <h3 style={styles.previewHeading}>Lyrics + Chords</h3>
                {(result.sections || []).length > 0 ? (
                  (result.sections || []).map((section) => (
                    <div key={section.name} style={styles.sectionBlock}>
                      <h4 style={styles.sectionHeading}>[{section.name}]</h4>
                      {(section.lines || []).map((line, index) => (
                        <pre style={styles.preformatted} key={`${section.name}-${index}`}>
                          {(line.chord_line || line.chords.join(" ") || "N") + "\n"}
                          {line.text || ""}
                        </pre>
                      ))}
                    </div>
                  ))
                ) : (
                  <pre style={styles.preformatted}>
                    {(result.lines || [])
                      .map(
                        (line) =>
                          `${line.start.toFixed(2)}s - ${line.end.toFixed(2)}s | ${line.chords.join(" ") || "N"}\n${line.text}`,
                      )
                      .join("\n\n") || "No aligned lyric/chord output available."}
                  </pre>
                )}
              </div>

            </>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    backgroundColor: "#f5f7fb",
    fontFamily: "Arial, sans-serif",
    padding: "40px 20px",
  },
  container: {
    maxWidth: "900px",
    margin: "0 auto",
    backgroundColor: "#ffffff",
    borderRadius: "16px",
    padding: "40px",
    boxShadow: "0 6px 20px rgba(0,0,0,0.08)",
  },
  title: {
    fontSize: "2.5rem",
    color: "#111",
    marginBottom: "10px",
    textAlign: "center",
  },
  subtitle: {
    fontSize: "1.05rem",
    color: "#555",
    lineHeight: "1.6",
    textAlign: "center",
    marginBottom: "35px",
  },
  inputSection: {
    display: "flex",
    flexDirection: "column",
    gap: "20px",
    marginBottom: "30px",
  },
  inputBox: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  label: {
    fontWeight: "600",
    color: "#222",
  },
  input: {
    padding: "14px",
    fontSize: "1rem",
    borderRadius: "10px",
    border: "1px solid #ccc",
  },
  fileInput: {
    padding: "10px",
    fontSize: "1rem",
    borderRadius: "10px",
    border: "1px solid #ccc",
    backgroundColor: "#fff",
  },
  helperText: {
    color: "#666",
    fontSize: "0.85rem",
  },
  orText: {
    textAlign: "center",
    fontWeight: "bold",
    color: "#666",
  },
  button: {
    display: "block",
    margin: "0 auto 35px",
    padding: "14px 28px",
    fontSize: "1rem",
    border: "none",
    borderRadius: "10px",
    cursor: "pointer",
    backgroundColor: "#222",
    color: "#fff",
  },
  buttonDisabled: {
    backgroundColor: "#7a7a7a",
    cursor: "not-allowed",
  },
  errorText: {
    marginTop: "-15px",
    marginBottom: "25px",
    color: "#b00020",
    textAlign: "center",
    fontWeight: "600",
  },
  resultsSection: {
    backgroundColor: "#fafafa",
    border: "1px solid #e5e5e5",
    borderRadius: "14px",
    padding: "25px",
  },
  resultsTitle: {
    marginTop: 0,
    color: "#111",
  },
  resultsText: {
    color: "#555",
    marginBottom: "25px",
  },
  chordPreview: {
    marginBottom: "25px",
    padding: "20px",
    backgroundColor: "#f0f4f8",
    borderRadius: "12px",
  },
  lyricsPreview: {
    padding: "20px",
    backgroundColor: "#f0f4f8",
    borderRadius: "12px",
  },
  sectionBlock: {
    marginBottom: "20px",
  },
  sectionHeading: {
    margin: "10px 0",
    color: "#1c2a4a",
  },
  previewHeading: {
    marginTop: 0,
    color: "#111",
  },
  previewText: {
    fontSize: "1.2rem",
    fontWeight: "600",
    color: "#222",
  },
  preformatted: {
    whiteSpace: "pre-wrap",
    fontFamily: "monospace",
    color: "#222",
    margin: 0,
  },
};

export default ChordFinder;
