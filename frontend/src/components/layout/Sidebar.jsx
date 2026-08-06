import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Search,
  PenTool,
  Copy,
  Shield,
  ChevronLeft,
  ChevronRight,
  Scale,
  FolderSearch,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/cases", label: "Cases", icon: FolderSearch, end: false },
  { to: "/investigation", label: "Investigation", icon: Search, end: false },
  { to: "/signature", label: "Signature", icon: PenTool, end: false },
  { to: "/copy-move", label: "Copy-Move", icon: Copy, end: false },
];

function Sidebar({ collapsed, onToggle }) {
  return (
    <aside
      className={`fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-[#1F2937]/80 bg-[#0B1120]/80 backdrop-blur-2xl transition-all duration-300 ${
        collapsed ? "w-[72px]" : "w-64"
      }`}
      aria-label="Main navigation"
    >
      {/* Brand */}
      <div className="flex h-16 items-center gap-3 border-b border-[#1F2937]/60 px-4">
        <motion.div
          whileHover={{ scale: 1.05 }}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg shadow-blue-500/30"
        >
          <Shield className="h-5 w-5 text-white" />
        </motion.div>
        {!collapsed && (
          <div className="overflow-hidden">
            <p className="truncate text-sm font-bold tracking-wide text-white">AI-FORGE</p>
            <p className="truncate text-[10px] text-slate-500">Fraud Intelligence</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-gradient-to-r from-blue-600/20 to-cyan-600/10 text-cyan-400 shadow-sm shadow-blue-500/10 border border-blue-500/20"
                  : "text-slate-400 hover:bg-white/5 hover:text-white border border-transparent"
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* AI Jury badge */}
      {!collapsed && (
        <div className="mx-3 mb-3 rounded-xl border border-violet-500/20 bg-violet-500/5 p-3">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-violet-400" />
            <span className="text-xs font-medium text-violet-300">AI Jury Active</span>
          </div>
          <p className="mt-1 text-[10px] text-slate-500">6 agents ready</p>
        </div>
      )}

      {/* Collapse */}
      <div className="border-t border-[#1F2937]/60 p-3">
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-400 transition hover:bg-white/5 hover:text-white"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <><ChevronLeft className="h-4 w-4" /><span>Collapse</span></>}
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
