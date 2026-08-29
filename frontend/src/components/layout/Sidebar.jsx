import { NavLink, useLocation } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  FileSearch,
  FileText,
  Gavel,
  FolderOpen,
  History,
  HelpCircle,
  Image,
  LayoutDashboard,
  PenTool,
  Plus,
  Settings,
  Shield,
  Video,
} from "lucide-react";
import BackendStatus from "../ui/BackendStatus";

const NAV_GROUPS = [
  {
    id: "workspace",
    label: "Workspace",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
      { to: "/investigation?new=1", label: "New investigation", icon: Plus, newInvestigation: true },
      { to: "/cases", label: "Cases", icon: FolderOpen },
      { to: "/investigation", label: "Evidence", icon: ClipboardList },
      { to: "/investigation#expert-jury", label: "AI Jury", icon: Gavel, jury: true },
      { to: "/reports", label: "Reports", icon: FileSearch },
      { to: "/history", label: "History", icon: History },
    ],
  },
  {
    id: "analysis",
    label: "Analysis",
    items: [
      { to: "/investigation?mode=document", label: "Document Analysis", icon: FileText, mode: "document" },
      { to: "/investigation?mode=image", label: "Image Analysis", icon: Image, mode: "image" },
      { to: "/investigation?mode=video", label: "Video Analysis", icon: Video, mode: "video" },
      { to: "/signature-analysis", label: "Signature Analysis", icon: PenTool, signature: true },
    ],
  },
  {
    id: "system",
    label: "System",
    items: [
      { to: "/settings", label: "Settings", icon: Settings },
      { to: "/help", label: "Help", icon: HelpCircle },
    ],
  },
];

function Sidebar({ collapsed, onToggle }) {
  const location = useLocation();
  const currentMode = new URLSearchParams(location.search).get("mode");
  const isNewInvestigation = new URLSearchParams(location.search).get("new") === "1";
  const isJuryView = location.hash === "#expert-jury";

  return (
    <aside
      className={`forge-sidebar ${collapsed ? "forge-sidebar-collapsed" : ""}`}
      aria-label="Main navigation"
    >
      <div className="forge-sidebar-brand">
        <div className="forge-brand-mark" aria-hidden="true">
          <Shield className="h-4 w-4" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="forge-brand-name">AI-FORGE</p>
            <p className="forge-brand-sub">Forensic Intelligence</p>
          </div>
        )}
      </div>

      <nav className="forge-sidebar-nav" role="navigation">
        {NAV_GROUPS.map((group) => (
          <div key={group.id} className="forge-nav-group">
            {!collapsed && <p className="forge-label">{group.label}</p>}
            {group.items.map(({ to, label, icon: Icon, end, mode, newInvestigation, jury, signature }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                title={label}
                className={({ isActive }) => {
                  const modeActive =
                    Boolean(mode) &&
                    location.pathname === "/investigation" &&
                    currentMode === mode;
                  const newActive = newInvestigation && isNewInvestigation;
                  const juryActive = jury && location.pathname === "/investigation" && isJuryView;
                  const signatureActive = signature && ["/signature", "/signature-analysis"].includes(location.pathname);
                  const pathActive =
                    !mode &&
                    !newInvestigation &&
                    !jury &&
                    !signature &&
                    isActive &&
                    !(group.id === "workspace" && to === "/investigation" && (currentMode || isNewInvestigation || isJuryView));
                  return `forge-nav-item ${modeActive || pathActive || newActive || juryActive || signatureActive ? "forge-nav-item-active" : ""}`;
                }}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {!collapsed && <span className="truncate">{label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="forge-sidebar-footer">
        {!collapsed && (
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="forge-label">Service</p>
            <BackendStatus />
          </div>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="forge-sidebar-toggle"
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
