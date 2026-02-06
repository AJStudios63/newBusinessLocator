# 06 -- Data Fetching with React Query

This is Part 6 of a 10-part series. You already know C#, Python, JavaScript, TypeScript, React, Next.js, and Tailwind from documents 01 through 05. Now we tackle the question every frontend app must answer: how do you get data from the server and keep it in sync?

---

## 1. The Problem React Query Solves

### What Data Fetching Looks Like Without React Query

In a traditional React app, fetching data from an API requires you to wire up multiple pieces of state by hand. Here is what that looks like when you want to load a list of leads from `/api/stats`:

```tsx
import { useState, useEffect } from "react";

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [hasFetchedOnce, setHasFetchedOnce] = useState(false);

  const fetchStats = async () => {
    try {
      if (hasFetchedOnce) setIsRefreshing(true);
      else setIsLoading(true);

      const response = await fetch("/api/stats");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      setStats(data);
      setLastFetched(new Date());
      setHasFetchedOnce(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;
  if (!stats) return null;

  return <StatsCards stats={stats} />;
}
```

Count the problems:

- **Six `useState` calls** just to track one API request.
- **No caching.** If you navigate away and come back, the data is fetched all over again. The user sees a loading spinner every time.
- **No deduplication.** If two components on the same page both need `stats`, you get two identical HTTP requests.
- **No background refresh.** The data is fetched once and never updated unless you write more code.
- **Manual error handling** that is easy to get wrong (forgotten `finally`, race conditions, stale closures).
- **No retry logic.** If the network blips, the request fails permanently.

If you have done this in C#, the equivalent would be calling `HttpClient.GetFromJsonAsync<Stats>()` inside a view model, then manually managing `IsLoading`, `ErrorMessage`, `CachedData`, and `LastFetchTime` properties, plus wiring up a `DispatcherTimer` for periodic refresh. In Python, it would be `requests.get()` with a hand-rolled `@lru_cache` wrapper and manual expiry logic.

### What React Query Gives You

React Query (officially called TanStack Query) replaces all of that with a single hook:

```tsx
const { data: stats, isLoading } = useQuery({
  queryKey: ["stats"],
  queryFn: getStats,
});
```

Two lines. React Query handles:

| Concern | Without React Query | With React Query |
|---|---|---|
| Loading state | Manual `useState` + `useEffect` | `isLoading` boolean returned by hook |
| Error state | Manual try/catch + state | `isError` boolean + `error` object |
| Caching | You build it yourself | Automatic, keyed by `queryKey` |
| Deduplication | Nothing; duplicate fetches happen | Same key = one fetch, shared result |
| Background refetch | Manual timer or polling code | Automatic when data goes stale |
| Retry on failure | Manual retry loop | 3 retries with exponential backoff by default |

---

## 2. Setup: QueryClient and QueryClientProvider

Before any component can use `useQuery`, you need to set up the React Query infrastructure. This happens once, at the top of your component tree. Here is the actual `providers.tsx` file from this project:

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
            staleTime: 5 * 1000,           // Data is "fresh" for 5 seconds
            refetchOnWindowFocus: false,    // Don't refetch when user tabs back
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

### Line-by-line breakdown

**`"use client";`** -- This file uses React hooks (`useState`) and browser-only APIs, so it must be a Client Component. The `"use client"` directive tells Next.js to render it on the client side.

**`const [queryClient] = useState(() => new QueryClient({ ... }));`** -- This creates the `QueryClient` instance exactly once. The `useState` with an initializer function ensures a single instance is created per component lifecycle. Without this pattern, a new `QueryClient` would be created on every render, destroying the cache each time. Note we destructure only `[queryClient]` and ignore the setter -- we never need to replace the client after creation.

**`QueryClient`** -- This is the cache manager. It stores every piece of fetched data, indexed by query key. Think of it as an in-memory dictionary (like C# `ConcurrentDictionary<string, CacheEntry>` or Python `dict`) that also knows when each entry was last fetched and whether it is still fresh.

**`staleTime: 5 * 1000`** -- After data is fetched, it is considered "fresh" for 5,000 milliseconds (5 seconds). During this window, if a component requests the same data, React Query returns the cached version immediately without making a network request. After 5 seconds, the data is marked "stale." The next time a component mounts or the query is accessed, React Query will refetch in the background, showing the stale data while the fresh data loads. This means the user never sees a loading spinner on subsequent visits -- they see the old data instantly, which is then silently replaced with the new data.

**`refetchOnWindowFocus: false`** -- By default, React Query refetches all stale queries when the user tabs back to the browser window. This is useful for applications where data changes frequently (like a chat app), but for our lead management tool it would cause unnecessary API calls. We turn it off.

**`QueryClientProvider`** -- This is a React Context provider. It makes the `queryClient` instance available to every child component in the tree. Any component that calls `useQuery` will find the client through this context. If you forget to wrap your app in `QueryClientProvider`, `useQuery` will throw an error at runtime.

### How This Fits in the App

In a Next.js app, `Providers` wraps the entire application in the root layout:

```tsx
// frontend/app/layout.tsx
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

Every page component rendered inside `{children}` now has access to the shared `QueryClient`.

---

## 3. The useQuery Hook -- Reading Data

The `useQuery` hook is the primary way you read data in React Query. Let us walk through all three real `useQuery` calls from the homepage of this project (`frontend/app/page.tsx`).

### 3.1 Basic Query

```tsx
const { data: stats, isLoading } = useQuery({
  queryKey: ["stats"],
  queryFn: getStats,
});
```

This is the simplest form. Let us break down every part:

**`useQuery({ ... })`** -- You call `useQuery` with a configuration object. React Query calls this the "query options."

**`queryKey: ["stats"]`** -- A unique identifier for this piece of data in the cache. It is always an array. Think of it as the key in a `Dictionary<string[], CachedData>`. If any other component anywhere in the app also calls `useQuery` with `queryKey: ["stats"]`, React Query will not make a second HTTP request -- it will return the same cached data or wait for the in-flight request to complete.

**`queryFn: getStats`** -- The function that React Query calls to fetch the data. This is a reference to the `getStats` function from `api.ts` (we will look at its implementation in Section 5). It must return a `Promise`. React Query calls this function when:
- The component mounts and there is no cached data for this key.
- The cached data is stale and the query is accessed again.
- You manually trigger a refetch.

**`data`** -- The result returned by `queryFn`, once the Promise resolves. Its type is inferred from the return type of `getStats`: since `getStats` returns `Promise<Stats>`, `data` is typed as `Stats | undefined`. It is `undefined` until the first successful fetch.

**`data: stats`** -- This is JavaScript destructuring with rename syntax. The `useQuery` hook returns an object with a property called `data`. Writing `{ data: stats }` extracts that `data` property and assigns it to a local variable named `stats`. This is purely for readability -- `stats.total_leads` is clearer than `data.total_leads` when you have multiple queries in the same component.

**`isLoading`** -- A boolean. `true` while the first fetch is in progress (meaning there is no cached data yet). Once the first fetch completes successfully, `isLoading` becomes `false` and stays `false`, even during background refetches. This is intentional: you want to show data during refetches, not a loading spinner.

### 3.2 Query with Conditional Polling

```tsx
const { data: pipelineStatus, refetch: refetchStatus } = useQuery({
  queryKey: ["pipelineStatus"],
  queryFn: getPipelineStatus,
  refetchInterval: (query) => {
    return query.state.data?.running ? 2000 : false;
  },
});
```

This query introduces two new concepts.

**`refetchInterval`** -- Tells React Query to automatically refetch this data on a recurring interval, like a timer. Here it is not a fixed number but a function. The function receives the current query state and returns either:
- A number (milliseconds between refetches), or
- `false` to stop polling.

**`(query) => { return query.state.data?.running ? 2000 : false; }`** -- The logic: look at the most recently fetched data. If the pipeline is currently running (`running === true`), poll every 2,000 milliseconds (2 seconds). If the pipeline is not running, stop polling entirely. This is a common pattern for progress tracking -- you poll frequently while something is in progress, then stop once it completes.

In C# terms, this is like creating a `System.Timers.Timer` that checks a condition in its `Elapsed` handler and either restarts itself or calls `timer.Stop()`. In Python, it is like an `asyncio` loop with a conditional `await asyncio.sleep(2)`. React Query makes this a one-liner.

**`refetch: refetchStatus`** -- `refetch` is a function that manually triggers a new fetch, ignoring the cache and staleTime. We destructure-rename it to `refetchStatus` for clarity (since we have multiple queries, we want distinct names). You will see this used in Section 7.

**`data: pipelineStatus`** -- The fetched `PipelineStatus` object, destructured and renamed just like in the basic query.

### 3.3 Simple Query

```tsx
const { data: duplicatesData } = useQuery({
  queryKey: ["duplicatesCount"],
  queryFn: getDuplicatesCount,
});
```

This is the absolute minimum `useQuery` call. We only destructure `data` (renamed to `duplicatesData`). We do not need `isLoading` because we do not show a full-page spinner for this query -- the duplicate count card simply does not render until the data arrives:

```tsx
{duplicatesData && duplicatesData.count > 0 && (
  <Card>
    <p>{duplicatesData.count}</p>
    <p>leads to review and merge</p>
  </Card>
)}
```

The `&&` short-circuit means: if `duplicatesData` is `undefined` (still loading) or the count is zero, nothing renders. No loading spinner needed.

---

## 4. Query Keys -- The Cache System

Query keys are the backbone of React Query's caching and deduplication. They deserve dedicated attention.

### Keys Are Arrays

Every query key is an array. The simplest keys are single-element arrays:

```tsx
queryKey: ["stats"]           // The stats data
queryKey: ["pipelineStatus"]  // The pipeline status
queryKey: ["duplicatesCount"] // The duplicate count
```

### Keys Can Include Parameters

When you fetch data that depends on filters or pagination, you include those parameters in the key:

```tsx
queryKey: ["leads", { page: 1, stage: "New" }]
queryKey: ["leads", { page: 2, stage: "New" }]
queryKey: ["leads", { page: 1, stage: "Qualified" }]
```

Each of these is a **different** cache entry. Page 1 of "New" leads and page 2 of "New" leads are cached separately. This means if the user goes from page 2 back to page 1, the page-1 data is shown instantly from cache.

### How Caching Works

When `useQuery` is called with a given key:

1. **Cache hit, data fresh.** The cached data is returned immediately. No network request is made. This happens when someone re-renders a component within the `staleTime` window (5 seconds in our config).

2. **Cache hit, data stale.** The cached data is returned immediately (so the user sees something right away), AND a background fetch is triggered. When the fresh data arrives, the component re-renders with the new data. The user never sees a loading spinner.

3. **Cache miss.** No data exists for this key. A fetch is initiated, `isLoading` is `true`, and the component shows a loading state until the data arrives.

### Deduplication

If two components on the same page both call:

```tsx
useQuery({ queryKey: ["stats"], queryFn: getStats })
```

React Query makes **one** HTTP request and delivers the result to both components. This is automatic. You do not need to coordinate anything.

### Comparison to Familiar Patterns

In C#, the closest equivalent is `IMemoryCache`:

```csharp
// C# equivalent concept
if (!cache.TryGetValue("stats", out Stats stats))
{
    stats = await httpClient.GetFromJsonAsync<Stats>("/api/stats");
    cache.Set("stats", stats, TimeSpan.FromSeconds(5));
}
return stats;
```

In Python, the closest equivalent is `functools.lru_cache` or a dictionary-based cache:

```python
# Python equivalent concept
_cache = {}
_timestamps = {}

def get_stats():
    if "stats" in _cache and time.time() - _timestamps["stats"] < 5:
        return _cache["stats"]
    data = requests.get("/api/stats").json()
    _cache["stats"] = data
    _timestamps["stats"] = time.time()
    return data
```

React Query gives you all of this with zero manual cache management.

---

## 5. The API Client Layer

React Query does not care how you fetch data. It just needs a function that returns a `Promise`. In this project, the API client lives in `frontend/lib/api.ts` and is built in layers: a generic fetch wrapper, then specific functions for each endpoint.

### 5.1 The Generic Fetch Wrapper

```tsx
// frontend/lib/api.ts

import type {
  Lead, LeadsResponse, Stats, PipelineStatus,
  LeadFilters, DuplicatesResponse, MergeRequest,
  // ... more types
} from "./types";

const API_BASE = "/api";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
```

Let us trace through every line.

**`const API_BASE = "/api";`** -- All API URLs start with `/api`. This is a relative URL -- it does not include a hostname. In development, Next.js is configured to proxy requests starting with `/api` to the FastAPI backend at `http://localhost:8000`. In production, a reverse proxy (like Nginx) would handle this routing. The benefit: the frontend code never hardcodes `http://localhost:8000`, so it works in any environment.

**`async function fetchJson<T>(url: string, options?: RequestInit): Promise<T>`** -- This is a generic function. The `<T>` type parameter means the caller specifies what type the JSON response will be. `RequestInit` is a built-in browser type representing the options you can pass to `fetch()` (method, headers, body, etc.). The `?` means options is optional -- GET requests typically do not need any options.

**`const response = await fetch(url, { ... });`** -- `fetch()` is the browser's built-in HTTP client. It is a global function available in all modern browsers and in Node.js 18+. It returns a `Promise<Response>`. The `await` pauses execution until the HTTP response headers arrive (but not necessarily the body).

C# equivalent: `HttpClient.SendAsync(request)`.
Python equivalent: `requests.get(url)` or `aiohttp.ClientSession().get(url)`.

**`...options`** -- The spread operator. If the caller passed `{ method: "POST", body: JSON.stringify(data) }`, those properties are spread into the options object. This merges caller options with our defaults.

**`headers: { "Content-Type": "application/json", ...options?.headers }`** -- We always send `Content-Type: application/json` to tell the server we are sending JSON. The `...options?.headers` part uses optional chaining with spread: if the caller provided custom headers, merge them in; if `options` is `undefined` or `options.headers` is `undefined`, the spread produces nothing (no error).

**`if (!response.ok)`** -- `response.ok` is `true` for HTTP status codes 200-299 and `false` for everything else (400, 404, 500, etc.). Unlike Python's `requests` library, `fetch()` does not throw on non-2xx responses -- you must check manually.

**`const error = await response.json().catch(() => ({ detail: "Request failed" }));`** -- Try to parse the error response body as JSON. Our FastAPI backend returns errors in the format `{ "detail": "Error message" }`. The `.catch()` handles the case where the response body is not valid JSON (for example, a 502 Bad Gateway from a reverse proxy returns HTML, not JSON). In that case, we fall back to a generic error object.

**`throw new Error(error.detail || \`HTTP ${response.status}\`);`** -- If the response is not OK, throw an Error. React Query catches this and stores it in the `error` property returned by `useQuery`. The error message comes from the backend's `detail` field if available, otherwise from the HTTP status code.

**`return response.json();`** -- Parse the successful response body as JSON. The return type is `Promise<T>`, where `T` is whatever the caller specified. TypeScript trusts us that the JSON matches the type. (There is no runtime validation -- this is a TypeScript convention, not a guarantee.)

### 5.2 Specific API Functions

Each endpoint gets its own typed function that wraps `fetchJson`.

**Simple GET:**

```tsx
export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>(`${API_BASE}/stats`);
}
```

This fetches `/api/stats` and tells TypeScript the response will be a `Stats` object. The `Stats` type is defined in `types.ts`:

```tsx
export interface Stats {
  by_stage: Record<string, number>;
  by_county: Record<string, number>;
  by_type: Record<string, number>;
  avg_score: number;
  total_leads: number;
  last_run: PipelineRun | null;
}
```

C# equivalent: `httpClient.GetFromJsonAsync<Stats>("/api/stats")`.
Python equivalent: `Stats(**requests.get("/api/stats").json())` (with a dataclass or Pydantic model).

**GET with query parameters:**

```tsx
export async function getLeads(filters: LeadFilters = {}): Promise<LeadsResponse> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore !== undefined) params.set("minScore", filters.minScore.toString());
  if (filters.maxScore !== undefined) params.set("maxScore", filters.maxScore.toString());
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.limit) params.set("limit", filters.limit.toString());
  if (filters.page !== undefined) params.set("page", filters.page.toString());
  if (filters.pageSize !== undefined) params.set("pageSize", filters.pageSize.toString());

  const query = params.toString();
  return fetchJson<LeadsResponse>(`${API_BASE}/leads${query ? `?${query}` : ""}`);
}
```

**`filters: LeadFilters = {}`** -- Default parameter. If no filters are passed, an empty object is used, meaning no query parameters are added and the backend returns unfiltered leads. This is the same concept as `def get_leads(filters=None):` in Python or `public Task<LeadsResponse> GetLeads(LeadFilters? filters = null)` in C#.

**`new URLSearchParams()`** -- A built-in browser API for building query strings. It handles URL encoding (special characters like spaces become `%20`), so you never have to do string concatenation with `&` and `=` manually.

**`if (filters.q) params.set("q", filters.q);`** -- Only add a parameter if it has a value. This prevents sending `?q=&stage=&county=` with empty values.

**`if (filters.minScore !== undefined)`** -- We use `!== undefined` instead of just `if (filters.minScore)` because `minScore` is a number, and `0` is a valid score but is falsy in JavaScript. `if (filters.minScore)` would skip `0`; `if (filters.minScore !== undefined)` correctly includes it.

**`` `${API_BASE}/leads${query ? `?${query}` : ""}` ``** -- Template literal. If there are query parameters, append `?` followed by the parameter string. If there are none, append nothing. Result: `/api/leads?stage=New&page=1` or just `/api/leads`.

**POST (mutation):**

```tsx
export async function triggerPipelineRun(): Promise<{ message: string; running: boolean }> {
  return fetchJson(`${API_BASE}/pipeline/run`, { method: "POST" });
}
```

This sends a POST request to start the ETL pipeline. The second argument to `fetchJson` provides the HTTP method. POST requests trigger actions on the server (as opposed to GET, which only reads data). The return type is an inline object type -- we do not need a named interface for simple response shapes.

React Query also provides a `useMutation` hook specifically designed for write operations like this. The homepage calls `triggerPipelineRun` directly in an event handler rather than through `useMutation`, which is a simpler approach that works fine for one-off actions. We will see `useMutation` in other parts of the codebase where write operations need loading states and error handling.

---

## 6. Using Query Data in Components

Here is the complete flow from fetch to render, as it actually works in the homepage:

### Step 1: Fetch the data

```tsx
const { data: stats, isLoading } = useQuery({
  queryKey: ["stats"],
  queryFn: getStats,
});
```

When the `DashboardPage` component mounts, React Query checks the cache for the key `["stats"]`. If it is a cache miss, it calls `getStats()`, which calls `fetchJson<Stats>("/api/stats")`, which calls `fetch("/api/stats")`. The HTTP request goes to the FastAPI backend, which queries SQLite and returns JSON.

### Step 2: Handle the loading state

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

While the first fetch is in progress, `isLoading` is `true` and `stats` is `undefined`. The component returns early with a spinning loader icon. The `AppShell` wrapper is rendered even during loading so the sidebar and navigation remain visible -- only the content area shows the spinner.

Note the `|| !stats` guard. This is a TypeScript narrowing pattern. After this check, TypeScript knows `stats` is not `undefined`, so you can access `stats.total_leads` without a type error. Without `!stats`, TypeScript would complain because `isLoading` being `false` does not logically guarantee `data` is defined (there could have been an error).

### Step 3: Render with data

```tsx
return (
  <AppShell>
    <div className="space-y-8">
      <StatsCards stats={stats} />

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <TypePieChart data={stats.by_type} />
        <CountyBarChart data={stats.by_county} />
        <StageBarChart data={stats.by_stage} />
      </div>
    </div>
  </AppShell>
);
```

Once `stats` is available, the component renders child components and passes slices of the data as props. `StatsCards` receives the entire `stats` object. Each chart component receives only the specific `Record<string, number>` it needs.

This is a common pattern: a parent component owns the query and distributes the data downward. The child components (`StatsCards`, `TypePieChart`) are pure presentation components -- they receive typed props, render UI, and know nothing about data fetching.

---

## 7. Manual Refetch and Cache Invalidation

Sometimes you need to force a refetch. In our homepage, this happens when the user clicks "Run Pipeline":

```tsx
// Get the refetch function from useQuery
const { data: pipelineStatus, refetch: refetchStatus } = useQuery({
  queryKey: ["pipelineStatus"],
  queryFn: getPipelineStatus,
  refetchInterval: (query) => {
    return query.state.data?.running ? 2000 : false;
  },
});

// Call it after triggering the pipeline
const handleRunPipeline = async () => {
  try {
    await triggerPipelineRun();        // POST /api/pipeline/run
    toast.success("Pipeline started"); // Show success notification
    refetchStatus();                   // Immediately refetch pipeline status
  } catch {
    toast.error("Failed to start pipeline");
  }
};
```

### What happens step by step

1. The user clicks the "Run Pipeline" button, which calls `handleRunPipeline`.
2. `triggerPipelineRun()` sends a POST request to start the ETL pipeline on the backend.
3. If the POST succeeds, we show a success toast notification.
4. `refetchStatus()` immediately fetches `/api/pipeline/status` again, bypassing the cache and staleTime. The new status will show `running: true`.
5. Because `running` is now `true`, the `refetchInterval` function returns `2000`, which starts the polling loop.
6. Every 2 seconds, React Query refetches the pipeline status. The UI updates to reflect progress.
7. When the pipeline finishes, the status returns `running: false`. The `refetchInterval` function returns `false`, and polling stops.

### Cache Invalidation

There is another approach to triggering refetches: **cache invalidation.** Instead of calling `refetch()` on a specific query, you can invalidate a cache key, which marks it as stale and triggers a refetch for any component currently using it:

```tsx
import { useQueryClient } from "@tanstack/react-query";

const queryClient = useQueryClient();

// Invalidate a specific query
queryClient.invalidateQueries({ queryKey: ["stats"] });

// Invalidate all queries that start with "leads"
queryClient.invalidateQueries({ queryKey: ["leads"] });
```

The `invalidateQueries` approach is particularly useful after a mutation that affects multiple queries. For example, after merging two duplicate leads, you might want to invalidate both `["leads"]` and `["stats"]` because both the lead list and the aggregate counts have changed.

The difference between `refetch()` and `invalidateQueries()`:
- `refetch()` -- Immediately refetches one specific query, even if it is still fresh.
- `invalidateQueries()` -- Marks matching queries as stale. They refetch on next access, or immediately if a component is currently using them. Can match multiple queries at once using partial key matching.

---

## 8. The Complete Data Flow

Here is the full lifecycle of a data request, from component mount to screen render:

```
DashboardPage component mounts
  |
  v
useQuery({ queryKey: ["stats"], queryFn: getStats })
  |
  v
React Query checks internal cache for key ["stats"]
  |
  +-- Cache MISS (first visit)
  |     |
  |     v
  |   isLoading = true, data = undefined
  |   Component renders loading spinner
  |     |
  |     v
  |   React Query calls getStats()
  |     |
  |     v
  |   fetchJson<Stats>("/api/stats")
  |     |
  |     v
  |   Browser fetch() sends HTTP GET /api/stats
  |     |
  |     v
  |   FastAPI backend queries SQLite, returns JSON
  |     |
  |     v
  |   response.json() parses body as Stats
  |     |
  |     v
  |   Data stored in cache under key ["stats"]
  |   with timestamp = now
  |     |
  |     v
  |   isLoading = false, data = Stats object
  |   Component re-renders with data
  |     |
  |     v
  |   StatsCards, TypePieChart, CountyBarChart render
  |
  +-- Cache HIT, data FRESH (within 5 seconds)
  |     |
  |     v
  |   isLoading = false, data = cached Stats
  |   Component renders immediately with cached data
  |   NO network request
  |
  +-- Cache HIT, data STALE (after 5 seconds)
        |
        v
      isLoading = false, data = cached (stale) Stats
      Component renders immediately with stale data
        |
        v
      Background: React Query calls getStats() again
        |
        v
      When fresh data arrives:
        - Cache updated
        - Component silently re-renders with new data
        - User sees no loading state
```

This "stale-while-revalidate" strategy is the key insight of React Query. The user always sees something (cached data), and fresh data replaces it seamlessly in the background.

---

## 9. React Query States

Every `useQuery` call returns an object with several state properties. Understanding the lifecycle helps you write correct loading and error UI.

### The State Properties

| Property | Type | When it is `true` |
|---|---|---|
| `isLoading` | boolean | First fetch in progress, no cached data exists |
| `isFetching` | boolean | Any fetch in progress (including background refetches) |
| `isError` | boolean | The most recent fetch failed |
| `isSuccess` | boolean | Data has been fetched successfully at least once |
| `isPending` | boolean | No data yet (alias for `isLoading` in v5) |

### The Data Properties

| Property | Type | Description |
|---|---|---|
| `data` | `T \| undefined` | The cached data (may be stale while refetching) |
| `error` | `Error \| null` | The error object if the fetch failed |
| `status` | `"pending" \| "error" \| "success"` | String version of the state |
| `fetchStatus` | `"fetching" \| "paused" \| "idle"` | Whether a fetch is in progress |

### The Lifecycle

Here is how the states transition over time:

```
Component mounts, no cache
  status:      "pending"
  isLoading:   true
  isFetching:  true
  data:        undefined

First fetch succeeds
  status:      "success"
  isLoading:   false
  isFetching:  false
  data:        { total_leads: 42, ... }

5 seconds pass (staleTime expires), component re-renders
  status:      "success"    (still success -- we have data)
  isLoading:   false        (still false -- we have cached data)
  isFetching:  true         (true -- background refetch started)
  data:        { total_leads: 42, ... }  (stale data shown)

Background refetch completes
  status:      "success"
  isLoading:   false
  isFetching:  false
  data:        { total_leads: 45, ... }  (fresh data)
```

### The Critical Distinction: isLoading vs isFetching

- **`isLoading`** is `true` only when there is no cached data at all. Use this for full-page loading spinners (the "first paint" loading state).
- **`isFetching`** is `true` whenever a network request is in progress, even if cached data is being shown. Use this for subtle indicators (like a small spinner in the corner, or a fading effect on the data).

In our homepage, we use `isLoading` for the full-page spinner. We do not use `isFetching` because we do not show any indicator during background refetches -- the stale data is good enough to display while fresh data loads silently.

### Error Handling

If a fetch fails, React Query retries 3 times by default (with exponential backoff). If all retries fail:

```tsx
const { data, error, isError } = useQuery({
  queryKey: ["stats"],
  queryFn: getStats,
});

if (isError) {
  return <p>Error loading stats: {error.message}</p>;
}
```

The `error` object is the `Error` thrown by `fetchJson`. Its `message` property contains either the backend's error detail or the HTTP status code, depending on what `fetchJson` extracted from the response.

---

## Key Takeaway Summary

1. **React Query separates data fetching concerns from UI rendering.** Your components declare what data they need (`queryKey` + `queryFn`), and React Query handles the how -- caching, deduplication, background updates, retries, polling, and error recovery.

2. **`useQuery` replaces half a dozen `useState` + `useEffect` calls** with a single hook that returns `data`, `isLoading`, `isError`, and more. The result is less code, fewer bugs, and automatic cache management.

3. **Query keys are the cache identity.** Two components with the same key share the same cached data and the same network request. Keys with parameters (like `["leads", { page: 1 }]`) create separate cache entries, enabling instant back-navigation.

4. **The API client layer wraps `fetch()` with type safety and error handling.** The `fetchJson<T>` generic function provides a single point for setting default headers, parsing errors, and casting response types. Specific functions like `getStats()` and `getLeads()` add endpoint-specific URL construction and parameter building.

5. **Stale-while-revalidate is the core strategy.** Users see cached data immediately while fresh data loads in the background. This eliminates most loading spinners after the first visit and makes the app feel instant.

6. **Manual refetch and cache invalidation give you control when automatic behavior is not enough.** After a mutation (like starting the pipeline), you can force a refetch or invalidate related cache entries so the UI reflects the change immediately.
