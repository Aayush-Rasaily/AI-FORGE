import { useState } from "react";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";

function AppLayout({ children, title, subtitle }) {

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [mobileOpen, setMobileOpen] = useState(false);


  return (

    <div className="app-gradient-bg min-h-screen text-white">

      {/* ================================= */}
      {/* Desktop Sidebar                   */}
      {/* ================================= */}

      <div className="hidden lg:block">

        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() =>
            setSidebarCollapsed((prev) => !prev)
          }
        />

      </div>


      {/* ================================= */}
      {/* Mobile Sidebar Overlay            */}
      {/* ================================= */}

      {mobileOpen && (

        <>

          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />

          <div className="fixed left-0 top-0 z-50 lg:hidden">

            <Sidebar
              collapsed={false}
              onToggle={() => setMobileOpen(false)}
            />

          </div>

        </>

      )}


      {/* ================================= */}
      {/* Main Content Area                 */}
      {/* ================================= */}

      <div
        className={`flex min-h-screen flex-col transition-all duration-300 ${
          sidebarCollapsed
            ? "lg:ml-[72px]"
            : "lg:ml-64"
        }`}
      >

        <TopNav
          sidebarCollapsed={sidebarCollapsed}
          onMenuToggle={() => setMobileOpen((prev) => !prev)}
          title={title}
          subtitle={subtitle}
        />


        <main className="flex-1 p-4 md:p-6 lg:p-8">

          <div className="mx-auto max-w-7xl animate-fade-in-up">

            {children}

          </div>

        </main>

      </div>

    </div>

  );

}

export default AppLayout;
