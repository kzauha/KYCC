import { Link, useLocation } from "react-router-dom";

export default function Sidebar() {
  const location = useLocation();

  const links = [
    { to: "/", label: "Party List", icon: "bi-people" },
    // { to: "/new", label: "Create Party", icon: "bi-plus-circle" },
    { to: "/relationship", label: "Relationships", icon: "bi-diagram-3" },
    { to: "/network", label: "Network Graph", icon: "bi-share" },
    { to: "/credit", label: "Credit Score", icon: "bi-graph-up" },
    { to: "/upload", label: "Upload CSV", icon: "bi-upload" },
  ];

  return (
    <div className="bg-dark text-white vh-100 p-3 position-fixed" style={{ width: "240px" }}>
      <h4 className="text-center mb-4 fw-bold">KYCC</h4>

      <nav className="nav flex-column gap-1">
        {links.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`nav-link d-flex align-items-center gap-2 text-white rounded px-3 py-2 ${
              location.pathname === item.to ? "bg-primary" : ""
            }`}
          >
            <i className={`bi ${item.icon}`}></i>
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
