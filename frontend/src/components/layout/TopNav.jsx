import { Bell, LogOut, Menu, PanelLeft, User } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import GlobalSearch from "./GlobalSearch";
import BackendStatus from "../ui/BackendStatus";

function TopNav({ onMenuToggle, onSidebarToggle, title, subtitle, contextLabel }) {
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <header className="forge-topnav">
      <div className="forge-topnav-left">
        <button
          type="button"
          onClick={onMenuToggle}
          className="forge-icon-button lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={onSidebarToggle}
          className="forge-icon-button hidden lg:inline-flex"
          aria-label="Toggle sidebar"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
        <div className="min-w-0">
          <h1>{title || "AI-FORGE"}</h1>
          {(subtitle || contextLabel) && (
            <p>{contextLabel || subtitle}</p>
          )}
        </div>
      </div>

      <div className="forge-topnav-right">
        <GlobalSearch />
        <button type="button" className="forge-icon-button" aria-label="Notifications" title="Notifications">
          <Bell className="h-4 w-4" />
        </button>
        <div className="forge-topnav-service">
          <BackendStatus />
        </div>
        {isAuthenticated && (
          <div className="forge-user-chip">
            <User className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              {user?.email?.split("@")[0] || user?.username || "Investigator"}
            </span>
            <button type="button" onClick={logout} title="Sign out">
              <LogOut className="h-3.5 w-3.5" />
              <span className="sr-only">Sign out</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default TopNav;
