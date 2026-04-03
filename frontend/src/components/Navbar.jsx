function Navbar() {
  return (
    <header style={styles.navbar}>
      <h2 style={styles.logo}>TuneFlow</h2>
      <nav style={styles.navLinks}>
        <a href="/" style={styles.link}>Home</a>
        <a href="/chord-finder" style={styles.link}>Chord Finder</a>
      </nav>
    </header>
  );
}

const styles = {
  navbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "20px 40px",
    backgroundColor: "#ffffff",
    borderBottom: "1px solid #ddd",
  },
  logo: {
    margin: 0,
    color: "#111",
    fontWeight: "bold",
    fontSize: "1.5rem",
  },
  navLinks: {
    display: "flex",
    gap: "20px",
  },
  link: {
    textDecoration: "none",
    color: "#111",
    fontWeight: "500",
  },
};

export default Navbar;