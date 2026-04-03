function Hero() {
  return (
    <main style={styles.hero}>
      <div style={styles.heroText}>
        <h1 style={styles.title}>Stay in tune. Stay in flow.</h1>
        <p style={styles.subtitle}>
          A simple website to help guitarists find chords for their favourite songs
        </p>
        <button style={styles.button}>Get Started</button>
      </div>
    </main>
  );
}

const styles = {
  hero: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    textAlign: "center",
    padding: "80px 20px 50px",
  },
  heroText: {
    maxWidth: "700px",
  },
  title: {
    fontSize: "2rem",
    marginBottom: "20px",
    color: "#111",
  },
  subtitle: {
    fontSize: "1.1rem",
    lineHeight: "1.6",
    marginBottom: "30px",
    color: "#555",
  },
  button: {
    padding: "12px 24px",
    fontSize: "1rem",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    backgroundColor: "#222",
    color: "white",
  },
};

export default Hero;