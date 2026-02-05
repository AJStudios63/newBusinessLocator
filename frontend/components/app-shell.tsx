import type { ReactNode } from "react";
import { NavSidebar } from "./nav-sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen">
      <NavSidebar />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
