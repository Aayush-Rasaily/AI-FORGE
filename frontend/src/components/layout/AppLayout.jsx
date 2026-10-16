import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";
import FooterSuperchat from "../registry/footer-superchat";

function readCollapsed() {
  try {
    return localStorage.getItem("forge-sidebar-collapsed") === "true";
  } catch {
    return false;
  }
}

function AppLayout({ children, title, subtitle, contextLabel }) {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem("forge-sidebar-collapsed", String(collapsed));
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  useEffect(() => {
    function onResize() {
      if (window.innerWidth >= 1024) setMobileOpen(false);
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  function handleNavigationToggle() {
    if (window.innerWidth >= 1024) {
      setCollapsed((value) => !value);
      return;
    }
    setMobileOpen((value) => !value);
  }

  return (
    <div className="forge-shell">
      <div className="hidden lg:block">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      </div>

      {mobileOpen && (
        <>
          <button
            type="button"
            className="forge-nav-backdrop lg:hidden"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          />
          <div className="forge-mobile-drawer lg:hidden">
            <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
          </div>
        </>
      )}

      <div
        className={`forge-main flex min-w-0 flex-col ${
          collapsed ? "forge-content-collapsed" : "forge-content-normal"
        }`}
      >
        <TopNav
          onSidebarToggle={handleNavigationToggle}
          title={title}
          subtitle={subtitle}
          contextLabel={contextLabel}
        />
        <main className="forge-page">
          <div className="forge-page-inner">{children}</div>
        </main>
        <FooterSuperchat />
      </div>
    </div>
  );
}

export default AppLayout;
