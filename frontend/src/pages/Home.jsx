import Navbar from "../components/Navbar";
import Hero from "../components/Hero";
import FeatureCard from "../components/FeatureCard";

function Home() {
  return (
    <div style={styles.page}>
      <Navbar />
      <Hero />

      <section style={styles.features}>
        <FeatureCard
          title="Play your favourite songs"
          description="Upload your favourite song and TuneFlow will give you the chords to play it."
        />
        <FeatureCard
          title="Easy to Use"
          description="Designed for beginners and experienced players alike."
        />
      </section>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    backgroundColor: "#f5f7fb",
    fontFamily: "Arial, sans-serif",
    color: "#222",
  },
  features: {
    display: "flex",
    justifyContent: "center",
    gap: "20px",
    padding: "20px 40px 60px",
    flexWrap: "wrap",
  },
};

export default Home;