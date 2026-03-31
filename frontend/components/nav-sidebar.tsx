"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Columns3,
  Play,
  Copy,
  MapPin,
  Sun,
  Moon,
  Zap,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/map", label: "Map", icon: MapPin },
  { href: "/kanban", label: "Kanban", icon: Columns3 },
  { href: "/duplicates", label: "Duplicates", icon: Copy },
  { href: "/pipeline", label: "Pipeline", icon: Play },
];

export function NavSidebar() {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  return (
    <aside className="w-64 flex flex-col glass-strong border-r-0 border-l-0 border-t-0 border-b-0 rounded-none">
      {/* Logo area */}
      <div className="p-6 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-accent-gradient flex items-center justify-center shadow-md">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight">NBL</h1>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">
              Lead Generation
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-1">
        <p className="px-3 pt-2 pb-1.5 text-[10px] uppercase tracking-widest font-semibold text-muted-foreground">
          Navigation
        </p>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-accent-gradient text-white shadow-md"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/10"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
              {isActive && (
                <div className="ml-auto h-1.5 w-1.5 rounded-full bg-white/70" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Theme toggle */}
      <div className="p-3 border-t border-border/50">
        <button
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          className="flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-accent/10 transition-all duration-200"
        >
          {mounted ? (
            resolvedTheme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )
          ) : (
            <div className="h-4 w-4" />
          )}
          {mounted ? (resolvedTheme === "dark" ? "Light Mode" : "Dark Mode") : "Toggle Theme"}
        </button>
      </div>
    </aside>
  );
}
