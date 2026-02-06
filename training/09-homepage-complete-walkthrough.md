# 09 — Homepage Complete Walkthrough

This is the capstone document of the training series. Every concept you learned across the previous eight documents converges on a single page: the NBL dashboard homepage. We will trace the full lifecycle of a request to `/`, then walk through `page.tsx` line by line, connecting each pattern back to the document where it was introduced. By the end, you should be able to read any page in this codebase and identify every construct at work.

---

## Table of Contents

1. [The Request Lifecycle](#the-request-lifecycle)
2. [page.tsx — Line by Line](#pagetsx--line-by-line)
   - [Imports (Lines 1-13)](#imports-lines-1-13)
   - [Component Function and Data Fetching (Lines 15-32)](#component-function-and-data-fetching-lines-15-32)
   - [Event Handler (Lines 34-42)](#event-handler-lines-34-42)
   - [Loading State (Lines 44-52)](#loading-state-lines-44-52)
   - [Header Section (Lines 58-82)](#header-section-lines-58-82)
   - [Stats Cards (Line 85)](#stats-cards-line-85)
   - [Charts Grid (Lines 88-92)](#charts-grid-lines-88-92)
   - [Duplicates Alert (Lines 96-121)](#duplicates-alert-lines-96-121)
   - [Last Run Card (Lines 123-163)](#last-run-card-lines-123-163)
3. [The Complete Component Tree](#the-complete-component-tree)
4. [Cross-Reference Table](#cross-reference-table)
5. [What to Explore Next](#what-to-explore-next)

---

## The Request Lifecycle

When a user types `http://localhost:3000/` into their browser and presses Enter, an eight-step sequence unfolds. Each step draws on concepts from a different document in this series.

### Step 1 — Browser Sends a Request

The browser sends an HTTP GET request to `localhost:3000`. The Next.js development server is listening on that port.

### Step 2 — Next.js File-Based Routing Resolves the Page

Next.js uses **file-based routing** (Document 04). The URL `/` maps to `app/page.tsx` because a file named `page.tsx` at the root of the `app/` directory is the convention for the index route. There is no router configuration file. The file system is the router.

### Step 3 — Layout Renders First

Before `page.tsx` runs, Next.js renders the **root layout** at `app/layout.tsx` (Document 04). The layout is responsible for the outer HTML shell:

- The `<html>` element with language and theme class attributes.
- The `<body>` element with the application font applied via `next/font`.
- The `<Providers>` wrapper component, which wraps `{children}`.

The `{children}` slot is where the matched page component will be inserted. This is the **children pattern** from Document 03 applied at the framework level.

### Step 4 — Page Renders as Children

`page.tsx` renders inside the `{children}` slot of the layout. The layout acts as a persistent shell; the page is the variable content that changes as the user navigates between routes.

### Step 5 — Client-Side Hydration

The top of `page.tsx` contains the `"use client"` directive (Document 04). This tells Next.js that this component must hydrate in the browser. The server sends pre-rendered HTML for fast initial paint, then React **hydrates** it by attaching event handlers and making the page interactive. All hooks, event handlers, and browser APIs become available after hydration.

### Step 6 — React Query Fires API Requests

Once the component mounts in the browser, three `useQuery` hooks fire (Document 06):

| Query Key | API Function | Endpoint |
|---|---|---|
| `["stats"]` | `getStats()` | `GET /api/stats` |
| `["pipelineStatus"]` | `getPipelineStatus()` | `GET /api/pipeline/status` |
| `["duplicatesCount"]` | `getDuplicatesCount()` | `GET /api/duplicates/count` |

React Query manages these requests independently. Each has its own loading state, error state, and cache entry. The requests fire in parallel because none depends on another's result.

### Step 7 — Loading Spinner Displays

While the `stats` query is in flight, the `isLoading` flag is `true`. The component hits an early return (Document 03) that renders a centered `Loader2` spinner with the Tailwind class `animate-spin` (Document 05). The user sees this for a fraction of a second on a fast connection.

### Step 8 — Dashboard Renders with Data

Once the stats data arrives, `isLoading` flips to `false` and `stats` is populated. React re-renders the component (Document 03), skipping the early return and rendering the full dashboard: header, stats cards, charts, and bottom row.

---

## page.tsx — Line by Line

### Imports (Lines 1-13)

```tsx
"use client";
```

The **"use client" directive** marks this file as a Client Component (Document 04). It must be the very first line of the file, before any imports. Without it, Next.js would treat the file as a Server Component, and hooks like `useQuery` would fail because hooks require a browser environment with React's component lifecycle.

```tsx
import { useQuery } from "@tanstack/react-query";
```

The `useQuery` hook from React Query (Document 06). This is the primary data-fetching primitive in the application. It accepts a configuration object with `queryKey` (a unique cache identifier) and `queryFn` (the function that fetches data), and returns an object containing `data`, `isLoading`, `error`, and utility functions like `refetch`.

```tsx
import { AppShell } from "@/components/layout/app-shell";
```

The `AppShell` component provides the persistent page layout: sidebar navigation on the left, main content area on the right. It accepts `{children}` as a prop (Document 03, the children pattern). The `@/` prefix is a Next.js path alias that resolves to the project root, so you never need fragile relative paths like `../../components/`.

```tsx
import { StatsCards } from "@/components/dashboard/stats-cards";
```

A **presentation component** (Document 03) that receives stats data as props and renders four summary cards. It has no data-fetching logic of its own. The parent (`DashboardPage`) fetches the data and passes it down. This separation of concerns makes components reusable and testable.

```tsx
import { TypePieChart } from "@/components/dashboard/type-pie-chart";
import { CountyBarChart } from "@/components/dashboard/county-bar-chart";
import { StageBarChart } from "@/components/dashboard/stage-bar-chart";
```

Three chart components built with Recharts (Document 08). Each wraps a Recharts `PieChart` or `BarChart` in a responsive container and accepts a slice of the stats data. They follow the same pattern: receive data as props, render a chart.

```tsx
import { getStats, triggerPipelineRun, getPipelineStatus, getDuplicatesCount } from "@/lib/api";
```

API client functions (Document 06). Each is an `async` function (Document 01) that calls `fetch()` against the FastAPI backend at `localhost:8000` and returns parsed JSON. These are the `queryFn` values passed to `useQuery`, and `triggerPipelineRun` is called directly from an event handler.

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
```

**shadcn/ui components** (Document 07). `Button` accepts props like `variant`, `size`, `disabled`, and `onClick`. `Card` and its sub-components (`CardHeader`, `CardTitle`, `CardContent`) form a **compound component pattern** where the parent provides the container styling and each child fills a specific slot.

```tsx
import { toast } from "sonner";
```

The `toast` function from the Sonner library (Document 07). It creates non-blocking notification popups. `toast.success()` shows a green confirmation message; `toast.error()` shows a red error message. The toast container is mounted once in `layout.tsx` via the `<Toaster />` component.

```tsx
import { Loader2, Play, Copy, ArrowRight, Clock, Zap, TrendingUp } from "lucide-react";
```

**Lucide icons** (Document 07). These are React components that render inline SVGs. They accept `className` for Tailwind styling (e.g., `className="h-4 w-4"` to set dimensions). They are tree-shaken at build time, so importing individual icons does not bloat the bundle.

```tsx
import Link from "next/link";
```

The Next.js `Link` component (Document 04). It performs **client-side navigation** instead of a full page reload. When the user clicks a `Link`, Next.js fetches only the new page's JavaScript and data, leaving the layout shell intact. This is what makes navigation feel instantaneous.

```tsx
import { formatLocalDateTime } from "@/lib/utils";
```

A utility function that formats ISO timestamps into human-readable local date strings. Utility functions like this live in `lib/utils.ts` and are pure functions with no side effects, making them trivial to test.

---

### Component Function and Data Fetching (Lines 15-32)

```tsx
export default function DashboardPage() {
```

Three concepts in one line:

- **`export default`** (Document 01): Makes this function the default export of the module. Next.js requires that each `page.tsx` file has a default export. When another file imports this module without curly braces (`import DashboardPage from "..."`), it gets this function.
- **`function DashboardPage()`**: A named function component (Document 03). React calls this function to get the JSX it should render. Every time state or props change, React calls this function again.

```tsx
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });
```

This is **destructuring with rename** (Document 01). The `useQuery` hook returns an object with a `data` property, but `data` is too generic a name when you have multiple queries. The syntax `{ data: stats }` extracts the `data` property and assigns it to a local variable named `stats`. The `isLoading` property is extracted without renaming.

The `queryKey: ["stats"]` is a **cache key** (Document 06). React Query uses this array to identify, cache, and invalidate this particular query. If any other component in the application calls `useQuery` with the same key, it will share the cached data instead of making a duplicate network request.

The `queryFn: getStats` uses **shorthand property syntax** (Document 01). Since the key and value have the same name, you write `queryFn: getStats` instead of `queryFn: function() { return getStats(); }`. The function reference is passed directly; React Query will call it when it needs data.

```tsx
  const { data: pipelineStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => query.state.data?.running ? 2000 : false,
  });
```

This query introduces **conditional polling** (Document 06). The `refetchInterval` option accepts either a number (poll every N milliseconds) or a function that returns a number or `false`. Here, the function checks whether the pipeline is currently running:

- `query.state.data?.running` uses **optional chaining** (Document 01). If `query.state.data` is `null` or `undefined`, the expression short-circuits to `undefined` instead of throwing a TypeError. If `data` exists and `running` is `true`, the expression evaluates to `true`.
- When the pipeline is running, the query re-fetches every 2000 milliseconds (2 seconds), providing near-real-time status updates.
- When the pipeline is idle, the function returns `false`, which disables polling entirely to avoid unnecessary network traffic.

The `refetch: refetchStatus` destructuring extracts the manual refetch function and renames it to `refetchStatus`. This function is called in the event handler after triggering a pipeline run.

```tsx
  const { data: duplicatesData } = useQuery({
    queryKey: ["duplicatesCount"],
    queryFn: getDuplicatesCount,
  });
```

The third query fetches the count of detected duplicates. Only the `data` property is needed, renamed to `duplicatesData`. The loading state is not destructured because the duplicates alert is not critical to the initial render; it simply will not appear until data arrives, thanks to conditional rendering.

---

### Event Handler (Lines 34-42)

```tsx
  const handleRunPipeline = async () => {
    try {
      await triggerPipelineRun();
      toast.success("Pipeline started");
      refetchStatus();
    } catch {
      toast.error("Failed to start pipeline");
    }
  };
```

This block combines several concepts:

- **`const handleRunPipeline`**: Declares the function as a constant (Document 01). By convention, event handlers in React are prefixed with `handle` to distinguish them from the prop names that receive them (which are prefixed with `on`).
- **`async () =>`**: An async arrow function (Document 01). The `async` keyword allows the use of `await` inside the function body. Arrow functions capture the surrounding `this` context, though in React function components `this` is not used, so the practical reason for arrows here is syntactic brevity.
- **`await triggerPipelineRun()`**: Pauses execution until the API call completes (Document 01). If the API returns a success response, execution continues to the next line. If it throws, execution jumps to the `catch` block.
- **`toast.success("Pipeline started")`**: Shows a green toast notification (Document 07). This provides immediate visual feedback so the user knows their action succeeded.
- **`refetchStatus()`**: Manually triggers the `pipelineStatus` query to re-fetch (Document 06). This is necessary because the status just changed (the pipeline started running), and we want the UI to reflect that immediately rather than waiting for the next automatic fetch.
- **`try/catch`** (Document 01): Error handling. If `triggerPipelineRun()` throws (network error, server 500, etc.), the catch block runs instead, showing an error toast. The user sees feedback either way.

---

### Loading State (Lines 44-52)

```tsx
  if (isLoading || !stats) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }
```

This is the **early return pattern** (Document 03). Instead of wrapping the entire render output in a conditional, we check the loading condition at the top and return a simpler component. Everything below this block can assume that `stats` is defined and populated.

The condition `isLoading || !stats` is defensive. `isLoading` is `true` during the initial fetch. The `!stats` guard handles the edge case where `isLoading` has flipped to `false` but `data` is still `undefined` (which can happen briefly during transitions).

The Tailwind classes on the wrapper `div` (Document 05):

| Class | Effect |
|---|---|
| `flex` | Sets `display: flex` |
| `items-center` | Sets `align-items: center` (vertical centering) |
| `justify-center` | Sets `justify-content: center` (horizontal centering) |
| `h-64` | Sets `height: 16rem` (256px), giving the spinner a defined vertical space |

The `Loader2` icon classes:

| Class | Effect |
|---|---|
| `h-8` | Sets `height: 2rem` (32px) |
| `w-8` | Sets `width: 2rem` (32px) |
| `animate-spin` | Applies a continuous 360-degree rotation animation (Document 05) |
| `text-primary` | Uses the theme's primary color (Document 05, theme-aware colors) |

Note that the spinner is still wrapped in `<AppShell>`. This means the sidebar remains visible during loading. The user sees the navigation immediately and knows the application is functional; only the main content area shows a loading state.

---

### Header Section (Lines 58-82)

```tsx
<div className="flex items-center justify-between mb-8">
  <div>
    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
    <p className="text-muted-foreground mt-1">
      New business leads across Middle Tennessee
    </p>
  </div>
  <Button
    onClick={handleRunPipeline}
    disabled={pipelineStatus?.running}
    size="lg"
    className="bg-accent-gradient"
  >
    {pipelineStatus?.running ? (
      <>
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Running...
      </>
    ) : (
      <>
        <Play className="mr-2 h-4 w-4" />
        Run Pipeline
      </>
    )}
  </Button>
</div>
```

The outer `div` uses `flex items-center justify-between` (Document 05). This creates a horizontal layout where the left content (title and subtitle) and the right content (button) are pushed to opposite ends of the row. The `mb-8` adds `margin-bottom: 2rem` to separate the header from the content below.

**Typography classes** on the `h1` (Document 05):

| Class | Effect |
|---|---|
| `text-3xl` | Sets `font-size: 1.875rem` |
| `font-bold` | Sets `font-weight: 700` |
| `tracking-tight` | Sets `letter-spacing: -0.025em`, pulling letters slightly closer for a polished heading look |

The `text-muted-foreground` class on the `<p>` tag (Document 05) applies a **theme-aware color**. In dark mode, this is a muted gray that provides visual hierarchy without competing with the heading. In light mode, it adjusts accordingly. These semantic color names are defined as CSS custom properties in the theme system.

**The Button component** (Document 07):

- `onClick={handleRunPipeline}` attaches the event handler (Document 03). When the user clicks, React calls `handleRunPipeline`.
- `disabled={pipelineStatus?.running}` conditionally disables the button (Document 07). The optional chaining `?.` (Document 01) handles the case where `pipelineStatus` is still `undefined` before the query resolves. If `undefined`, the expression evaluates to `undefined`, which is falsy, so the button remains enabled.
- `size="lg"` is a **variant prop** (Document 07). shadcn/ui buttons come in several sizes (`sm`, `default`, `lg`, `icon`), each applying different padding and font-size values.
- `className="bg-accent-gradient"` applies a custom gradient defined in the project's `globals.css`. This overrides the button's default background color with the blue-to-purple gradient from the glassmorphism design system.

**Conditional button content** uses a **ternary expression** (Document 01) inside JSX (Document 03):

```tsx
{pipelineStatus?.running ? (
  <>
    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    Running...
  </>
) : (
  <>
    <Play className="mr-2 h-4 w-4" />
    Run Pipeline
  </>
)}
```

The `<>...</>` syntax is a **Fragment** (Document 03). Fragments let you group multiple elements without adding an extra DOM node. Here, each branch of the ternary returns an icon and text, and the Fragment wraps them into a single expression that the ternary can return. The `mr-2` class on each icon adds `margin-right: 0.5rem` to space the icon from the text.

---

### Stats Cards (Line 85)

```tsx
<StatsCards stats={stats} />
```

This is **passing props** (Document 03) at its simplest. The `stats` object fetched by React Query is passed to the `StatsCards` component, which handles all rendering logic for the four summary cards. The parent does not need to know the internal structure of `StatsCards`; it just provides the data contract.

The `stats` object has a TypeScript interface (Document 02) that defines its shape: `total_leads`, `new_leads`, `avg_score`, and aggregate breakdowns like `by_type`, `by_county`, and `by_stage`. The type system ensures that if the API response shape changes, TypeScript will flag every component that depends on the old shape.

---

### Charts Grid (Lines 88-92)

```tsx
<div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
  <TypePieChart data={stats.by_type} />
  <CountyBarChart data={stats.by_county} />
  <StageBarChart data={stats.by_stage} />
</div>
```

This is a **responsive grid** (Document 05). The classes apply progressively:

| Class | Breakpoint | Effect |
|---|---|---|
| `grid` | All sizes | Sets `display: grid` |
| `gap-6` | All sizes | Sets `gap: 1.5rem` between grid items |
| `md:grid-cols-2` | 768px and up | Two columns |
| `lg:grid-cols-3` | 1024px and up | Three columns |

On a phone, the three charts stack vertically in a single column (the default grid behavior). On a tablet, they arrange into two columns (with one chart wrapping to a second row). On a desktop, all three sit side by side. No media queries are written by hand; Tailwind's responsive prefix system (Document 05) handles it.

Each chart component receives a **data slice**. The `stats.by_type` property is typed as `Record<string, number>` (Document 02), which means it is an object whose keys are strings (business type names) and values are numbers (counts). The chart components (Document 08) transform this data into the array-of-objects format that Recharts expects.

---

### Duplicates Alert (Lines 96-121)

```tsx
{duplicatesData && duplicatesData.count > 0 && (
  <Card className="border-warning/20">
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-base">
        <Copy className="h-4 w-4 text-warning" />
        Potential Duplicates Found
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-muted-foreground mb-3">
        {duplicatesData.count} potential duplicate leads detected.
      </p>
      <Link href="/duplicates">
        <Button variant="outline" size="sm">
          Review Duplicates
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </Link>
    </CardContent>
  </Card>
)}
```

**Conditional rendering with `&&`** (Document 03). The entire `Card` block only renders if both conditions are true:

1. `duplicatesData` is truthy (the query has resolved and returned data).
2. `duplicatesData.count > 0` (there are actual duplicates to review).

If either condition is false, React renders nothing for this section. This is cleaner than a ternary when there is no `else` branch.

**`border-warning/20`** (Document 05) demonstrates Tailwind's **opacity modifier syntax**. The `/20` appends 20% opacity to the `warning` border color, creating a subtle tinted border that draws attention without being visually aggressive.

**Compound component structure** (Document 07):

```
Card
  CardHeader (pb-3 reduces default bottom padding)
    CardTitle (flex layout with icon and text)
  CardContent
    <p> description
    Link > Button
```

The `Card`, `CardHeader`, `CardTitle`, and `CardContent` components each apply a portion of the card's styling. `CardHeader` provides padding for the top section. `CardTitle` styles the heading text. `CardContent` provides padding for the body. Together they form a consistent, composable card layout.

**Navigation** (Document 04): The `Link` component wraps the `Button`, making the entire button a navigation trigger. Clicking it performs a client-side transition to `/duplicates` without a full page reload. The `Button` with `variant="outline"` renders with a transparent background and a visible border, appropriate for a secondary action.

---

### Last Run Card (Lines 123-163)

```tsx
{stats.last_run && (
  <Card>
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-base">
        <Clock className="h-4 w-4 text-muted-foreground" />
        Last Pipeline Run
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Date</p>
          <p className="text-sm font-medium">
            {formatLocalDateTime(stats.last_run.started_at)}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Status</p>
          <p className="text-sm font-medium flex items-center gap-1">
            {stats.last_run.status === "success" ? (
              <Zap className="h-3 w-3 text-green-500" />
            ) : (
              <TrendingUp className="h-3 w-3 text-yellow-500" />
            )}
            <span className="capitalize">{stats.last_run.status}</span>
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Leads Found</p>
          <p className="text-sm font-medium">{stats.last_run.leads_added}</p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Duration</p>
          <p className="text-sm font-medium">{stats.last_run.duration}s</p>
        </div>
      </div>
    </CardContent>
  </Card>
)}
```

**Conditional rendering** (Document 03): The entire card is gated behind `stats.last_run &&`. If the application has never run the pipeline, `last_run` is `null` and this card does not appear.

**`grid grid-cols-2 gap-4`** (Document 05) creates a fixed two-column grid for the run metadata. Unlike the responsive charts grid above, this one does not change at different breakpoints because the content is compact enough to always fit in two columns.

**`formatLocalDateTime(stats.last_run.started_at)`** calls a utility function. The raw `started_at` value is an ISO 8601 timestamp string from the API. The utility converts it to a localized, human-readable format using the browser's `Intl.DateTimeFormat` API. This is a plain JavaScript function call (Document 01) inside a JSX expression.

**Ternary for status icon** (Document 01, Document 03):

```tsx
{stats.last_run.status === "success" ? (
  <Zap className="h-3 w-3 text-green-500" />
) : (
  <TrendingUp className="h-3 w-3 text-yellow-500" />
)}
```

If the last run succeeded, a green lightning bolt icon renders. Otherwise, a yellow trending-up icon renders. The `text-green-500` and `text-yellow-500` classes (Document 05) apply specific color values from Tailwind's color palette.

**`capitalize`** (Document 05) is a Tailwind utility that applies `text-transform: capitalize` in CSS. The raw status string from the API is lowercase (`"success"` or `"partial"`), and this class ensures the first letter displays as uppercase without modifying the data.

---

## The Complete Component Tree

The following tree shows every component involved in rendering the homepage, from the outermost HTML element to the innermost leaf node. Indentation represents nesting.

```
RootLayout (app/layout.tsx -- Server Component)
|
+-- <html lang="en">
+-- <body className={font.className}>
    |
    +-- Providers (providers.tsx -- Client Component)
        |
        +-- ThemeProvider (next-themes)
        |   Manages dark/light mode. Reads system preference
        |   on first visit, stores choice in localStorage.
        |
        +-- QueryClientProvider (React Query)
        |   Provides the query cache to all descendants.
        |   Configured with staleTime: 5000ms and
        |   refetchOnWindowFocus: false.
        |
        +-- DashboardPage (app/page.tsx -- Client Component)
            |
            +-- AppShell
                |
                +-- NavSidebar
                |   +-- Logo (Zap icon + "NBL" text)
                |   +-- Navigation links (x5):
                |   |   Dashboard, Leads, Kanban, Duplicates, Pipeline
                |   +-- Theme toggle button (sun/moon icon)
                |
                +-- <main>
                    |
                    +-- Header row (flex justify-between)
                    |   +-- Title ("Dashboard") + subtitle
                    |   +-- Run Pipeline Button
                    |       +-- Loader2 (when running)
                    |       +-- Play icon (when idle)
                    |
                    +-- StatsCards
                    |   +-- Card: Total Leads (stats.total_leads)
                    |   +-- Card: New Leads (stats.new_leads)
                    |   +-- Card: Avg Score (stats.avg_score)
                    |   +-- Card: This Week (stats.this_week)
                    |
                    +-- Charts Grid (responsive 1/2/3 columns)
                    |   +-- TypePieChart (stats.by_type)
                    |   +-- CountyBarChart (stats.by_county)
                    |   +-- StageBarChart (stats.by_stage)
                    |
                    +-- Bottom Row
                        +-- Duplicates Alert Card (conditional)
                        |   +-- Copy icon + count
                        |   +-- Link to /duplicates
                        +-- Last Run Card (conditional)
                            +-- Date, Status, Leads Found, Duration
```

Understanding this tree is understanding the application. Every parent controls what data its children receive. Every child is responsible only for rendering its slice. This is the core mental model from Document 03.

---

## Cross-Reference Table

This table maps every significant pattern on the homepage back to the training document where it was introduced. Use it as a quick reference when you encounter something unfamiliar in other pages of the codebase.

| Pattern | Example on Homepage | Document |
|---|---|---|
| Arrow functions | `async () => { ... }` in `handleRunPipeline` | 01 - JavaScript |
| Destructuring with rename | `{ data: stats, isLoading }` from `useQuery` | 01 - JavaScript |
| Optional chaining | `pipelineStatus?.running` | 01 - JavaScript |
| Template literals | `${stats.last_run.duration}s` | 01 - JavaScript |
| Ternary expressions | `status === "success" ? <Zap /> : <TrendingUp />` | 01 - JavaScript |
| `async`/`await` | `await triggerPipelineRun()` | 01 - JavaScript |
| `try`/`catch` | Error handling in `handleRunPipeline` | 01 - JavaScript |
| `export default` | `export default function DashboardPage()` | 01 - JavaScript |
| Interfaces and types | `Stats`, `PipelineStatus` type definitions | 02 - TypeScript |
| `Record<string, number>` | `stats.by_type`, `stats.by_county` data shapes | 02 - TypeScript |
| Type narrowing | `isLoading \|\| !stats` guard before main render | 02 - TypeScript |
| Components and props | `<StatsCards stats={stats} />` | 03 - React |
| Children pattern | `<AppShell>{...content...}</AppShell>` | 03 - React |
| Conditional rendering (`&&`) | `{duplicatesData && duplicatesData.count > 0 && (...)}` | 03 - React |
| Conditional rendering (ternary) | Running/idle button content | 03 - React |
| Early return pattern | Loading spinner guard clause | 03 - React |
| Fragments (`<>...</>`) | Wrapping icon + text in button content | 03 - React |
| `"use client"` directive | First line of `page.tsx` | 04 - Next.js |
| File-based routing | `app/page.tsx` maps to `/` | 04 - Next.js |
| Layouts and `{children}` | `layout.tsx` wrapping `page.tsx` | 04 - Next.js |
| `Link` for navigation | `<Link href="/duplicates">` | 04 - Next.js |
| Hydration | Server-rendered HTML + client-side React | 04 - Next.js |
| Flexbox utilities | `flex items-center justify-between` | 05 - Tailwind |
| Responsive grid | `grid md:grid-cols-2 lg:grid-cols-3` | 05 - Tailwind |
| Spacing utilities | `gap-6`, `mb-8`, `mr-2`, `mt-1`, `pb-3` | 05 - Tailwind |
| Typography utilities | `text-3xl font-bold tracking-tight` | 05 - Tailwind |
| Theme-aware colors | `text-primary`, `text-muted-foreground` | 05 - Tailwind |
| Opacity modifier | `border-warning/20` | 05 - Tailwind |
| Animation | `animate-spin` on `Loader2` | 05 - Tailwind |
| Text transform | `capitalize` on status text | 05 - Tailwind |
| `useQuery` with `queryKey`/`queryFn` | All three data-fetching calls | 06 - React Query |
| Conditional polling | `refetchInterval: (query) => ... ? 2000 : false` | 06 - React Query |
| Manual refetch | `refetchStatus()` after triggering pipeline | 06 - React Query |
| Loading states | `isLoading` from `useQuery` | 06 - React Query |
| `Button` with variants | `variant="outline"`, `size="lg"`, `size="sm"` | 07 - shadcn/ui |
| `Card` compound components | `Card > CardHeader > CardTitle > CardContent` | 07 - shadcn/ui |
| Toast notifications | `toast.success(...)`, `toast.error(...)` | 07 - shadcn/ui |
| Lucide icons | `Loader2`, `Play`, `Copy`, `ArrowRight`, `Clock`, `Zap`, `TrendingUp` | 07 - shadcn/ui |
| Pie chart | `<TypePieChart data={stats.by_type} />` | 08 - Recharts |
| Bar chart | `<CountyBarChart data={stats.by_county} />` | 08 - Recharts |
| Data transformation for charts | `Record<string, number>` to array-of-objects | 08 - Recharts |

---

## What to Explore Next

You have now traced every line of the homepage and connected it to the foundational concept where it was taught. The remaining pages of the application use the same patterns in different combinations. Here is a suggested order for self-directed exploration:

### `frontend/app/leads/page.tsx` — Tables, Pagination, Search, and Filters

This page introduces new patterns: controlled form inputs for search and filter dropdowns, pagination state management with query parameters, and the shadcn/ui `Table` component. The data-fetching pattern is the same `useQuery` approach from the homepage, but with dynamic query keys that change based on filter state (Document 06 covers query key dependencies).

### `frontend/app/kanban/page.tsx` — Drag-and-Drop with dnd-kit

The Kanban page uses the `@dnd-kit/core` library for drag-and-drop interactions. Each stage column is a droppable zone, and each lead card is a draggable item. When a card is dropped into a new column, a mutation fires to update the lead's stage via the API. This is a natural extension of the event handling patterns from Document 03 and the mutation concepts from Document 06.

### `frontend/app/duplicates/page.tsx` — Duplicate Detection and Merge UI

This page presents pairs of potentially duplicate leads side by side, letting the user merge or dismiss them. It combines conditional rendering (Document 03), API mutations (Document 06), and compound card layouts (Document 07) in a workflow-oriented UI.

### External Documentation

When you need to go deeper than this training series covers, these are the authoritative references:

- **Next.js**: [https://nextjs.org/docs](https://nextjs.org/docs) -- Routing, data fetching, deployment, middleware, and server actions.
- **React**: [https://react.dev](https://react.dev) -- Hooks reference, component patterns, performance optimization, and the new React compiler.
- **Tailwind CSS**: [https://tailwindcss.com/docs](https://tailwindcss.com/docs) -- Every utility class, configuration options, and plugin system.
- **React Query**: [https://tanstack.com/query/latest/docs](https://tanstack.com/query/latest/docs) -- Advanced caching strategies, optimistic updates, and infinite queries.
- **shadcn/ui**: [https://ui.shadcn.com](https://ui.shadcn.com) -- Component API reference and customization guides.
- **Recharts**: [https://recharts.org/en-US/api](https://recharts.org/en-US/api) -- Chart types, props, and responsive container patterns.

---

## Series Summary

| Document | Topic | Core Takeaway |
|---|---|---|
| 00 | Welcome and Setup | Development environment and project structure |
| 01 | JavaScript | The language: functions, destructuring, async/await, modules |
| 02 | TypeScript | The type system: interfaces, generics, type safety |
| 03 | React | The component model: props, state, hooks, composition |
| 04 | Next.js | The framework: routing, layouts, server vs. client components |
| 05 | Tailwind CSS | The styling: utility classes, responsive design, theming |
| 06 | React Query | The data layer: caching, loading states, mutations |
| 07 | shadcn/ui | The component library: buttons, cards, dialogs, toasts |
| 08 | Recharts | The visualization layer: charts, responsive containers, data formatting |
| **09** | **Homepage Walkthrough** | **Everything together: one page, every concept** |

Every line of code in this application is built from these primitives. When you encounter something new in the codebase, identify which layer it belongs to (language, type system, component model, framework, styling, data fetching, component library, or visualization), and refer back to the corresponding document. The patterns repeat; only the combinations change.
