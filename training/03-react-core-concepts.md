# React Core Concepts

> **Document 3 of 10** -- Previous: 01 (JavaScript) and 02 (TypeScript). This document assumes you have read those and now understand JS/TS syntax, but have never seen React or JSX.

---

## 1. What Is React?

React is a JavaScript library for building user interfaces. It was created by Facebook (now Meta) and is the most widely used frontend framework in the world.

If you have used C# WPF, Blazor, or Python Tkinter, the core idea will feel familiar: you build your UI out of **components** -- self-contained, reusable pieces that each manage a portion of the screen.

### Declarative vs. Imperative

There are two fundamentally different approaches to building a UI:

**Imperative** (C# WinForms, Python Tkinter without abstractions):

You write step-by-step instructions telling the computer *how* to update the screen.

```csharp
// C# WinForms -- imperative
var label = new Label();
label.Text = "Loading...";
panel.Controls.Add(label);
// Later:
label.Text = "Done!";
```

You manually create elements, manually set their properties, and manually update them when data changes.

**Declarative** (React, C# WPF XAML, Blazor):

You describe *what* the UI should look like for a given state, and the framework figures out how to make the screen match.

```tsx
// React -- declarative
function Status({ isLoading }: { isLoading: boolean }) {
  return <p>{isLoading ? "Loading..." : "Done!"}</p>;
}
```

You never tell React "find the paragraph and change its text." You just say "when `isLoading` is true, the paragraph says Loading; otherwise it says Done." React compares the previous output to the new output and updates only the parts of the page (the DOM) that actually changed. This diffing process is called **reconciliation**.

If you have written WPF XAML, this model is very similar -- you bind your UI to data, and the framework handles updates. React takes the same philosophy but uses JavaScript functions instead of XML markup.

---

## 2. Components

A React component is a **function that returns JSX** (HTML-like syntax that we will cover in detail in Section 3). That is it. There is no base class to inherit from, no interface to implement, no decorator to attach. Just a function.

Here is the simplest component in this project -- the `AppShell`, which provides the outer layout for every page:

```tsx
// frontend/components/app-shell.tsx

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

Let us walk through every line.

### Line 1: `import type { ReactNode } from "react";`

This imports a TypeScript type called `ReactNode` from the React library. `ReactNode` means "anything React knows how to render" -- a string, a number, a JSX element, an array of those things, or `null`. The `type` keyword tells the bundler this is a type-only import (covered in doc 02) and can be erased at build time.

### Line 2: `import { NavSidebar } from "./nav-sidebar";`

This imports the `NavSidebar` component from a neighboring file. In React, each component is typically one file, and you import/export them with standard ES module syntax (covered in doc 01).

### Line 4: `export function AppShell({ children }: { children: ReactNode }) {`

This is a function named `AppShell`. In React, any function whose name starts with a capital letter and returns JSX is a component. The function takes a single argument: an object of **props** (properties). Here, we are using destructuring (from doc 01) to pull out a single prop called `children`.

The type annotation `{ children: ReactNode }` is an inline TypeScript interface saying "this object has one property named `children` whose type is `ReactNode`."

**C# analogy:** `children` is like the `Content` property on a WPF `ContentControl`. Whatever you place *inside* the `<AppShell>` tags becomes the `children` prop. In Blazor, this is the `@ChildContent` render fragment.

### Lines 5-14: The Return Statement (JSX)

The function returns JSX -- the HTML-like syntax surrounded by parentheses. Everything between `return (` and `)` describes what this component should render. We will cover JSX syntax in detail in Section 3, but a few things to notice now:

- `<div className="...">` -- this creates an HTML `<div>` element. `className` is used instead of `class` (explained in Section 3).
- `<NavSidebar />` -- this renders another React component. It looks like a self-closing HTML tag. React sees the capital letter and knows this is a component, not an HTML element.
- `{children}` -- the curly braces mean "insert this JavaScript value here." Whatever was placed inside the `<AppShell>` tags in the parent component gets rendered in this spot.

**C# analogy:** Think of this like a WPF `UserControl` with a `ContentPresenter`. The `<NavSidebar />` is a fixed part of the layout (the sidebar), and `{children}` is the content area that changes per page. In Python terms, it is like a Tkinter `Frame` that contains a fixed sidebar widget and a content area where you pack different widgets depending on the screen.

### How AppShell Gets Used

In the dashboard page (`frontend/app/page.tsx`), you see:

```tsx
return (
  <AppShell>
    <div className="space-y-8">
      <h1>Dashboard</h1>
      <StatsCards stats={stats} />
      {/* ...more content... */}
    </div>
  </AppShell>
);
```

Everything between `<AppShell>` and `</AppShell>` -- that entire `<div>` with the heading and stats cards -- becomes the `children` prop that `AppShell` renders inside its `<main>` area.

---

## 3. JSX -- The Template Language

JSX stands for JavaScript XML. It is a syntax extension that lets you write HTML-like markup directly inside JavaScript. It is not HTML -- your build tool (in this project, Next.js using a compiler) transforms it into JavaScript function calls before the browser sees it.

When you write:

```tsx
<div className="container">
  <h1>Hello</h1>
</div>
```

The compiler transforms it into something like:

```js
React.createElement("div", { className: "container" },
  React.createElement("h1", null, "Hello")
);
```

You never write those `createElement` calls by hand. JSX exists so you can think in terms of HTML structure. But understanding the transformation helps you see that JSX is just JavaScript -- which is why you can use it inside `if` statements, assign it to variables, return it from functions, and pass it as arguments.

### Key Differences from HTML

If you know HTML, JSX will look almost identical, but there are important differences:

| HTML | JSX | Why |
|------|-----|-----|
| `class="..."` | `className="..."` | `class` is a reserved word in JavaScript |
| `for="..."` | `htmlFor="..."` | `for` is a reserved word in JavaScript (the loop) |
| `onclick="..."` | `onClick={...}` | All event handlers use camelCase |
| `tabindex="0"` | `tabIndex={0}` | All attributes use camelCase |
| `<img>` | `<img />` | All tags must be explicitly closed (self-closing or with a closing tag) |
| `<br>` | `<br />` | Same rule -- self-closing required |
| `style="color: red"` | `style={{ color: "red" }}` | `style` takes a JavaScript object, not a CSS string |
| `<!-- comment -->` | `{/* comment */}` | JSX comments use JavaScript block comment syntax inside curly braces |

### Curly Braces: The Escape Hatch into JavaScript

Inside JSX, curly braces `{ }` mean "evaluate this as a JavaScript expression and insert the result." This is how you embed dynamic content.

**Inserting a value:**

```tsx
// From frontend/app/page.tsx
<p className="text-3xl font-bold tracking-tight">{value}</p>
```

The variable `value` is evaluated and its content is rendered as text inside the `<p>` tag.

**C# Razor analogy:** `@variable` or `@Model.Property`
**Python Jinja2 analogy:** `{{ variable }}`

**Conditional rendering (ternary):**

```tsx
// From frontend/app/page.tsx -- the pipeline run button
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

This is a JavaScript ternary expression (covered in doc 01) inside JSX. If `pipelineStatus?.running` is truthy, it renders a spinner icon with the text "Running...". Otherwise, it renders a play icon with "Run Pipeline."

**C# Razor analogy:** `@if (condition) { <div>A</div> } else { <div>B</div> }`

**Rendering a list:**

```tsx
// From frontend/components/nav-sidebar.tsx
{navItems.map((item) => {
  const Icon = item.icon;
  return (
    <Link key={item.href} href={item.href}>
      <Icon className="h-4 w-4" />
      {item.label}
    </Link>
  );
})}
```

The `.map()` array method (covered in doc 01) transforms an array of data into an array of JSX elements. React knows how to render arrays. The `key` prop is required and is explained in Section 8.

**C# analogy:** `@foreach (var item in items) { <div>@item.Name</div> }`
**Python Jinja2 analogy:** `{% for item in items %} <div>{{ item.name }}</div> {% endfor %}`

### What Can Go Inside Curly Braces

Any JavaScript **expression** (something that produces a value). You cannot put statements like `if`, `for`, `while`, or variable declarations directly in curly braces. This is why you use:

- Ternary `? :` instead of `if/else`
- `.map()` instead of `for` loops
- `&&` for "show this or nothing" (explained in Section 7)

---

## 4. Props (Properties)

Props are how you pass data **down** from a parent component to a child component. They are analogous to constructor parameters in C# or Python, or to attributes on an HTML element.

Here is a real example from the project:

```tsx
// frontend/components/stats-cards.tsx

interface StatsCardsProps {
  stats: Stats;
}

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* ...renders stats cards using the stats object... */}
    </div>
  );
}
```

And from the parent (`frontend/app/page.tsx`):

```tsx
<StatsCards stats={stats} />
```

Let us break this down:

1. **`interface StatsCardsProps`** -- A TypeScript interface defining the shape of the props this component accepts. It says: "this component expects one prop called `stats` of type `Stats`." This is like a C# class with public properties that serves as the "contract" for what data the component needs.

2. **`{ stats }: StatsCardsProps`** -- Destructuring the props object to pull out `stats`. Without destructuring, it would be:

   ```tsx
   export function StatsCards(props: StatsCardsProps) {
     const stats = props.stats;
     // ...
   }
   ```

   Both forms are equivalent. Destructuring is the convention in React.

3. **`<StatsCards stats={stats} />`** -- The parent passes data by writing it as an attribute. The curly braces mean "this is a JavaScript expression" (the variable `stats`), not a string literal.

### Props Are Read-Only

A component must never modify its own props. If `StatsCards` receives `stats`, it can read `stats.total_leads` but must never do `stats.total_leads = 42`. Props flow in one direction only: parent to child.

**C# analogy:** Props are like `readonly` fields set through a constructor, or like a ViewModel passed to a UserControl. The control can read the ViewModel but does not own it.

**Python analogy:** Think of props like arguments to a function. The function can use them but should not mutate them.

### Another Example: Chart Components with Optional Props

The chart components in this project show a more complex prop definition:

```tsx
// frontend/components/charts.tsx

interface TypeChartProps {
  data: Record<string, number>;
  onSegmentClick?: (filterKey: string, filterValue: string) => void;
}

export function TypePieChart({ data, onSegmentClick }: TypeChartProps) {
  // ...
}
```

Here, `data` is required and `onSegmentClick` is optional (the `?` makes it optional). `onSegmentClick` is a callback function -- a way for the child to communicate back up to the parent. This pattern is explained more in Section 9.

**Used in the dashboard:**

```tsx
<TypePieChart data={stats.by_type} />
```

Since `onSegmentClick` is optional, the dashboard omits it and the chart uses its default behavior (navigating to the leads page).

---

## 5. The `children` Prop

`children` is a special prop in React. Whatever you place between a component's opening and closing tags automatically becomes the `children` prop.

```tsx
<AppShell>
  <div>This entire div becomes the "children" prop of AppShell</div>
</AppShell>
```

This is equivalent to:

```tsx
<AppShell children={<div>This entire div becomes the "children" prop of AppShell</div>} />
```

But no one writes it the second way. The tag syntax is cleaner and is the universal convention.

`children` can be anything React can render:

- A string: `<Button>Click me</Button>`
- An element: `<AppShell><div>...</div></AppShell>`
- Multiple elements: `<AppShell><Header /><Content /></AppShell>`
- Nothing: `<NavSidebar />` (self-closing, no children)
- A mix: `<Button><Icon /> Click me</Button>`

The TypeScript type for `children` is `ReactNode`, which is a union type covering all of those possibilities.

**C# WPF analogy:** This is exactly like `ContentPresenter` in a `ContentControl`. When you write:

```xml
<MyUserControl>
  <TextBlock>Hello</TextBlock>
</MyUserControl>
```

The `TextBlock` becomes the content that `ContentPresenter` renders. React's `{children}` serves the same role.

**Blazor analogy:** The `@ChildContent` render fragment parameter.

---

## 6. React Hooks

Hooks are special functions provided by React that let your components have **state** (data that changes over time) and **side effects** (actions like fetching data, setting timers, or interacting with browser APIs).

Before hooks existed (pre-2019), you had to use classes to have state. Hooks let you do everything with plain functions.

### The Two Rules of Hooks

These rules are enforced by the React linter and violating them causes bugs:

1. **Only call hooks at the top level of your component.** Never inside `if` statements, `for` loops, `while` loops, or nested functions. React tracks hooks by the *order* they are called. If the order changes between renders, React gets confused.

   ```tsx
   // WRONG -- hook inside a condition
   function BadComponent({ showName }: { showName: boolean }) {
     if (showName) {
       const [name, setName] = useState("");  // React cannot track this reliably
     }
   }

   // RIGHT -- hook at the top, condition inside the JSX
   function GoodComponent({ showName }: { showName: boolean }) {
     const [name, setName] = useState("");
     return showName ? <p>{name}</p> : null;
   }
   ```

2. **Only call hooks inside React components or custom hooks.** You cannot call `useState` in a regular utility function.

### `useState` -- Managing Local State

`useState` is the most fundamental hook. It gives your component a piece of state that persists between renders and triggers a re-render when updated.

```tsx
const [mounted, setMounted] = useState(false);
```

This single line does a lot. Let us unpack it:

- `useState(false)` -- Creates a state variable with an initial value of `false`.
- It returns an array with exactly two elements: the current value and a function to update it.
- `[mounted, setMounted]` -- Array destructuring (from doc 01) assigns names to those two elements.
  - `mounted` -- the current value. On the first render, it is `false`.
  - `setMounted` -- a function you call to update the value. When you call `setMounted(true)`, React sets the value to `true` and **re-renders the component** -- meaning it calls your component function again, and this time `mounted` will be `true`.

The naming convention is always `[thing, setThing]`.

**C# analogy:** This is like a property with `INotifyPropertyChanged` in WPF/MVVM:

```csharp
// C# equivalent concept
private bool _mounted = false;
public bool Mounted
{
    get => _mounted;
    set
    {
        _mounted = value;
        OnPropertyChanged();  // This triggers the UI to update
    }
}
```

In C#, calling `OnPropertyChanged()` tells WPF to re-read the property and update any bound UI elements. In React, calling `setMounted(true)` tells React to re-run the component function and update the DOM with the new output.

**Python analogy:** There is no direct equivalent in standard Python. The closest would be a Tkinter `StringVar` or `IntVar`:

```python
# Python Tkinter
name_var = tk.StringVar(value="")
name_var.set("Alice")  # Updates any widgets bound to this variable
```

**Real example from `frontend/components/nav-sidebar.tsx`:**

```tsx
const [mounted, setMounted] = useState(false);
```

This state variable tracks whether the component has finished its first render in the browser. It starts as `false` and gets set to `true` inside a `useEffect` (covered next). This pattern exists because of server-side rendering in Next.js -- the component first renders on the server (where there is no browser), and `mounted` stays `false` until the browser takes over. This prevents the theme toggle from flickering because the server does not know which theme the user prefers.

### `useEffect` -- Side Effects

`useEffect` lets you run code **after** React has rendered your component to the screen. It is for "side effects" -- things that happen outside of rendering, like:

- Fetching data from an API
- Setting up event listeners
- Starting timers
- Interacting with browser APIs (localStorage, document.title, etc.)

```tsx
useEffect(() => {
  setMounted(true);
}, []);
```

This has two parts:

1. **The effect function** `() => { setMounted(true); }` -- the code to run.
2. **The dependency array** `[]` -- controls *when* the effect runs.

#### The Dependency Array

The second argument to `useEffect` is critical:

| Dependency Array | When the Effect Runs | Analogy |
|---|---|---|
| `[]` (empty array) | Once, after the first render | C# `OnInitialized()` in Blazor, `Loaded` event in WPF, Python `__init__` |
| `[count]` | After the first render, and again whenever `count` changes | C# property change handler -- code that runs when a specific value updates |
| `[a, b]` | After the first render, and again whenever `a` or `b` changes | Same, but watching multiple values |
| *(omitted entirely)* | After every single render | Rarely wanted. Equivalent to running code on every PropertyChanged event regardless of which property changed |

**Real example from `frontend/components/nav-sidebar.tsx`:**

```tsx
const [mounted, setMounted] = useState(false);

useEffect(() => setMounted(true), []);
```

The empty dependency array `[]` means this runs exactly once, right after the component first appears on screen. It sets `mounted` to `true`, which triggers a re-render. Now the component knows it is running in the browser and can safely read the theme.

**C# analogy:**

```csharp
// Blazor
protected override void OnAfterRender(bool firstRender)
{
    if (firstRender)
    {
        _mounted = true;
        StateHasChanged();
    }
}
```

#### Cleanup Functions

`useEffect` can return a function that React calls when the component is removed from the screen (unmounted) or before re-running the effect. This is for cleanup -- removing event listeners, canceling timers, etc.

```tsx
useEffect(() => {
  const timer = setInterval(() => console.log("tick"), 1000);
  return () => clearInterval(timer);  // Cleanup: stop the timer
}, []);
```

**C# analogy:** Like implementing `IDisposable`. The cleanup function is your `Dispose()` method.

### `useQuery` -- Data Fetching (Brief Introduction)

This project uses React Query (TanStack Query), which provides the `useQuery` hook. Detailed coverage is in document 06, but since it appears frequently, here is the essential pattern:

```tsx
// From frontend/app/page.tsx
const { data: stats, isLoading } = useQuery({
  queryKey: ["stats"],
  queryFn: getStats,
});
```

- `queryKey: ["stats"]` -- A unique identifier for this query. React Query uses it for caching and deduplication.
- `queryFn: getStats` -- The function that fetches the data (defined in `frontend/lib/api.ts`).
- `data: stats` -- The fetched data (renamed from `data` to `stats` via destructuring).
- `isLoading` -- A boolean that is `true` while the first fetch is in progress.

Think of `useQuery` as a `useState` + `useEffect` combination that handles loading states, error states, caching, background refetching, and retry logic for you. Without it, you would write:

```tsx
// What you'd have to write without React Query:
const [stats, setStats] = useState<Stats | null>(null);
const [isLoading, setIsLoading] = useState(true);

useEffect(() => {
  getStats()
    .then(data => setStats(data))
    .finally(() => setIsLoading(false));
}, []);
```

React Query eliminates this boilerplate and adds many features on top.

---

## 7. Conditional Rendering

React does not have a special `if` directive like C# Razor (`@if`) or Vue (`v-if`). Instead, you use standard JavaScript expressions inside JSX. There are three common patterns, and this project uses all three.

### Pattern 1: Ternary Operator -- Show A or B

Use when you have two different things to render based on a condition.

```tsx
// From frontend/app/page.tsx -- the Run Pipeline button
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

**How to read this:**

- `pipelineStatus?.running` -- Is the pipeline currently running? (The `?.` is optional chaining from doc 01 -- if `pipelineStatus` is null/undefined, the whole expression is `undefined` rather than throwing an error.)
- If yes (`?`): render a spinning loader icon and the text "Running..."
- If no (`:`): render a play icon and the text "Run Pipeline"

**C# Razor equivalent:**

```csharp
@if (pipelineStatus?.Running == true)
{
    <Loader2 /> Running...
}
else
{
    <Play /> Run Pipeline
}
```

### Pattern 2: Logical AND (`&&`) -- Show or Nothing

Use when you want to render something OR render nothing at all.

```tsx
// From frontend/app/page.tsx
{duplicatesData && duplicatesData.count > 0 && (
  <Card className="border-warning/20">
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-base">
        Potential Duplicates
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-3xl font-bold tracking-tight">
        {duplicatesData.count}
      </p>
      <p className="text-sm text-muted-foreground mb-4">
        leads to review and merge
      </p>
    </CardContent>
  </Card>
)}
```

**How this works:**

JavaScript's `&&` operator short-circuits. If the left side is falsy, it returns the left side and never evaluates the right side. If the left side is truthy, it returns the right side.

- `duplicatesData && duplicatesData.count > 0` -- First, check if `duplicatesData` exists. If not, stop (render nothing). Then check if `count > 0`. If not, stop.
- If both conditions are true, the `&&` evaluates the JSX on the right side, and that Card gets rendered.
- If either condition is false, React receives `false` or `null` and renders nothing.

**C# Razor equivalent:**

```csharp
@if (duplicatesData != null && duplicatesData.Count > 0)
{
    <Card>...</Card>
}
```

Another example from nav-sidebar.tsx showing nested conditional rendering:

```tsx
{isActive && (
  <div className="ml-auto h-1.5 w-1.5 rounded-full bg-white/70" />
)}
```

If the nav item is the currently active page, render a small dot indicator. Otherwise, render nothing.

### Pattern 3: Early Return -- Bail Out Entirely

Use when the component cannot render its main content yet (data not loaded, error state, etc.).

```tsx
// From frontend/app/page.tsx
if (isLoading || !stats) {
  return (
    <AppShell>
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    </AppShell>
  );
}

// Everything below this line only runs when stats is loaded
return (
  <AppShell>
    <div className="space-y-8">
      <StatsCards stats={stats} />
      {/* ...rest of the dashboard... */}
    </div>
  </AppShell>
);
```

This is a regular JavaScript `if` statement (not inside JSX). Because it comes before the main `return`, the component returns early with a loading spinner and never reaches the dashboard code. This eliminates the need to pepper `isLoading` checks throughout the rest of the component.

**C# analogy:** Guard clauses in a method:

```csharp
if (stats == null) return new LoadingView();
// Main logic proceeds knowing stats is not null
```

An important benefit: after the early return, TypeScript knows that `stats` is not `null` or `undefined`. This is called type narrowing (from doc 02). You can use `stats.total_leads` without any `?.` optional chaining because TypeScript has eliminated the `null` possibility.

---

## 8. Rendering Lists

To render a list of items in React, you use the `.map()` array method (from doc 01) to transform each data item into a JSX element.

Here is the full real example from `frontend/components/stats-cards.tsx`:

```tsx
const statConfig = [
  {
    key: "total_leads" as const,
    label: "Total Leads",
    icon: Users,
    gradient: "from-blue-500/20 to-indigo-500/20",
    iconColor: "text-blue-400",
    getValue: (stats: Stats) => stats.total_leads,
  },
  {
    key: "avg_score" as const,
    label: "Avg Score",
    icon: Target,
    gradient: "from-purple-500/20 to-pink-500/20",
    iconColor: "text-purple-400",
    getValue: (stats: Stats) => stats.avg_score.toFixed(1),
  },
  // ...two more entries...
];

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {statConfig.map((stat) => {
        const Icon = stat.icon;
        const value = stat.getValue(stats);
        return (
          <div
            key={stat.key}
            className="glass glow-hover rounded-xl p-5 transition-all duration-300 animate-slide-in"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </p>
              <div className={`h-9 w-9 rounded-lg bg-gradient-to-br ${stat.gradient} flex items-center justify-center`}>
                <Icon className={`h-4.5 w-4.5 ${stat.iconColor}`} />
              </div>
            </div>
            <div className="mt-3">
              <p className="text-3xl font-bold tracking-tight">{value}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

Let us trace through what happens:

1. `statConfig` is an array of four objects, each describing one stats card.
2. `statConfig.map((stat) => { ... })` iterates over the array. For each object, the arrow function runs and returns a JSX element.
3. The result is an array of four `<div>` elements. React renders all of them inside the parent grid `<div>`.

### The `key` Prop

Every element in a list **must** have a `key` prop:

```tsx
<div key={stat.key} className="...">
```

The `key` is a unique string or number that helps React identify which items have changed, been added, or been removed between renders. Without keys, React would have to re-render every item in the list whenever the list changes. With keys, React can match old items to new items and only update what actually changed.

**C# analogy:** Like a `DataTemplate` with a unique `DataContext` identifier, or like setting `x:Key` in a WPF `ResourceDictionary` so WPF can track and recycle elements efficiently.

**Critical rule: never use the array index as a key if items can be reordered, inserted, or deleted.** Using the index means that if you insert an item at the beginning of the list, every item's key changes (item 0 becomes item 1, etc.), and React thinks every item is different. Always use a stable identifier from your data -- an `id`, a unique `key` field, an `href`, etc.

```tsx
// GOOD: stable, unique identifier
{navItems.map((item) => (
  <Link key={item.href} href={item.href}>{item.label}</Link>
))}

// BAD: index changes when items are reordered
{navItems.map((item, index) => (
  <Link key={index} href={item.href}>{item.label}</Link>
))}
```

### Dynamic Components

Notice this pattern in the stats cards example:

```tsx
const Icon = stat.icon;
// ...
<Icon className="h-4.5 w-4.5" />
```

`stat.icon` holds a reference to a React component (like `Users` or `Target` from the Lucide icon library). By assigning it to a variable that starts with a capital letter (`Icon`), we can use it in JSX like any other component. If the variable name started with a lowercase letter, React would treat it as an HTML element instead of a component.

---

## 9. Event Handling

React event handling is similar to C# event handlers or Python callback binding, but with a simpler syntax.

Here is the real example from `frontend/app/page.tsx`:

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

// In the JSX:
<Button onClick={handleRunPipeline}>Run Pipeline</Button>
```

### How It Works

1. **Define the handler function.** `handleRunPipeline` is an `async` arrow function (from doc 01) that calls the API, shows a success toast notification, and refreshes the pipeline status. If anything fails, it shows an error toast.

2. **Attach it to an element with an event prop.** `onClick={handleRunPipeline}` tells React: "when this button is clicked, call this function."

### Important: Pass the Function Reference, Do Not Call It

```tsx
// CORRECT: pass the function (no parentheses)
<Button onClick={handleRunPipeline}>

// WRONG: this CALLS the function immediately during rendering
<Button onClick={handleRunPipeline()}>
```

`handleRunPipeline` (no parentheses) is a reference to the function -- "here is the function, call it later when the button is clicked."

`handleRunPipeline()` (with parentheses) calls the function *right now* and passes its *return value* to `onClick`. This is almost never what you want.

**C# analogy:**

```csharp
// C# event handler -- you also pass the method reference, not a call
button.Click += HandleRunPipeline;   // Correct -- method reference
button.Click += HandleRunPipeline(); // Wrong -- this calls the method
```

**Python analogy:**

```python
# Python Tkinter -- same pattern
button.config(command=handle_run_pipeline)        # Correct -- function reference
button.config(command=handle_run_pipeline())      # Wrong -- calls the function
```

### Inline Event Handlers

For simple handlers, you can define the function inline:

```tsx
// From frontend/components/nav-sidebar.tsx
<button
  onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
>
```

The arrow function `() => setTheme(...)` creates an anonymous function that gets called when the button is clicked. This is fine for simple one-liners. For anything more complex (like the pipeline handler with try/catch), define a named function above the JSX for readability.

### Events React Supports

React normalizes browser events across all browsers. Common event props:

| Event Prop | Fires When |
|---|---|
| `onClick` | Element is clicked |
| `onChange` | Input/select value changes |
| `onSubmit` | Form is submitted |
| `onKeyDown` | Key is pressed |
| `onMouseEnter` | Mouse enters the element |
| `onFocus` | Element receives focus |
| `onBlur` | Element loses focus |

All follow the pattern: `on` + event name in camelCase.

---

## 10. Fragments

Sometimes you need to return multiple elements from a component or a conditional block, but you do not want to add an extra wrapper `<div>` to the DOM. Fragments solve this.

```tsx
// From frontend/app/page.tsx -- inside the pipeline button
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

`<>` and `</>` are the shorthand syntax for a Fragment. They group multiple elements together without adding any HTML element to the page. Without the fragment, you would get an error because JSX expressions must have a single root element.

The long form is `<React.Fragment>` and `</React.Fragment>`, but the shorthand is used almost universally.

**When to use Fragments:**

- Returning multiple elements side by side (an icon and text, as above)
- Avoiding unnecessary wrapper divs that would break CSS layouts
- Rendering adjacent table rows, list items, or other elements where an extra wrapper div would be invalid HTML (e.g., `<tr>` must be a direct child of `<tbody>`)

---

## 11. Component Composition Pattern

React applications are built by composing small components into larger ones, forming a tree structure. Here is the actual component hierarchy for the dashboard page of this project:

```
DashboardPage (frontend/app/page.tsx)
  |
  +-- AppShell (frontend/components/app-shell.tsx)
  |     |
  |     +-- NavSidebar (frontend/components/nav-sidebar.tsx)
  |     |     |
  |     |     +-- Link (one per navItem, from next/link)
  |     |     +-- Theme toggle button
  |     |
  |     +-- <main> content area (children)
  |           |
  |           +-- Header section (h1, p, Button)
  |           +-- StatsCards (frontend/components/stats-cards.tsx)
  |           |     +-- Four stat card divs (rendered via .map())
  |           +-- Chart grid
  |           |     +-- TypePieChart (frontend/components/charts.tsx)
  |           |     +-- CountyBarChart (frontend/components/charts.tsx)
  |           |     +-- StageBarChart (frontend/components/charts.tsx)
  |           +-- Alert cards (duplicates, last run)
```

### Key Principles

**Data flows down.** The `DashboardPage` fetches `stats` from the API and passes it down to `StatsCards` and the chart components via props. Child components never reach up to grab data from a parent.

**Events flow up.** If a child needs to tell the parent something happened, the parent passes a callback function as a prop. For example, `TypeChartProps` accepts an optional `onSegmentClick` prop:

```tsx
interface TypeChartProps {
  data: Record<string, number>;
  onSegmentClick?: (filterKey: string, filterValue: string) => void;
}
```

The parent decides what happens when a chart segment is clicked. The child just calls the function.

**Each component has a single responsibility.**

- `AppShell` handles the overall page layout (sidebar + content area).
- `NavSidebar` handles navigation links and the theme toggle.
- `StatsCards` handles rendering the four stat cards.
- `TypePieChart` handles rendering a pie chart.
- `DashboardPage` orchestrates everything: fetching data, handling the pipeline trigger, and composing the child components.

**C# analogy:** This is like building a WPF application with UserControls. You have a `MainWindow` (AppShell), a `NavigationPanel` UserControl (NavSidebar), and various content UserControls (StatsCards, charts). The MainWindow's DataContext flows down to child controls via bindings.

**Python analogy:** Like a Tkinter application with `Frame` widgets. A main `Frame` contains a sidebar `Frame` and a content `Frame`, and each sub-frame manages its own widgets.

---

## 12. The `"use client"` Directive

You will see this line at the top of many files in this project:

```tsx
"use client";
```

This is a **Next.js directive** (not a React feature). It tells Next.js that this file is a **Client Component** -- it runs in the user's browser.

By default, Next.js treats components as **Server Components** -- they run on the server, generate HTML, and send it to the browser. Server Components cannot use hooks (`useState`, `useEffect`, `useQuery`) or browser APIs (`window`, `document`, `localStorage`).

You must add `"use client"` to any file that:

- Uses `useState`, `useEffect`, or any other React hook
- Uses `useQuery` from React Query
- Uses browser-specific APIs
- Has interactive event handlers that modify state

In this project, most components are Client Components because they use React Query for data fetching or hooks for interactivity. The `AppShell` component (`frontend/components/app-shell.tsx`) does NOT have `"use client"` because it does not use any hooks -- it is a pure layout component that just receives `children` and renders them.

We will cover the Server Component vs. Client Component distinction in much more detail in the Next.js document (doc 05). For now, just remember: if a component needs hooks or interactivity, put `"use client"` at the very top of the file (before any imports).

---

## 13. Putting It All Together

Let us trace through the entire flow of the dashboard page to solidify all these concepts. Open `frontend/app/page.tsx` and follow along:

```tsx
"use client";
```
This is a Client Component because it uses hooks.

```tsx
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { StatsCards } from "@/components/stats-cards";
import { TypePieChart, CountyBarChart, StageBarChart } from "@/components/charts";
import { getStats, triggerPipelineRun, getPipelineStatus, getDuplicatesCount } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2, Play, Copy, ArrowRight, Clock, Zap, TrendingUp } from "lucide-react";
import Link from "next/link";
import { formatLocalDateTime } from "@/lib/utils";
```
Imports: React Query hook, our project components, API functions, UI library components, icons, and utilities. The `@/` prefix is a path alias meaning "the root of the frontend project" (configured in `tsconfig.json`).

```tsx
export default function DashboardPage() {
```
This is a component. `export default` makes it the default export of the file, which Next.js uses for page routing (covered in doc 05).

```tsx
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const { data: pipelineStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: getPipelineStatus,
    refetchInterval: (query) => {
      return query.state.data?.running ? 2000 : false;
    },
  });

  const { data: duplicatesData } = useQuery({
    queryKey: ["duplicatesCount"],
    queryFn: getDuplicatesCount,
  });
```
Three `useQuery` hooks at the top level (following the Rules of Hooks). Each fetches different data from the API. The pipeline status query has a special `refetchInterval` that polls every 2 seconds while the pipeline is running. These are hooks (Section 6) that handle data fetching (detailed in doc 06).

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
An event handler function (Section 9). Calls the API, shows a toast, and refreshes the pipeline status.

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
Early return pattern (Section 7, Pattern 3). If data is still loading, show a spinner and stop. The `AppShell` wrapping ensures the sidebar is still visible even while loading.

```tsx
  return (
    <AppShell>
      <div className="space-y-8">
```
Main render. The `AppShell` provides the layout (Section 2), and everything inside it becomes the `children` prop (Section 5).

```tsx
        <StatsCards stats={stats} />
```
Passing props (Section 4). The `stats` object fetched from the API is passed down to the `StatsCards` component, which renders the four stat cards using `.map()` (Section 8).

```tsx
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <TypePieChart data={stats.by_type} />
          <CountyBarChart data={stats.by_county} />
          <StageBarChart data={stats.by_stage} />
        </div>
```
Three chart components, each receiving a subset of the stats data as props. Component composition (Section 11) at work.

```tsx
        {duplicatesData && duplicatesData.count > 0 && (
          <Card>...</Card>
        )}
```
Conditional rendering with `&&` (Section 7, Pattern 2). The duplicates card only appears if there are duplicates.

```tsx
        {stats.last_run && (
          <Card>...</Card>
        )}
```
Another conditional render. The "Last Pipeline Run" card only appears if there has been at least one run.

Every concept from this document appears in this single 168-line file. That is typical of React -- a small number of core concepts combine in predictable ways to build arbitrarily complex UIs.

---

## Key Takeaway Summary

| Concept | One-Sentence Explanation | C# Equivalent |
|---|---|---|
| Component | A function that returns JSX describing what to render | WPF UserControl or Blazor component |
| JSX | HTML-like syntax embedded in JavaScript, compiled to function calls | XAML markup or Razor syntax |
| Props | Read-only data passed from parent to child | Constructor parameters or ViewModel binding |
| `children` | The special prop for content placed between component tags | ContentPresenter or @ChildContent |
| `useState` | Creates a reactive state variable that triggers re-renders when updated | Property with INotifyPropertyChanged |
| `useEffect` | Runs side-effect code after rendering, with dependency tracking | OnAfterRender or Loaded event |
| `useQuery` | Fetches and caches remote data with loading/error states (React Query) | HttpClient call + ObservableCollection |
| Conditional rendering | Use ternary (`? :`), AND (`&&`), or early return -- no special directives | @if in Razor |
| List rendering | Use `.map()` with a `key` prop -- no special loop syntax | @foreach with DataTemplate |
| Event handling | Pass function references to `onClick`, `onChange`, etc. | Button.Click += Handler |
| Fragments (`<> </>`) | Group elements without adding a wrapper div | No direct equivalent |
| `"use client"` | Marks a file as a Client Component (Next.js, not React) | No direct equivalent |

---

**Next up:** Document 04 covers **TypeScript in React** -- generics with components, type inference with hooks, discriminated unions for props, and the type patterns used throughout this project.
