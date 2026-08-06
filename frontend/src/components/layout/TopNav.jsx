import { Bell, Menu } from "lucide-react";
import BackendStatus from "../ui/BackendStatus";

function TopNav({ onMenuToggle, title, subtitle }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[#1F2937] bg-[#0B1120]/80 backdrop-blur-xl px-4 md:px-6">

      {/* Left: Mobile Menu + Page Title */}
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuToggle}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-[#111827] hover:text-white lg:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div>
          <h1 className="text-lg font-semibold text-white md:text-xl">
            {title || "AI-FORGE"}
          </h1>
          {subtitle && (
            <p className="hidden text-xs text-slate-400 sm:block">{subtitle}</p>
          )}
        </div>
      </div>

      {/* Right: Backend Status + Notifications */}
      <div className="flex items-center gap-3">
        <BackendStatus />

        <button
          className="relative rounded-lg p-2 text-slate-400 transition hover:bg-[#111827] hover:text-white"
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
