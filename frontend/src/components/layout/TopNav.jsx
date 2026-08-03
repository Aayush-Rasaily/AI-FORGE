import { useState, useEffect } from "react";
import { Bell, Circle, Menu } from "lucide-react";
import { checkBackendHealth } from "../../services/api";

function TopNav({ sidebarCollapsed, onMenuToggle, title, subtitle }) {

  const [backendOnline, setBackendOnline] = useState(null);

  /* ========================================= */
  /* Backend Health Check                      */
  /* ========================================= */

  useEffect(() => {

    let mounted = true;

    async function checkHealth() {

      try {

        await checkBackendHealth();

        if (mounted) {
          setBackendOnline(true);
        }

      } catch {

        if (mounted) {
          setBackendOnline(false);
        }

      }

    }

    checkHealth();

    const interval = setInterval(checkHealth, 30000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };

  }, []);


  return (

    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-800/60 glass-panel px-4 md:px-6">

      {/* ================================= */}
      {/* Left: Mobile Menu + Page Title    */}
      {/* ================================= */}

      <div className="flex items-center gap-4">

        <button
          onClick={onMenuToggle}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800/50 hover:text-white lg:hidden"
          aria-label="Toggle navigation menu"
        >

          <Menu className="h-5 w-5" />

        </button>


        <div>

          <h1 className="text-lg font-semibold text-white md:text-xl">
            {title || "AI-FORGE"}
          </h1>

          {subtitle && (
            <p className="hidden text-xs text-slate-400 sm:block">
              {subtitle}
            </p>
          )}

        </div>

      </div>


      {/* ================================= */}
      {/* Right: Status + Notifications     */}
      {/* ================================= */}

      <div className="flex items-center gap-4">

        {/* Backend Status Badge */}

        <div
          className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${
            backendOnline === null
              ? "bg-slate-800/50 text-slate-400"
              : backendOnline
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-red-500/10 text-red-400"
          }`}
        >

          <Circle
            className={`h-2 w-2 fill-current ${
              backendOnline === null
                ? "text-slate-400"
                : backendOnline
                  ? "animate-pulse-glow text-emerald-400"
                  : "text-red-400"
            }`}
          />

          <span className="hidden sm:inline">
            {backendOnline === null
              ? "Checking..."
              : backendOnline
                ? "System Online"
                : "Backend Offline"}
          </span>

        </div>


        {/* Notification Bell */}

        <button
          className="relative rounded-lg p-2 text-slate-400 transition hover:bg-slate-800/50 hover:text-white"
          aria-label="Notifications"
        >

          <Bell className="h-5 w-5" />

          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-blue-500" />

        </button>

      </div>

    </header>

  );

}

export default TopNav;
