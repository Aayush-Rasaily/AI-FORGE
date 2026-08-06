import { useState } from "react";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";
import ParticleBackground from "../ui/ParticleBackground";

function AppLayout({ children, title, subtitle }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="relative min-h-screen overflow-x-hidden text-white">
      <ParticleBackground />

      {/* Desktop Sidebar */}
      <div className="hidden lg:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((prev) => !prev)}
        />
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed left-0 top-0 z-50 lg:hidden">
            <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
          </div>
        </>
      )}

      {/* Main Content */}
      <div
        className={`relative z-10 flex min-h-screen flex-col transition-all duration-300 ${
          sidebarCollapsed ? "lg:ml-[72px]" : "lg:ml-64"
        }`}
      >
        <TopNav
          onMenuToggle={() => setMobileOpen((prev) => !prev)}
          title={title}
          subtitle={subtitle}
        />

        <main className="flex-1 overflow-x-hidden p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-[1400px]">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
