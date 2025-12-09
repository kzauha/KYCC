import { Link } from "react-router-dom";

export default function Sidebar() {
  return (
    <div style={styles.sidebar}>
      <h2 style={styles.title}>KYCC</h2>

      <nav style={styles.nav}>
        <Link style={styles.link} to="/">📋 Party List</Link>
        <Link style={styles.link} to="/new">➕ Create Party</Link>
        <Link style={styles.link} to="/relationship">🔗 Relationships</Link>
        <Link style={styles.link} to="/network">🌐 Network Graph</Link>
        <Link style={styles.link} to="/credit">💳 Credit Score</Link>
        <Link style={styles.link} to="/upload">📁 Upload CSV</Link>
      </nav>
    </div>
  );
}

const styles = {
  sidebar: {
    width: "220px",
    height: "100vh",
    background: "#1e1e1e",
    padding: "20px",
    color: "white",
    position: "fixed",
    top: 0,
    left: 0,
  },
  title: {
    marginBottom: "20px",
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  link: {
    color: "#fff",
    textDecoration: "none",
    fontSize: "16px",
    padding: "8px",
    borderRadius: "4px",
  },
};
