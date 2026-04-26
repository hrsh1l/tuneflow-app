function FeatureCard({ title, description }) {
  return (
    <div style={styles.card}>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

const styles = {
  card: {
    backgroundColor: "#f7fcff",
    padding: "25px",
    borderRadius: "12px",
    border: "1px solid #b9ddf5",
    boxShadow: "0 8px 18px rgba(25, 118, 185, 0.12)",
    width: "280px",
    textAlign: "center",
    color: "#123047",
  },
};

export default FeatureCard;
