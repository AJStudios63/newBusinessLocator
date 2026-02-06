# Document 4: Next.js and the App Router

This is Part 4 of a 10-part training series. You have learned JavaScript (doc 01), TypeScript (doc 02), and React (doc 03). Now we add the framework layer that turns React into a full web application.

---

## 1. What is Next.js?

React by itself is a UI library. It knows how to render components and manage state, but it does not know how to:

- Route between pages (which URL shows which component?)
- Render HTML on the server (for fast initial load and SEO)
- Bundle and optimize your code for production
- Load fonts, images, and assets efficiently
- Handle API proxying or server-side data fetching

Next.js is a **framework built on top of React** that provides all of this. The relationship is:

| Analogy | UI Library | Full Framework |
|---------|-----------|----------------|
| C# | A Razor component library | ASP.NET MVC / Razor Pages |
| Python | Jinja2 templates | Django or Flask |
| JavaScript | React | **Next.js** |

React alone is like having a powerful templating engine but no web server, no router, and no build system. Next.js is the full package -- it gives you a development server, file-based routing, server-side rendering, production builds, and much more.

Next.js was created by Vercel (a cloud hosting company) and is the most widely used React framework in production. This project uses **Next.js 14** with the **App Router**, which you can see in `package.json`:

```json
// frontend/package.json
{
  "dependencies": {
    "next": "14.2.35",
    "react": "^18",
    "react-dom": "^18"
  }
}
```

---

## 2. App Router vs Pages Router

Next.js has two routing systems. The older one is the "Pages Router" (uses a `pages/` directory). The newer one is the **App Router** (uses an `app/` directory). This project uses the App Router.

### The Core Idea: Folder Names Become URLs

In the App Router, the file system IS the router. Every folder inside `app/` becomes a URL segment, and a `page.tsx` file inside that folder becomes the page rendered at that URL.

Here is the actual folder structure of this project:

```
frontend/app/
  page.tsx            -->  /           (dashboard homepage)
  layout.tsx          -->  wraps every page
  globals.css         -->  global styles
  leads/
    page.tsx          -->  /leads      (lead table with filters)
  kanban/
    page.tsx          -->  /kanban     (drag-drop board)
  duplicates/
    page.tsx          -->  /duplicates (duplicate detection)
  pipeline/
    page.tsx          -->  /pipeline   (ETL run history)
  batch/
    [id]/
      page.tsx        -->  /batch/123  (dynamic route -- any ID)
```

The rules are simple:
- A folder named `leads` maps to the URL path `/leads`
- A folder named `kanban` maps to `/kanban`
- The `page.tsx` file inside each folder is the component that renders for that URL
- A folder name in `[brackets]` like `[id]` is a **dynamic segment** -- it matches any value

### C# Comparison

This is similar to ASP.NET Razor Pages where file location determines the URL:

```
// C# Razor Pages (similar concept)
Pages/
  Index.cshtml        -->  /
  Leads/
    Index.cshtml      -->  /Leads
  Batch/
    Details.cshtml    -->  /Batch/123 (with route parameter)
```

### Python Comparison

In Django, you manually define URL patterns in `urls.py`. In Flask, you use `@app.route()` decorators. Next.js eliminates that manual mapping -- the file system IS the configuration.

```python
# Django: manual URL configuration
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('leads/', views.leads, name='leads'),
    path('batch/<int:id>/', views.batch_detail, name='batch-detail'),
]

# Next.js: no configuration needed -- folder structure IS the routing
```

### Dynamic Routes in Detail

The `[id]` folder name creates a dynamic route parameter. When a user visits `/batch/42`, Next.js passes `{ id: "42" }` as a prop to the page component:

```tsx
// frontend/app/batch/[id]/page.tsx
interface BatchPageProps {
  params: Promise<{ id: string }>;  // Next.js passes the URL parameter
}

export default function BatchPage({ params }: BatchPageProps) {
  const { id } = use(params);       // Extract the ID (e.g., "42")
  // ...use `id` to fetch data for this specific batch
}
```

In C# terms, this is like `[Route("batch/{id}")]` on a controller action. In Python Django, it is like `path('batch/<int:id>/', views.batch_detail)`. The key difference is that Next.js infers the parameter from the folder name rather than from an explicit route definition.

---

## 3. Layout Files

Every Next.js app has a **root layout** that wraps every page. This is the outermost shell of your HTML document. Here is the real one from this project:

```tsx
// frontend/app/layout.tsx
import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Providers } from "@/components/providers";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "New Business Locator",
  description: "POS lead generation dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

Let's break down every part.

### `export const metadata: Metadata`

```tsx
export const metadata: Metadata = {
  title: "New Business Locator",
  description: "POS lead generation dashboard",
};
```

This sets the HTML `<title>` and `<meta name="description">` tags. Next.js reads this exported object and injects it into the `<head>` of the rendered HTML page. You never manually write `<head>` or `<title>` tags -- you export this object and Next.js handles it.

This is like:
- **C#**: `ViewBag.Title = "New Business Locator"` in ASP.NET MVC, or `@page` directives in Razor Pages
- **Python Django**: `{% block title %}New Business Locator{% endblock %}` in a template

### `localFont()` -- Font Loading

```tsx
const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
```

Next.js has a built-in font optimization system. When you use `localFont()`, it:
1. Loads the font file at build time
2. Creates a CSS custom property (here `--font-geist-sans`)
3. Optimizes the font so there is no flash of unstyled text (FOUT)
4. Self-hosts the font rather than loading it from an external CDN

The `variable: "--font-geist-sans"` creates a CSS variable that Tailwind CSS uses to apply this font. The `weight: "100 900"` says this is a variable font supporting all weights from thin (100) to black (900).

### `RootLayout` -- The Wrapper for Every Page

```tsx
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

This function is called for **every page** in the application. `{children}` is where the actual page content gets rendered. When a user visits `/leads`, Next.js renders:

```
RootLayout
  └── <html>
       └── <body>
            └── <Providers>
                 └── LeadsPage (the children)
```

When they visit `/kanban`:

```
RootLayout
  └── <html>
       └── <body>
            └── <Providers>
                 └── KanbanPage (the children)
```

The layout stays the same; only `{children}` changes.

This is exactly like:
- **C#**: `_Layout.cshtml` in ASP.NET MVC, where `@RenderBody()` is the equivalent of `{children}`
- **Python Django**: `base.html` template, where `{% block content %}{% endblock %}` is the equivalent of `{children}`

### Special Attributes

**`className="dark"`** -- Sets the default theme to dark mode. The `next-themes` library reads this class to determine the current theme.

**`suppressHydrationWarning`** -- Tells React not to warn when the server-rendered HTML has `className="dark"` but the client might change it to `"light"` based on user preference. This is necessary because the server does not know the user's theme preference (more on hydration in section 7).

**`Readonly<{ children: React.ReactNode }>`** -- TypeScript type that says "this component receives children, and that props object should not be mutated." `React.ReactNode` means children can be any renderable React content (elements, strings, numbers, null, etc.).

---

## 4. Server Components vs Client Components

This is the **most important concept in Next.js**. If you understand this, everything else falls into place. If you do not, nothing will make sense.

### Two Kinds of Components

In Next.js App Router, every component is one of two types:

| | Server Component | Client Component |
|---|---|---|
| **Where it runs** | On the server only | In the browser (after initial server render) |
| **Declared how** | Default -- no special syntax | Must add `"use client"` at top of file |
| **Can use hooks?** | No (no useState, useEffect, useQuery) | Yes |
| **Can use event handlers?** | No (no onClick, onChange) | Yes |
| **Can access browser APIs?** | No (no window, document, localStorage) | Yes |
| **Can access server resources?** | Yes (database, file system, env vars) | No (not directly) |

### Server Components (the Default)

When you create a component in the App Router without any special directive, it is a **Server Component**. It runs on the server, generates HTML, and sends that HTML to the browser. The browser never sees the JavaScript code for that component.

The `layout.tsx` in this project is a Server Component:

```tsx
// frontend/app/layout.tsx -- NO "use client" directive = Server Component
import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {  // <-- Only works in Server Components
  title: "New Business Locator",
  description: "POS lead generation dashboard",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

Notice: no `"use client"` at the top, no `useState`, no `useEffect`, no event handlers. It just receives props and returns JSX. The `metadata` export only works in Server Components.

**C# analogy**: Server Components are like Razor Pages or MVC Views. They run on the server, produce HTML, and send it to the client. The client never executes the C# code.

**Python analogy**: Server Components are like Jinja2 or Django templates rendered on the server. The template logic runs server-side; the browser only gets the resulting HTML.

### Client Components (Opt-in with "use client")

When a component needs interactivity -- hooks, event handlers, browser APIs -- you add `"use client"` as the very first line:

```tsx
// frontend/app/page.tsx -- "use client" = Client Component
"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
// ...

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({    // <-- Hook: needs "use client"
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const handleRunPipeline = async () => {           // <-- Event handler: needs "use client"
    try {
      await triggerPipelineRun();
      toast.success("Pipeline started");            // <-- Browser-side toast
    } catch {
      toast.error("Failed to start pipeline");
    }
  };

  return (
    <AppShell>
      <Button onClick={handleRunPipeline}>          {/* <-- onClick: needs "use client" */}
        Run Pipeline
      </Button>
    </AppShell>
  );
}
```

Every single `page.tsx` in this project has `"use client"` at the top because they all use React Query hooks (`useQuery`) and event handlers (`onClick`). Let's verify:

```tsx
// frontend/app/page.tsx         -- "use client"  (uses useQuery, onClick)
// frontend/app/leads/page.tsx   -- "use client"  (uses useQuery, useState, useSearchParams)
// frontend/app/kanban/page.tsx  -- "use client"  (uses useQuery, useState)
// frontend/app/duplicates/page.tsx -- "use client" (uses useQuery, useMutation)
// frontend/app/pipeline/page.tsx   -- "use client" (uses useQuery, useMutation)
// frontend/app/batch/[id]/page.tsx -- "use client" (uses useQuery, useRouter)
```

**C# analogy**: Client Components are like Blazor WebAssembly components. They run in the browser, can respond to user events, and maintain local state. The trade-off is the browser must download and execute the JavaScript.

**Python analogy**: Client Components are like the JavaScript you would write in a Django template's `<script>` tag, but structured as full React components rather than loose scripts.

### The Rule

The decision is straightforward:

1. Does the component need hooks (`useState`, `useEffect`, `useQuery`)? Add `"use client"`.
2. Does the component need event handlers (`onClick`, `onChange`)? Add `"use client"`.
3. Does the component need browser APIs (`window`, `document`, `localStorage`)? Add `"use client"`.
4. Otherwise, leave it as a Server Component (do nothing).

### The Boundary

A key architectural concept: Server Components can import and render Client Components, but Client Components cannot import Server Components. The boundary flows in one direction.

In this project, the root layout is a Server Component. It imports and renders `<Providers>`, which is a Client Component. Everything inside `<Providers>` (all the pages) runs in the browser:

```
layout.tsx (Server Component)
  └── <Providers> (Client Component -- "use client")
       └── <DashboardPage> (Client Component)
            └── <AppShell> (rendered in client context)
                 └── <NavSidebar> (rendered in client context)
```

Once you cross the `"use client"` boundary, everything below it in the tree is also client-side. You do not need `"use client"` on every child component -- only on the one that establishes the boundary.

### In This Project

Looking at the `AppShell` component, it does NOT have `"use client"`:

```tsx
// frontend/components/app-shell.tsx -- no "use client" directive
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
```

But `NavSidebar` does have `"use client"` because it uses `usePathname()` and `useTheme()`:

```tsx
// frontend/components/nav-sidebar.tsx
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
// ...
```

Because `AppShell` is always imported by Client Components (the page files), it runs in the client context regardless. But `NavSidebar` explicitly declares `"use client"` because it directly uses hooks. This is a best practice -- be explicit about which components need client-side features.

---

## 5. The Providers Pattern

Most React applications need several "providers" -- components that make shared state or services available to the entire component tree. In Next.js, these providers must be Client Components because they use React context (a client-side feature). But the root layout is a Server Component. The solution is the **Providers pattern**.

Here is the real `providers.tsx` from this project:

```tsx
// frontend/components/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster position="top-right" richColors />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
```

Let's dissect every part.

### Why `"use client"`?

Providers need `"use client"` because:
- `QueryClientProvider` uses React context internally (context = client-side feature)
- `ThemeProvider` uses React context to share theme state
- `useState` is used to create the QueryClient
- `Toaster` renders toast notifications that respond to browser events

### The Server/Client Boundary

The layout (Server Component) imports and renders Providers (Client Component). This creates the boundary:

```tsx
// layout.tsx (Server Component)
export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <Providers>{children}</Providers>  {/* Boundary: server -> client */}
      </body>
    </html>
  );
}
```

Everything rendered inside `<Providers>` is now in client context.

### `useState(() => new QueryClient(...))`

```tsx
const [queryClient] = useState(
  () =>
    new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 5 * 1000,
          refetchOnWindowFocus: false,
        },
      },
    })
);
```

This uses **lazy initialization** -- the `() =>` arrow function inside `useState()` means "run this function once to create the initial value, then never again." Without it, a new `QueryClient` would be created on every render (wasteful and would reset all cached data).

The configuration says:
- `staleTime: 5 * 1000` -- cached data is considered "fresh" for 5 seconds before React Query refetches
- `refetchOnWindowFocus: false` -- do not refetch data every time the user tabs back to the page

**C# analogy**: This is like registering a singleton service in `Startup.cs`. You create one instance of QueryClient and share it with the entire application through dependency injection (React context is essentially DI for React).

**Python analogy**: This is like creating a single database connection pool in Flask's `create_app()` and making it available to all request handlers.

### `ThemeProvider`

```tsx
<ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
```

From the `next-themes` library. It manages dark/light mode by:
- `attribute="class"` -- adds `class="dark"` or `class="light"` to the `<html>` element (Tailwind CSS reads this)
- `defaultTheme="dark"` -- starts in dark mode
- `enableSystem={false}` -- ignores the OS-level dark mode preference

### `QueryClientProvider`

```tsx
<QueryClientProvider client={queryClient}>
  {children}
  <Toaster position="top-right" richColors />
</QueryClientProvider>
```

Makes the React Query client available to all child components. Any component that calls `useQuery()` will use this shared client. Without this provider wrapper, `useQuery()` would throw an error saying "no QueryClient found."

### `Toaster`

```tsx
<Toaster position="top-right" richColors />
```

From the Sonner library. This renders a container for toast notifications in the top-right corner. When any component calls `toast.success("Pipeline started")`, the notification appears in this container. Placing it at the root level means toasts work from any page.

### The Nesting Order Matters

Providers are nested, and the order matters. The outermost provider's context is available to everything inside it:

```
ThemeProvider (provides theme to everything)
  └── QueryClientProvider (provides data fetching to everything)
       └── {children} (the actual pages)
       └── Toaster (can access both theme and query context)
```

---

## 6. Navigation

Next.js provides three navigation tools. All three are used in this project.

### Link Component (Declarative Navigation)

The `Link` component from `next/link` is the primary way to navigate between pages:

```tsx
// frontend/app/page.tsx (dashboard page)
import Link from "next/link";

// Simple text link
<Link href="/leads">View Leads</Link>

// Button wrapped in a link
<Link href="/duplicates">
  <Button variant="outline" size="sm">
    Review Now
    <ArrowRight className="ml-2 h-3.5 w-3.5" />
  </Button>
</Link>
```

`Link` renders an HTML `<a>` tag but intercepts the click to do **client-side navigation**. This means:
- No full page reload (the browser does not re-download HTML, CSS, JavaScript)
- React preserves state (the layout, sidebar, and providers stay mounted)
- Only the new page component is rendered and swapped in
- The URL in the address bar updates normally

Without `Link`, clicking an `<a href="/leads">` would trigger a full page reload -- the browser would re-request the HTML, re-download all scripts, and re-mount the entire React tree. With `Link`, only the page content changes.

**C# analogy**: Like Blazor's `<NavLink href="/leads">` which navigates within the SPA without a full page reload.

**Python analogy**: Django and Flask always do full page reloads. `Link` gives you the SPA experience where only the content area updates.

### Navigation in the Sidebar

The sidebar uses `Link` to create the nav menu, mapping over an array of route definitions:

```tsx
// frontend/components/nav-sidebar.tsx
import Link from "next/link";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/kanban", label: "Kanban", icon: Columns3 },
  { href: "/duplicates", label: "Duplicates", icon: Copy },
  { href: "/pipeline", label: "Pipeline", icon: Play },
];

// Inside the component:
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
    </Link>
  );
})}
```

This generates five navigation links. The `isActive` check compares the current URL path to each item's `href` to apply different styling to the active page.

### Programmatic Navigation (useRouter)

Sometimes you need to navigate in response to an event -- a button click, a form submission, or data loading. Use the `useRouter` hook:

```tsx
// frontend/components/charts.tsx
import { useRouter } from "next/navigation";

const router = useRouter();

// When user clicks a chart segment, navigate to leads filtered by county
router.push(`/leads?county=${encodeURIComponent(entry.name)}`);
```

Another example from the batch page -- navigate after deleting leads:

```tsx
// frontend/app/batch/[id]/page.tsx
import { useRouter } from "next/navigation";

const router = useRouter();

// After successful bulk delete, go back to the leads page
const deleteMutation = useMutation({
  mutationFn: () => bulkDeleteLeads(selectedIds),
  onSuccess: (result) => {
    toast.success(`Deleted ${result.deleted.length} leads`);
    router.push("/leads");
  },
});
```

And `router.replace()` for updating the URL without adding a history entry (the back button skips it):

```tsx
// frontend/app/leads/page.tsx
const router = useRouter();

// Update URL to reflect current filters, but don't add history entries
// (user shouldn't have to click Back 20 times to undo filter changes)
useEffect(() => {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  // ...

  const queryString = params.toString();
  const newUrl = queryString ? `/leads?${queryString}` : "/leads";

  if (window.location.pathname + window.location.search !== newUrl) {
    router.replace(newUrl, { scroll: false });
  }
}, [filters, router]);
```

**`router.push()`** = navigate and add to history (user can click Back).
**`router.replace()`** = navigate but replace current history entry (Back button goes to the previous page, not the previous filter state).

**C# analogy**: `router.push()` is like `NavigationManager.NavigateTo("/leads")` in Blazor.

**Python analogy**: `router.push()` is like `redirect("/leads")` in Flask or Django, except it happens client-side without a server round-trip.

### Detecting the Current Route (usePathname)

The `usePathname` hook returns the current URL path. The sidebar uses it to highlight the active nav item:

```tsx
// frontend/components/nav-sidebar.tsx
import { usePathname } from "next/navigation";

const pathname = usePathname();  // e.g., "/leads" or "/kanban"

const isActive = pathname === item.href;
// isActive is true for the nav item matching the current page
```

### Reading URL Search Parameters (useSearchParams)

The leads page reads filter values from the URL query string:

```tsx
// frontend/app/leads/page.tsx
import { useSearchParams } from "next/navigation";

const searchParams = useSearchParams();

// URL: /leads?stage=New&county=Davidson
const stage = searchParams.get("stage");    // "New"
const county = searchParams.get("county");  // "Davidson"
```

This allows the page to initialize its filter state from the URL, which means users can bookmark or share filtered views.

---

## 7. Hydration

This concept confuses many developers new to server-rendered React. Understanding it will save you hours of debugging.

### The Process

When a user visits a Next.js page, here is what happens:

1. **Server renders HTML**: Next.js runs your React components on the server and generates plain HTML
2. **Browser receives HTML**: The browser displays this HTML immediately (fast initial load)
3. **Browser downloads JavaScript**: The React runtime and your component code download in the background
4. **Hydration**: React "wakes up" the static HTML by attaching event listeners, initializing state, and connecting the component tree to the DOM

During step 4, React compares the HTML the server rendered with what the client would render. If they do not match, React throws a **hydration mismatch** error.

### Why Mismatches Happen

The server and client can produce different HTML when:
- The server does not have access to browser state (localStorage, cookies, window size)
- The server does not know user preferences (dark mode, language, timezone)
- Random values differ between server and client

### The Theme Problem (Real Example)

The most common hydration issue in this project involves the theme toggle. The server does not know if the user prefers dark or light mode. If the server renders a "Sun" icon (switch to light mode) but the client determines the user is actually in light mode and renders a "Moon" icon (switch to dark mode), React sees a mismatch and throws an error.

### The Hydration Guard Pattern

The sidebar solves this with a `mounted` state variable:

```tsx
// frontend/components/nav-sidebar.tsx
export function NavSidebar() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);
  //         ^^^^^^^^^^^^^^^^^^^^^^^^^^
  // useEffect runs ONLY on the client, AFTER hydration
  // So mounted is false during server render and first client render
  // Then becomes true after hydration completes

  return (
    // ...
    <button onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>
      {mounted ? (
        // After hydration: show the correct icon based on actual theme
        resolvedTheme === "dark" ? (
          <Sun className="h-4 w-4" />
        ) : (
          <Moon className="h-4 w-4" />
        )
      ) : (
        // Before hydration: show a same-sized placeholder
        // This matches on both server and client = no mismatch
        <div className="h-4 w-4" />
      )}
      {mounted ? (resolvedTheme === "dark" ? "Light Mode" : "Dark Mode") : "Toggle Theme"}
    </button>
  );
}
```

Here is the timeline:

1. **Server render**: `mounted` is `false`, renders `<div className="h-4 w-4" />` placeholder
2. **Client first render (hydration)**: `mounted` is still `false`, renders the same placeholder -- **matches server HTML, no error**
3. **After hydration**: `useEffect` fires, sets `mounted` to `true`, component re-renders with the correct Sun/Moon icon

The placeholder `<div className="h-4 w-4" />` has the same dimensions as the icon (4x4 = 16px), so the layout does not shift when the real icon replaces it.

**C# analogy**: In Blazor Server, the page is server-rendered first, then SignalR connects and "hydrates" the interactivity. If initial render does not match, you get similar issues.

**Python analogy**: There is no direct equivalent because Django/Flask templates render entirely on the server. Hydration is a React-specific concept that arises from rendering the same component on both server and client.

### `suppressHydrationWarning` in the Layout

```tsx
<html lang="en" className="dark" suppressHydrationWarning>
```

The `suppressHydrationWarning` attribute on `<html>` tells React: "I know the server and client might render different `className` values on this element (because the theme might change), and that is intentional -- do not warn me about it."

This is a targeted escape hatch, not a global silencer. It only affects the specific element it is applied to.

---

## 8. Path Aliases

Throughout this project, you will see imports using `@/`:

```tsx
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { getStats } from "@/lib/api";
import type { Lead } from "@/lib/types";
```

The `@/` prefix is a **path alias** configured in `tsconfig.json`:

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

This tells TypeScript (and Next.js) that `@/` maps to the project root directory (`frontend/`). So:

| Import | Resolves To |
|--------|-------------|
| `@/components/ui/button` | `frontend/components/ui/button` |
| `@/lib/api` | `frontend/lib/api` |
| `@/lib/types` | `frontend/lib/types` |

Without this alias, you would write relative paths like `../../components/ui/button`, which are error-prone and change when you move files.

**C# analogy**: This is like `using` aliases at the top of a C# file, or namespace aliases. The import path is clean and absolute rather than relative.

**Python analogy**: This is like having a package structure where you can do `from lib.api import get_stats` regardless of which file you are in, rather than `from ...lib.api import get_stats` with relative imports.

---

## 9. Metadata API

Next.js provides a type-safe way to set HTML `<head>` content through the Metadata API:

```tsx
// frontend/app/layout.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "New Business Locator",
  description: "POS lead generation dashboard",
};
```

This generates:

```html
<head>
  <title>New Business Locator</title>
  <meta name="description" content="POS lead generation dashboard" />
</head>
```

Key rules:
- **Only works in Server Components** (cannot use in files with `"use client"`)
- Must be a named export called `metadata`
- The `Metadata` type provides autocomplete for all valid fields (title, description, openGraph, twitter, robots, etc.)
- Each page can export its own `metadata` to override or extend the layout's metadata

The reason it only works in Server Components: metadata needs to be available before the page is sent to the browser so it can be included in the initial HTML `<head>`. Client Components run after the HTML is already sent.

**C# analogy**: Like `ViewBag.Title` in ASP.NET MVC, or `<meta>` tag helpers in Razor Pages.

**Python Django analogy**: Like `{% block title %}` in a template that extends `base.html`.

---

## 10. Font Loading

```tsx
// frontend/app/layout.tsx
import localFont from "next/font/local";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});
```

Next.js handles font loading as a first-class feature:

1. **No Flash of Unstyled Text (FOUT)**: Next.js preloads the font during the build, so it is available before the page renders. Without this, text would briefly appear in a fallback font before switching to the custom font.

2. **Self-hosted**: The font files are bundled with your application. No external requests to Google Fonts or other CDNs, which improves privacy and eliminates a network dependency.

3. **CSS Variables**: The `variable` option creates a CSS custom property. `--font-geist-sans` can be referenced in CSS and Tailwind configuration.

4. **Applied via className**: The font variables are added to the `<body>`:

```tsx
<body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
```

This adds the CSS variables to the body element, making them available to all child elements. The Tailwind class `font-sans` is configured to use `--font-geist-sans`.

---

## 11. API Proxying with Rewrites

The Next.js config file sets up a proxy to the Python backend:

```js
// frontend/next.config.mjs
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
```

This means when the frontend code makes a request to `/api/leads`, Next.js intercepts it and forwards it to `http://localhost:8000/api/leads` (the Python FastAPI server). The browser never sees the `localhost:8000` URL -- it thinks the API is served from the same origin as the frontend.

This solves two problems:
1. **CORS**: Browser security blocks requests from `localhost:3000` to `localhost:8000` unless CORS headers are set. By proxying, the browser thinks it is talking to the same server.
2. **Production readiness**: In production, you can change the destination to a real server URL without modifying any frontend code.

**C# analogy**: Like configuring a reverse proxy in ASP.NET's `Startup.cs` or in IIS.

**Python analogy**: Like Nginx sitting in front of a Django/Flask app and forwarding requests to the right backend.

---

## 12. Suspense Boundaries

The leads page uses a React `Suspense` boundary:

```tsx
// frontend/app/leads/page.tsx
import { Suspense } from "react";

export default function LeadsPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </AppShell>
      }
    >
      <LeadsPageContent />
    </Suspense>
  );
}
```

This pattern is needed because `LeadsPageContent` uses `useSearchParams()`, which requires a Suspense boundary in Next.js App Router. When the component is loading (reading search parameters during server rendering), React shows the `fallback` content (a loading spinner inside the app shell). Once ready, it swaps in the actual content.

`Suspense` is React's built-in mechanism for handling asynchronous operations during rendering. Next.js uses it extensively for:
- Loading states during navigation
- Streaming server-rendered content
- Components that read URL parameters

---

## Key Takeaway Summary

Here is a concise reference of the core concepts:

**Next.js is to React what ASP.NET is to Razor components, or what Django is to Jinja2 templates.** It is the framework that adds routing, rendering, optimization, and structure on top of the UI library.

**File-based routing**: Folders in `app/` become URL paths. `app/leads/page.tsx` serves `/leads`. No manual route configuration needed.

**Layouts wrap pages**: `layout.tsx` is like `_Layout.cshtml` (C#) or `base.html` (Django). It provides the consistent shell (HTML structure, providers, sidebar) that surrounds every page.

**Server Components are the default**: They run on the server and produce HTML. They cannot use hooks or event handlers. Add `"use client"` only when you need interactivity.

**The Providers pattern**: A single Client Component wraps the app with context providers (React Query, theme, toasts) at the root. The layout (Server Component) renders this one Client Component, and everything inside it is client-side.

**Hydration**: The server sends HTML for fast initial load, then React "wakes it up" by attaching JavaScript. If server HTML does not match client render, you get a hydration error. Use the `mounted` guard pattern for content that depends on browser state (like theme).

**Navigation**: Use `Link` for clickable links (declarative), `useRouter().push()` for programmatic navigation, and `usePathname()` to detect the current route.

These concepts form the foundation for understanding the full application architecture. The next documents will build on this by covering data fetching (React Query), the component library (shadcn/ui + Tailwind), and the API integration layer.
