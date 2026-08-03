import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  PenTool,
  Copy,
  Shield,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

/* ========================================= */
/* Navigation Items                          */
/* ========================================= */

const NAV_ITEMS = [
  {
    to: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    end: true,
  },
  {
    to: "/investigation",
    label: "Investigation",
    icon: Search,
    end: false,
  },
  {
    to: "/signature",
    label: "Signature Verify",
    icon: PenTool,
    end: false,
  },
  {
    to: "/copy-move",
    label: "Copy-Move",
    icon: Copy,
    end: false,
  },
];

function Sidebar({ collapsed, onToggle }) {

  return (

    <aside
      className={`fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-slate-800/60 glass-panel transition-all duration-300 ${
        collapsed ? "w-[72px]" : "w-64"
      }`}
      aria-label="Main navigation"
    >

      {/* ================================= */}
      {/* Logo / Brand                      */}
      {/* ================================= */}

      <div className="flex h-16 items-center gap-3 border-b border-slate-800/60 px-4">

        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg shadow-blue-500/20">

          <Shield className="h-5 w-5 text-white" aria-hidden="true" />

        </div>

        {!collapsed && (

          <div className="overflow-hidden">

            <p className="truncate text-sm font-bold tracking-wide text-white">
              AI-FORGE
            </p>

            <p className="truncate text-[10px] text-slate-400">
              Fraud Intelligence
            </p>

          </div>

        )}

      </div>


      {/* ================================= */}
      {/* Navigation Links                  */}
      {/* ================================= */}

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">

        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (

          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-blue-500/15 text-blue-400 shadow-sm shadow-blue-500/10"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-white"
              }`
            }
          >

            <Icon
              className="h-5 w-5 shrink-0"
              aria-hidden="true"
            />

            {!collapsed && (
              <span className="truncate">{label}</span>
            )}

          </NavLink>

        ))}

      </nav>


      {/* ================================= */}
      {/* Collapse Toggle                   */}
      {/* ================================= */}

      <div className="border-t border-slate-800/60 p-3">

        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 transition hover:bg-slate-800/50 hover:text-white"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >

          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}

        </button>

      </div>

    </aside>

  );

}

export default Sidebar;
