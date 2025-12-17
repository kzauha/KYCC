import { Link, useLocation } from "react-router-dom";

export default function Sidebar() {
  const location = useLocation();

  const links = [
    { to: "/", label: "Party List", icon: "bi-people" },
    { to: "/dashboard", label: "Simulation", icon: "bi-cpu" },
    { to: "/ml-dashboard", label: "ML Analytics", icon: "bi-bar-chart" },

  ];

  return (
    <div className="bg-dark text-white vh-100 p-3 position-fixed" style={{ width: "240px" }}>
      <h4 className="text-center mb-4 fw-bold">KYCC</h4>

      <nav className="nav flex-column gap-1">
        {links.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`nav-link d-flex align-items-center gap-2 text-white rounded px-3 py-2 ${location.pathname === item.to ? "bg-primary" : ""
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
