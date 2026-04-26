import { useMemo, useState } from "react";
import { analyzeSong } from "../api";
import Navbar from "../components/Navbar";

function ChordFinder() {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isEditingLyrics, setIsEditingLyrics] = useState(false);

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
      setIsEditingLyrics(false);
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

  function handleSectionLyricChange(sectionIndex, lineIndex, text) {
    setResult((currentResult) => {
      if (!currentResult) {
        return currentResult;
      }

      const sections = (currentResult.sections || []).map((section, currentSectionIndex) => {
        if (currentSectionIndex !== sectionIndex) {
          return section;
        }

        return {
          ...section,
          lines: (section.lines || []).map((line, currentLineIndex) =>
            currentLineIndex === lineIndex ? { ...line, text } : line,
          ),
        };
      });

      return { ...currentResult, sections };
    });
  }

  function handleLineLyricChange(lineIndex, text) {
    setResult((currentResult) => {
      if (!currentResult) {
        return currentResult;
      }

      return {
        ...currentResult,
        lines: (currentResult.lines || []).map((line, currentLineIndex) =>
          currentLineIndex === lineIndex ? { ...line, text } : line,
        ),
      };
    });
  }

  return (
    <div style={styles.page}>
      <Navbar />
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
          <div style={styles.resultsHeader}>
            <h2 style={styles.resultsTitle}>Analysis Results</h2>
            {result ? (
              <button
                style={styles.editLyricsButton}
                onClick={() => setIsEditingLyrics((editing) => !editing)}
              >
                {isEditingLyrics ? "Done Editing" : "Edit Lyrics"}
              </button>
            ) : null}
          </div>
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
                  (result.sections || []).map((section, sectionIndex) => (
                    <div key={section.name} style={styles.sectionBlock}>
                      <h4 style={styles.sectionHeading}>[{section.name}]</h4>
                      {(section.lines || []).map((line, index) => (
                        <div style={styles.lyricLineEditor} key={`${section.name}-${index}`}>
                          <pre style={styles.preformatted}>
                            {line.chord_line || line.chords.join(" ") || "N"}
                          </pre>
                          {isEditingLyrics ? (
                            <textarea
                              style={styles.lyricTextarea}
                              value={line.text || ""}
                              onChange={(event) =>
                                handleSectionLyricChange(
                                  sectionIndex,
                                  index,
                                  event.target.value,
                                )
                              }
                            />
                          ) : (
                            <pre style={styles.preformatted}>{line.text || ""}</pre>
                          )}
                        </div>
                      ))}
                    </div>
                  ))
                ) : (
                  <div>
                    {(result.lines || []).length > 0 ? (
                      (result.lines || []).map((line, index) => (
                        <div style={styles.lyricLineEditor} key={`${line.start}-${index}`}>
                          <pre style={styles.preformatted}>
                            {`${line.start.toFixed(2)}s - ${line.end.toFixed(2)}s | ${line.chords.join(" ") || "N"}`}
                          </pre>
                          {isEditingLyrics ? (
                            <textarea
                              style={styles.lyricTextarea}
                              value={line.text || ""}
                              onChange={(event) =>
                                handleLineLyricChange(index, event.target.value)
                              }
                            />
                          ) : (
                            <pre style={styles.preformatted}>{line.text || ""}</pre>
                          )}
                        </div>
                      ))
                    ) : (
                      <pre style={styles.preformatted}>
                        No aligned lyric/chord output available.
                      </pre>
                    )}
                  </div>
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
    background: "linear-gradient(180deg, #eaf7ff 0%, #d8efff 100%)",
    fontFamily: "Arial, sans-serif",
  },
  container: {
    width: "calc(100% - 40px)",
    maxWidth: "900px",
    margin: "40px auto",
    backgroundColor: "#f7fcff",
    borderRadius: "16px",
    padding: "40px",
    boxSizing: "border-box",
    border: "1px solid #b9ddf5",
    boxShadow: "0 12px 28px rgba(25, 118, 185, 0.14)",
  },
  title: {
    fontSize: "2.5rem",
    color: "#102a43",
    marginBottom: "10px",
    textAlign: "center",
  },
  subtitle: {
    fontSize: "1.05rem",
    color: "#4c647a",
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
    color: "#123047",
  },
  input: {
    padding: "14px",
    fontSize: "1rem",
    borderRadius: "10px",
    border: "1px solid #9fd0ef",
    backgroundColor: "#ffffff",
    color: "#102a43",
  },
  fileInput: {
    padding: "10px",
    fontSize: "1rem",
    borderRadius: "10px",
    border: "1px solid #9fd0ef",
    backgroundColor: "#fff",
    color: "#102a43",
  },
  helperText: {
    color: "#5f7890",
    fontSize: "0.85rem",
  },
  orText: {
    textAlign: "center",
    fontWeight: "bold",
    color: "#4c83a8",
  },
  button: {
    display: "block",
    margin: "0 auto 35px",
    padding: "14px 28px",
    fontSize: "1rem",
    border: "none",
    borderRadius: "10px",
    cursor: "pointer",
    backgroundColor: "#1976b9",
    color: "#fff",
    boxShadow: "0 8px 18px rgba(25, 118, 185, 0.22)",
  },
  buttonDisabled: {
    backgroundColor: "#8cb8d4",
    cursor: "not-allowed",
    boxShadow: "none",
  },
  errorText: {
    marginTop: "-15px",
    marginBottom: "25px",
    color: "#b00020",
    textAlign: "center",
    fontWeight: "600",
  },
  resultsSection: {
    backgroundColor: "#eef8ff",
    border: "1px solid #b9ddf5",
    borderRadius: "14px",
    padding: "25px",
  },
  resultsHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "16px",
    marginBottom: "10px",
  },
  resultsTitle: {
    marginTop: 0,
    marginBottom: 0,
    color: "#102a43",
  },
  editLyricsButton: {
    padding: "10px 16px",
    fontSize: "0.95rem",
    border: "1px solid #9fd0ef",
    borderRadius: "10px",
    cursor: "pointer",
    backgroundColor: "#ffffff",
    color: "#0f5f99",
    fontWeight: "600",
  },
  resultsText: {
    color: "#4c647a",
    marginBottom: "25px",
  },
  chordPreview: {
    marginBottom: "25px",
    padding: "20px",
    backgroundColor: "#dff1fb",
    borderRadius: "12px",
    border: "1px solid #b9ddf5",
  },
  lyricsPreview: {
    padding: "20px",
    backgroundColor: "#dff1fb",
    borderRadius: "12px",
    border: "1px solid #b9ddf5",
  },
  sectionBlock: {
    marginBottom: "20px",
  },
  sectionHeading: {
    margin: "10px 0",
    color: "#1c2a4a",
  },
  lyricLineEditor: {
    marginBottom: "16px",
  },
  lyricTextarea: {
    width: "100%",
    minHeight: "54px",
    resize: "vertical",
    boxSizing: "border-box",
    marginTop: "4px",
    padding: "10px 12px",
    border: "1px solid #9fd0ef",
    borderRadius: "10px",
    backgroundColor: "#ffffff",
    color: "#123047",
    fontFamily: "monospace",
    fontSize: "0.95rem",
    lineHeight: "1.5",
  },
  previewHeading: {
    marginTop: 0,
    color: "#102a43",
  },
  previewText: {
    fontSize: "1.2rem",
    fontWeight: "600",
    color: "#123047",
  },
  preformatted: {
    whiteSpace: "pre-wrap",
    fontFamily: "monospace",
    color: "#123047",
    margin: 0,
  },
};

export default ChordFinder;
