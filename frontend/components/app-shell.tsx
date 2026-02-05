import type { ReactNode } from "react";
import { NavSidebar } from "./nav-sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen bg-background bg-mesh">
      <NavSidebar />
      <main className="flex-1 overflow-auto custom-scrollbar p-8">
        <div className="max-w-[1440px] mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
