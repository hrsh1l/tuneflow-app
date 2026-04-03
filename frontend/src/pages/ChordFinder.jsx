function ChordFinder() {
  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <h1 style={styles.title}>AI Chord Finder</h1>
        <p style={styles.subtitle}>
          Upload a song file or paste a YouTube link to analyse the track and
          generate the chords needed to play it.
        </p>

        <div style={styles.inputSection}>
          <div style={styles.inputBox}>
            <label style={styles.label}>YouTube Link</label>
            <input
              type="text"
              placeholder="Paste a YouTube URL here"
              style={styles.input}
            />
          </div>

          <div style={styles.orText}>OR</div>

          <div style={styles.inputBox}>
            <label style={styles.label}>Upload Audio File</label>
            <input type="file" accept="audio/*" style={styles.fileInput} />
          </div>
        </div>

        <button style={styles.button}>Analyse Song</button>

        <div style={styles.resultsSection}>
          <h2 style={styles.resultsTitle}>Analysis Results</h2>
          <p style={styles.resultsText}>
            The detected chords and song structure will appear here once the song has been analysed.
          </p>

          <div style={styles.chordPreview}>
            <h3 style={styles.previewHeading}>Chord Preview</h3>
            <p style={styles.previewText}>G • Em • C • D</p>
          </div>

          <div style={styles.lyricsPreview}>
            <h3 style={styles.previewHeading}>Lyrics + Chords Preview</h3>
            <pre style={styles.preformatted}>
{`        G        Em
I found a love for me
  C
Darling, just dive right in
           D
And follow my lead
     G           Em
Well, I found a girl, beautiful and sweet
C
I never knew you were the someone
          D
waiting for me `}
            </pre>
          </div>
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