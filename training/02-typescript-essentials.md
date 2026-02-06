# TypeScript Essentials for C# Developers

> **Document 2 of 10** -- Developer Training Guide
>
> **Prerequisite:** Document 01 (JavaScript Fundamentals)
>
> **Audience:** Developer experienced with C# and Python, new to JavaScript/TypeScript

---

## Table of Contents

1. [What is TypeScript?](#1-what-is-typescript)
2. [Basic Type Annotations](#2-basic-type-annotations)
3. [Interfaces](#3-interfaces)
4. [Type Aliases and Union Types](#4-type-aliases-and-union-types)
5. [Optional Properties](#5-optional-properties)
6. [Generic Types](#6-generic-types)
7. [Utility Types](#7-utility-types)
8. [Type Assertions (Casting)](#8-type-assertions-casting)
9. [Structural Typing vs Nominal Typing](#9-structural-typing-vs-nominal-typing)
10. [The `type` Keyword vs `interface`](#10-the-type-keyword-vs-interface)
11. [Importing Types](#11-importing-types)
12. [Constants with Type Safety](#12-constants-with-type-safety)
13. [Quick Reference Table](#13-quick-reference-table)

---

## 1. What is TypeScript?

TypeScript is a **superset of JavaScript** that adds static type checking. Every valid JavaScript program is also a valid TypeScript program, but TypeScript adds a type system on top that catches errors before your code runs.

### The Compilation Model

TypeScript compiles (or more precisely, *transpiles*) down to plain JavaScript. This is conceptually similar to how C# compiles to IL (Intermediate Language):

```
C#     (.cs)  -->  C# Compiler  -->  IL (.dll)         -->  CLR executes IL
TypeScript (.ts)  -->  tsc Compiler  -->  JavaScript (.js)  -->  Browser/Node executes JS
```

The key difference: when the C# compiler produces IL, it **preserves all type information**. The CLR knows at runtime that a variable is an `int` or a `List<string>`. You can use reflection, `typeof`, `is` checks, and `GetType()` because types are real, concrete things in the running program.

TypeScript is fundamentally different.

### Types are Erased at Runtime

This is the single most important thing to understand about TypeScript: **types exist only during development and compilation. They are completely removed from the output JavaScript.**

Consider this TypeScript:

```typescript
function greet(name: string): string {
  return `Hello, ${name}`;
}
const message: string = greet("Nashville");
```

After compilation, the output JavaScript is:

```javascript
function greet(name) {
  return `Hello, ${name}`;
}
const message = greet("Nashville");
```

Every type annotation is gone. The `: string` after `name`, the `: string` return type, the `: string` on `message` -- all stripped away. The JavaScript runtime has no idea these types ever existed.

This means:

- You **cannot** check a TypeScript interface at runtime (no `typeof MyInterface` or `instanceof MyInterface`).
- You **cannot** do reflection on TypeScript types.
- You **cannot** use TypeScript types in `if` statements, `switch` cases, or any runtime logic.
- The type system is a development-time safety net, not a runtime feature.

If you come from C# and find yourself wanting to write `if (obj is Lead)`, you will need to use a different approach -- typically checking for the presence of specific properties (a pattern called a "type guard").

### TypeScript in This Project

This project uses **TypeScript 5** (specified in `frontend/package.json` as `"typescript": "^5"`). All `.tsx` files contain TypeScript with JSX syntax (React markup). The TypeScript compiler configuration lives in `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true,
    "jsx": "preserve",
    "module": "esnext",
    "moduleResolution": "bundler",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

A few things to note:

- **`"strict": true`** enables all strict type-checking options. This is the TypeScript equivalent of treating all warnings as errors in C#. It catches the most bugs and is considered best practice.
- **`"noEmit": true`** means TypeScript only type-checks; it does not produce output files. Next.js handles the actual compilation via its own build pipeline.
- **`"jsx": "preserve"`** tells TypeScript to leave JSX syntax alone (Next.js transforms it later).
- **`"paths"`** defines the `@/` import alias, so `@/lib/types` resolves to `./lib/types` relative to the frontend root.

---

## 2. Basic Type Annotations

If you know C#, TypeScript's type annotations will feel instantly familiar. The syntax is slightly different -- TypeScript puts types *after* the identifier with a colon, whereas C# puts them *before*.

### Variable Annotations

```typescript
// TypeScript
const name: string = "Acme Restaurant";
const score: number = 85;
const isNew: boolean = true;
const notes: string | null = null;
```

```csharp
// C# equivalent
string name = "Acme Restaurant";
int score = 85;        // or double -- TypeScript has only "number" for all numeric types
bool isNew = true;
string? notes = null;
```

Notice that TypeScript has a single `number` type that covers what C# splits into `int`, `long`, `float`, `double`, `decimal`, etc. There is no distinction between integers and floating-point numbers at the type level.

### Function Annotations

```typescript
// TypeScript
function add(a: number, b: number): number {
  return a + b;
}

function formatLead(name: string, score: number): string {
  return `${name} (Score: ${score})`;
}
```

```csharp
// C# equivalent
int Add(int a, int b)
{
    return a + b;
}

string FormatLead(string name, int score)
{
    return $"{name} (Score: {score})";
}
```

The pattern is consistent: C# puts the type before the name (`int a`), TypeScript puts it after (`a: number`).

### Arrow Function Annotations

Since arrow functions are common in this project (covered in Document 01), here is how they get typed:

```typescript
// Arrow function with explicit types
const double = (n: number): number => n * 2;

// Arrow function as a callback parameter
const scores: number[] = [85, 72, 93, 61];
const highScores: number[] = scores.filter((s: number): boolean => s > 80);
```

### Type Inference

TypeScript can **infer types** from context, just like C#'s `var` keyword:

```typescript
// TypeScript infers the type -- you do NOT need to write it out
const name = "Acme Restaurant";   // TypeScript knows this is string
const score = 85;                  // TypeScript knows this is number
const isNew = true;                // TypeScript knows this is boolean
const scores = [85, 72, 93];      // TypeScript knows this is number[]
```

```csharp
// C# equivalent using var
var name = "Acme Restaurant";   // compiler knows this is string
var score = 85;                  // compiler knows this is int
var isNew = true;                // compiler knows this is bool
var scores = new[] { 85, 72, 93 }; // compiler knows this is int[]
```

In practice, you will see most code in this project **omit type annotations when inference is sufficient**. You write explicit types when:

- The type cannot be inferred (function parameters always need types).
- You want to document the intent (especially on exported functions).
- Inference would produce a wider type than you want (e.g., you want a specific union type, not just `string`).

```typescript
// Inference works perfectly here -- no annotation needed
const x = 5;

// But parameters MUST be annotated -- TypeScript cannot infer them
function add(a: number, b: number) {  // return type inferred as number
  return a + b;
}
```

### The `void` Return Type

Just like C#, TypeScript uses `void` for functions that do not return a value:

```typescript
// TypeScript
function logMessage(msg: string): void {
  console.log(msg);
}
```

```csharp
// C#
void LogMessage(string msg)
{
    Console.WriteLine(msg);
}
```

---

## 3. Interfaces

This is where TypeScript will feel most like home for a C# developer. The keyword is the same, the purpose is similar, but there is a crucial conceptual difference.

### TypeScript Interfaces Define Shape

Here is the real `Lead` interface from this project (`frontend/lib/types.ts`):

```typescript
export interface Lead {
  id: number;
  fingerprint: string;
  business_name: string;
  business_type: string | null;
  raw_type: string | null;
  address: string | null;
  city: string | null;
  state: string;
  zip_code: string | null;
  county: string | null;
  license_date: string | null;
  pos_score: number;
  stage: Stage;
  source_url: string | null;
  source_type: string | null;
  source_batch_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  contacted_at: string | null;
  closed_at: string | null;
}
```

This says: "Any object that has all these properties with these types counts as a `Lead`." It defines the **shape** of the data.

### How This Differs from C# Interfaces

In C#, an interface defines a **behavioral contract** -- a set of methods and properties that a class must implement. A class opts into the contract with explicit syntax:

```csharp
// C# interface -- defines behavior
public interface ILead
{
    int Id { get; }
    string BusinessName { get; }
    string GetDisplayName();
}

// A class must EXPLICITLY implement the interface
public class Lead : ILead
{
    public int Id { get; set; }
    public string BusinessName { get; set; }
    public string GetDisplayName() => $"{BusinessName} (#{Id})";
}
```

The closest C# equivalent to a TypeScript interface is actually a **record** or a **DTO class**:

```csharp
// C# record -- this is closer to what a TypeScript interface represents
public record Lead(
    int Id,
    string Fingerprint,
    string BusinessName,
    string? BusinessType,
    string? Address,
    string? City,
    string State,
    int PosScore,
    Stage Stage,
    string CreatedAt,
    string UpdatedAt
);
```

Both define the shape of data. The difference is that in C#, the `Lead` record is a concrete type with a name that matters. In TypeScript, the interface name is just a label for a shape -- any object with the right properties matches, regardless of where it came from (more on this in Section 9).

### Interfaces for Component Props

In React with TypeScript, interfaces are commonly used to define the "props" a component accepts. Here is a real example from this project (`frontend/components/stats-cards.tsx`):

```typescript
import type { Stats } from "@/lib/types";

interface StatsCardsProps {
  stats: Stats;
}

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div>
      <p>{stats.total_leads} total leads</p>
      <p>Average score: {stats.avg_score}</p>
    </div>
  );
}
```

The `StatsCardsProps` interface defines what data the `StatsCards` component expects to receive. TypeScript will error if you try to use `<StatsCards />` without passing a `stats` prop, or if the `stats` object does not match the `Stats` interface.

In C#, this is somewhat like defining a ViewModel:

```csharp
// C# ViewModel approach
public class StatsCardsViewModel
{
    public Stats Stats { get; set; }
}
```

### Interface Extension

TypeScript interfaces can extend other interfaces, similar to C# interface inheritance:

```typescript
// Base interface
interface Entity {
  id: number;
  created_at: string;
}

// Extended interface -- has everything Entity has plus more
interface Lead extends Entity {
  business_name: string;
  pos_score: number;
}

// A Lead must have id, created_at, business_name, AND pos_score
```

```csharp
// C# equivalent
public interface IEntity
{
    int Id { get; }
    string CreatedAt { get; }
}

public interface ILead : IEntity
{
    string BusinessName { get; }
    int PosScore { get; }
}
```

You can also extend multiple interfaces:

```typescript
interface Timestamped {
  created_at: string;
  updated_at: string;
}

interface Scoreable {
  pos_score: number;
}

// Combine multiple interfaces
interface Lead extends Timestamped, Scoreable {
  id: number;
  business_name: string;
}
```

---

## 4. Type Aliases and Union Types

### Type Aliases

The `type` keyword creates a **type alias** -- a name for any type expression. Here is the real `Stage` type from this project (`frontend/lib/types.ts`):

```typescript
export type Stage =
  | "New"
  | "Qualified"
  | "Contacted"
  | "Follow-up"
  | "Closed-Won"
  | "Closed-Lost";
```

This is a **string literal union type**. A variable of type `Stage` can only hold one of those six exact string values. If you try to assign `"Invalid"` to a `Stage` variable, TypeScript will flag it as an error at compile time.

The closest C# equivalent is an enum:

```csharp
// C# approach
public enum Stage
{
    New,
    Qualified,
    Contacted,
    FollowUp,
    ClosedWon,
    ClosedLost
}
```

The key differences:

| Aspect | C# Enum | TypeScript String Union |
|--------|---------|------------------------|
| Underlying value | Integer by default | The actual string |
| Serialization | Needs conversion to/from string | Already a string -- no conversion needed |
| Runtime existence | Yes, enum type exists at runtime | No, type is erased; it is just a string at runtime |
| Display value | Needs `.ToString()` or `[Description]` attribute | The string IS the display value |

The TypeScript approach is particularly nice for APIs because the JSON value `"Closed-Won"` is already the type-safe value. In C# you would need `[JsonConverter]` or similar to map between `"Closed-Won"` and `Stage.ClosedWon`.

Here is another real example from the project:

```typescript
export type BusinessType =
  | "restaurant"
  | "bar"
  | "retail"
  | "salon"
  | "cafe"
  | "bakery"
  | "gym"
  | "spa"
  | "other";
```

### Union Types

Union types use the pipe (`|`) to say "this value can be one of these types." You have already seen the simplest version in the `Stage` type above. Unions also work with broader types:

```typescript
// This value is either a string or null
const address: string | null = null;

// This value is either a number or null
const score: number | null = null;

// This value is either a string or a number
const id: string | number = "abc-123";
```

The `string | null` pattern is the TypeScript equivalent of C# nullable reference types:

```csharp
// C#
string? address = null;    // Nullable reference type (C# 8+)
int? score = null;         // Nullable value type
```

```typescript
// TypeScript
const address: string | null = null;
const score: number | null = null;
```

The `string | number` union has no direct C# equivalent. The closest approximation would be `object`, or in newer C# you might use a discriminated union pattern:

```csharp
// C# -- no clean equivalent
object id = "abc-123";  // Loses type safety

// Or a hand-rolled discriminated union
public abstract record IdValue;
public record StringId(string Value) : IdValue;
public record NumericId(int Value) : IdValue;
```

TypeScript makes this trivial. You will see union types used extensively in the real `Lead` interface where many fields are `string | null`:

```typescript
export interface Lead {
  id: number;                       // always present
  business_name: string;            // always present
  business_type: string | null;     // might be null
  address: string | null;           // might be null
  city: string | null;              // might be null
  pos_score: number;                // always present
  // ...
}
```

### Narrowing Unions

When you have a union type, TypeScript requires you to **narrow** it before using type-specific operations. This is similar to C# pattern matching:

```typescript
function display(value: string | number): string {
  if (typeof value === "string") {
    // TypeScript knows value is string here
    return value.toUpperCase();
  } else {
    // TypeScript knows value is number here
    return value.toFixed(2);
  }
}
```

```csharp
// C# pattern matching equivalent
string Display(object value)
{
    return value switch
    {
        string s => s.ToUpper(),
        int n => n.ToString("F2"),
        _ => throw new ArgumentException()
    };
}
```

For nullable values, you narrow with null checks:

```typescript
function formatAddress(address: string | null): string {
  if (address === null) {
    return "No address on file";
  }
  // TypeScript knows address is string here (not null)
  return address.trim();
}
```

---

## 5. Optional Properties

TypeScript uses the `?` suffix to mark properties as optional. An optional property might not exist on the object at all.

Here is the real `LeadFilters` interface from this project (`frontend/lib/types.ts`):

```typescript
export interface LeadFilters {
  q?: string;
  stage?: string;
  county?: string;
  minScore?: number;
  maxScore?: number;
  sort?: string;
  limit?: number;
  page?: number;
  pageSize?: number;
}
```

Every property is optional. You can create a `LeadFilters` object with any combination of these fields -- all of them, some of them, or none of them:

```typescript
// All valid LeadFilters objects:
const filters1: LeadFilters = {};
const filters2: LeadFilters = { stage: "New" };
const filters3: LeadFilters = { county: "Davidson", minScore: 40, page: 1 };
const filters4: LeadFilters = { q: "restaurant", stage: "New", pageSize: 20 };
```

### Optional vs Nullable

This is a subtlety that does not exist in C#. In TypeScript, there is a difference between "optional" and "nullable":

```typescript
interface Example {
  a?: string;           // Optional: property might not exist. Type is string | undefined
  b: string | null;     // Required but nullable: property MUST exist, value can be null
  c?: string | null;    // Optional AND nullable: might not exist, or might be null
}

// Valid:
const ex1: Example = { b: null };           // a is missing (ok, it's optional), b is null
const ex2: Example = { a: "hi", b: "bye" }; // a is present, b has a value
const ex3: Example = { b: null, c: null };   // c is present but null

// Invalid:
const ex4: Example = { a: "hi" };            // ERROR: b is required
```

In C#, the distinction is simpler: a property either allows `null` or it does not. There is no concept of "property might not exist" because C# objects always have all their declared properties.

```csharp
// C# -- all properties always exist on the object
public class Example
{
    public string? A { get; set; }     // Can be null (but the property always exists)
    public string? B { get; set; }     // Can be null
}
```

### Optional Function Parameters

Functions can have optional parameters too:

```typescript
// Optional parameter with ?
function getLeads(filters?: LeadFilters): Promise<LeadsResponse> {
  // filters might be undefined
}

// Default parameter value (implicitly optional)
function getPipelineRuns(limit: number = 10): Promise<{ runs: PipelineRun[] }> {
  // limit defaults to 10 if not provided
}
```

```csharp
// C# equivalent
Task<LeadsResponse> GetLeads(LeadFilters? filters = null) { ... }
Task<PipelineRunsResult> GetPipelineRuns(int limit = 10) { ... }
```

Here is the real usage from `frontend/lib/api.ts`:

```typescript
export async function getLeads(filters: LeadFilters = {}): Promise<LeadsResponse> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.county) params.set("county", filters.county);
  if (filters.minScore !== undefined) params.set("minScore", filters.minScore.toString());
  // ...
}
```

Notice the pattern: `filters: LeadFilters = {}` gives the parameter a default value of an empty object. Then each property is checked before use because they are all optional.

---

## 6. Generic Types

Generics in TypeScript work almost identically to generics in C#. The syntax uses angle brackets (`<T>`) in the same way.

### Basic Generic Comparison

```typescript
// TypeScript generic function
function identity<T>(value: T): T {
  return value;
}

const str = identity<string>("hello");   // str is string
const num = identity<number>(42);         // num is number
const inferred = identity("hello");       // TypeScript infers T = string
```

```csharp
// C# generic method
T Identity<T>(T value)
{
    return value;
}

var str = Identity<string>("hello");
var num = Identity<int>(42);
var inferred = Identity("hello");   // C# also infers T = string
```

### Promise\<T> is Task\<T>

The most common generic type you will see in this project is `Promise<T>`, which is TypeScript's equivalent of C#'s `Task<T>`:

```typescript
// TypeScript
async function getStats(): Promise<Stats> {
  // returns a Promise that resolves to a Stats object
}

// Usage
const stats: Stats = await getStats();
```

```csharp
// C# equivalent
async Task<Stats> GetStats()
{
    // returns a Task that resolves to a Stats object
}

// Usage
Stats stats = await GetStats();
```

### Record\<K, V> is Dictionary\<K, V>

TypeScript's `Record<K, V>` utility type is the equivalent of C#'s `Dictionary<TKey, TValue>`:

```typescript
// TypeScript
const byStage: Record<string, number> = {
  "New": 42,
  "Qualified": 18,
  "Contacted": 7,
};
```

```csharp
// C# equivalent
var byStage = new Dictionary<string, int>
{
    ["New"] = 42,
    ["Qualified"] = 18,
    ["Contacted"] = 7,
};
```

Here is the real `Stats` interface from this project, which uses `Record` extensively:

```typescript
export interface Stats {
  by_stage: Record<string, number>;     // Dictionary<string, int>
  by_county: Record<string, number>;    // Dictionary<string, int>
  by_type: Record<string, number>;      // Dictionary<string, int>
  avg_score: number;
  total_leads: number;
  last_run: PipelineRun | null;
}
```

And the `KanbanData` interface shows a more specific `Record` usage:

```typescript
export interface KanbanData {
  stages: Stage[];
  columns: Record<Stage, Lead[]>;   // Dictionary<Stage, List<Lead>>
}
```

Here, the keys are not arbitrary strings -- they are constrained to the `Stage` union type. TypeScript ensures that the `columns` object has exactly one entry for each stage value.

### The Real fetchJson\<T> Function

Here is the actual generic function from `frontend/lib/api.ts` that all API calls go through:

```typescript
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

Breaking this down:

- `<T>` is the type parameter, just like a C# generic.
- The function takes a `url` and optional `options`.
- It returns `Promise<T>` -- the caller decides what type `T` is.
- `response.json()` returns `any` by default, but the `Promise<T>` return type tells TypeScript to trust that the JSON matches `T`.

Here is how the callers specify `T`:

```typescript
// Each caller provides the concrete type for T:
export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>(`${API_BASE}/stats`);
  //              ^^^^^^^ T = Stats
}

export async function getLead(id: number): Promise<Lead> {
  return fetchJson<Lead>(`${API_BASE}/leads/${id}`);
  //              ^^^^^^ T = Lead
}

export async function getKanbanData(filters: LeadFilters = {}): Promise<KanbanData> {
  // ...
  return fetchJson<KanbanData>(`${API_BASE}/kanban${query ? `?${query}` : ""}`);
  //              ^^^^^^^^^^^^ T = KanbanData
}
```

The C# equivalent would be:

```csharp
async Task<T> FetchJson<T>(string url, HttpRequestMessage? options = null)
{
    var response = await _httpClient.SendAsync(options ?? new HttpRequestMessage(HttpMethod.Get, url));
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<T>();
}

// Callers:
async Task<Stats> GetStats()
{
    return await FetchJson<Stats>($"{ApiBase}/stats");
}
```

The pattern is identical: define a generic function once, and let each call site specify the concrete type.

---

## 7. Utility Types

TypeScript provides built-in **utility types** that transform other types. These have no direct equivalent in C# (you would write custom code or use attributes). They are used throughout this project.

### Record\<K, V>

Already covered in Section 6. Creates an object type with keys of type `K` and values of type `V`.

```typescript
Record<string, number>      // { [key: string]: number }     -- like Dictionary<string, int>
Record<Stage, Lead[]>       // { "New": Lead[], "Qualified": Lead[], ... }
```

### Partial\<T>

Makes **all properties optional**. This is extremely useful for update operations where you only want to change some fields.

```typescript
// Original interface -- all fields required
interface Lead {
  id: number;
  business_name: string;
  pos_score: number;
  stage: Stage;
}

// Partial<Lead> is equivalent to:
// interface PartialLead {
//   id?: number;
//   business_name?: string;
//   pos_score?: number;
//   stage?: Stage;
// }

function updateLead(id: number, changes: Partial<Lead>) {
  // changes can have any subset of Lead fields
}

updateLead(1, { stage: "Qualified" });                    // valid
updateLead(1, { business_name: "New Name", pos_score: 90 }); // valid
updateLead(1, {});                                         // valid
```

There is no built-in C# equivalent. You would typically use nullable properties:

```csharp
// C# -- you have to manually define this
public class LeadUpdate
{
    public string? BusinessName { get; set; }
    public int? PosScore { get; set; }
    public Stage? Stage { get; set; }
}
```

The real `LeadFieldUpdate` interface in this project is essentially a hand-written `Partial<Lead>` with only the editable fields:

```typescript
export interface LeadFieldUpdate {
  business_name?: string;
  address?: string;
  city?: string;
  county?: string;
  zip_code?: string;
  business_type?: string;
  stage?: string;
  note?: string;
}
```

### Readonly\<T>

Makes all properties `readonly`, preventing reassignment. This is like marking all fields `readonly` in C#.

Here is a real usage from `frontend/app/layout.tsx`:

```typescript
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // children cannot be reassigned inside this function
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

The `Readonly<{ children: React.ReactNode }>` means the `children` property cannot be mutated. In C#:

```csharp
// C# equivalent concept
public class RootLayoutProps
{
    public readonly object Children;
}
```

### Pick\<T, K> and Omit\<T, K>

These let you create new types by selecting or excluding properties:

```typescript
// Pick only certain fields from Lead
type LeadSummary = Pick<Lead, "id" | "business_name" | "pos_score">;
// Result: { id: number; business_name: string; pos_score: number }

// Omit certain fields from Lead
type LeadWithoutDates = Omit<Lead, "created_at" | "updated_at">;
// Result: Lead but without created_at and updated_at
```

### React-Specific Types

You will encounter these types frequently in the component files:

- **`React.ReactNode`** -- The type for "anything React can render." This includes strings, numbers, JSX elements, arrays of elements, `null`, and `undefined`. It is the React equivalent of C#'s `object` when used for UI content.

- **`React.HTMLAttributes<HTMLDivElement>`** -- Built-in type definitions for standard HTML element attributes. This allows a component to accept any prop that a normal `<div>` would accept (`className`, `onClick`, `style`, etc.).

Here is a real example from `frontend/components/ui/card.tsx`:

```typescript
const Card = React.forwardRef<
  HTMLDivElement,                          // The ref type (what element this wraps)
  React.HTMLAttributes<HTMLDivElement>     // The props type (any valid div attributes)
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("rounded-xl glass glow-hover transition-all duration-300", className)}
    {...props}
  />
));
```

- **`React.ComponentProps<typeof SomeComponent>`** -- Extracts the props type from an existing component. Used in the project's Toaster wrapper:

```typescript
type ToasterProps = React.ComponentProps<typeof Sonner>;
```

This says "ToasterProps is whatever props the Sonner component accepts." No need to manually define them.

---

## 8. Type Assertions (Casting)

TypeScript has type assertions, which are similar to casting in C# but with a critical difference: **they have no runtime effect**. A type assertion tells the compiler "trust me, I know the type" without performing any actual conversion or validation.

### The `as` Keyword

```typescript
// TypeScript assertion
const theme = "dark";
const toasterTheme = theme as ToasterProps["theme"];
```

```csharp
// C# cast (with runtime check)
var theme = "dark";
var toasterTheme = (ToasterTheme)Enum.Parse(typeof(ToasterTheme), theme);
```

The crucial difference: a C# cast will throw `InvalidCastException` at runtime if the cast is invalid. A TypeScript assertion does **nothing** at runtime. It only affects the compiler's understanding. If you assert the wrong type, your program will have a bug that TypeScript cannot catch.

Here is the real usage from `frontend/components/ui/sonner.tsx`:

```typescript
const { theme = "system" } = useTheme();

return (
  <Sonner
    theme={theme as ToasterProps["theme"]}
    // ...
  />
);
```

The `useTheme()` hook returns `theme` as `string | undefined`, but the `Sonner` component's `theme` prop expects a specific union type (`"light" | "dark" | "system"`). The `as` assertion tells TypeScript: "I know this string is one of those valid values."

### The `as const` Assertion

`as const` narrows a value to its **literal type** rather than its general type. This is used extensively in this project:

```typescript
// Without "as const"
const key = "total_leads";           // TypeScript infers: string

// With "as const"
const key = "total_leads" as const;  // TypeScript infers: "total_leads" (the literal)
```

Why does this matter? From the real `stats-cards.tsx`:

```typescript
const statConfig = [
  {
    key: "total_leads" as const,
    label: "Total Leads",
    icon: Users,
    getValue: (stats: Stats) => stats.total_leads,
  },
  {
    key: "avg_score" as const,
    label: "Avg Score",
    icon: Target,
    getValue: (stats: Stats) => stats.avg_score.toFixed(1),
  },
  // ...
];
```

Without `as const`, each `key` would be typed as `string`. With `as const`, each `key` is typed as its exact literal value (`"total_leads"`, `"avg_score"`, etc.). This enables TypeScript to catch errors like using an invalid key value.

You can also apply `as const` to an entire array or object:

```typescript
const STATUSES = ["pending", "merged", "dismissed"] as const;
// Type: readonly ["pending", "merged", "dismissed"]
// Each element is a string literal, and the array is readonly
```

There is no direct C# equivalent to `as const`. The closest concept is `const` strings or `readonly` arrays, but C# does not narrow the type to the literal value.

### When to Use Assertions

Use assertions sparingly. They are an escape hatch, not a regular tool. Prefer:

1. **Type guards** (runtime checks that narrow the type):
   ```typescript
   if (typeof value === "string") { /* value is string here */ }
   ```

2. **Proper type definitions** so assertions are not needed.

3. **Assertions only when** you genuinely know more than the compiler (e.g., the `useTheme` example above, where you know the theme provider only returns valid theme strings).

---

## 9. Structural Typing vs Nominal Typing

This is the **single biggest conceptual difference** between TypeScript and C#. Understanding it is essential for working effectively with TypeScript.

### C# Uses Nominal Typing

In C#, types are matched by **name and inheritance**. Two classes with identical fields are different types unless they share a common base:

```csharp
// C# -- nominal typing
public class Dog
{
    public string Name { get; set; }
    public int Age { get; set; }
}

public class Cat
{
    public string Name { get; set; }
    public int Age { get; set; }
}

void PrintAnimal(Dog dog) { Console.WriteLine(dog.Name); }

var cat = new Cat { Name = "Whiskers", Age = 3 };
PrintAnimal(cat);  // COMPILE ERROR: Cat is not Dog, even though they have the same fields
```

The error occurs because `Cat` and `Dog` are different named types, even though they have identical shapes. In C#, you would fix this by defining a shared interface:

```csharp
public interface IAnimal
{
    string Name { get; }
    int Age { get; }
}

public class Dog : IAnimal { ... }
public class Cat : IAnimal { ... }

void PrintAnimal(IAnimal animal) { ... }  // Now both work
```

### TypeScript Uses Structural Typing

In TypeScript, types are matched by **shape** (structure), not by name. If an object has the right properties with the right types, it matches:

```typescript
// TypeScript -- structural typing
interface Dog {
  name: string;
  age: number;
}

interface Cat {
  name: string;
  age: number;
}

function printAnimal(dog: Dog): void {
  console.log(dog.name);
}

const cat: Cat = { name: "Whiskers", age: 3 };
printAnimal(cat);  // WORKS FINE: Cat has the same shape as Dog
```

This compiles and runs without error. TypeScript does not care that the parameter is called `Dog` and you passed a `Cat`. It only checks: does this object have a `name: string` and `age: number`? Yes? Then it matches.

### You Do Not Even Need to Declare a Type

This goes even further. You do not need to use any named type at all:

```typescript
interface Lead {
  id: number;
  business_name: string;
  pos_score: number;
}

function printLead(lead: Lead): void {
  console.log(`${lead.business_name}: ${lead.pos_score}`);
}

// This object was never declared as a Lead, but it has the right shape
const myObject = { id: 1, business_name: "Acme Grill", pos_score: 85, extra: "ignored" };
printLead(myObject);  // WORKS: has id, business_name, and pos_score
```

The `extra` property is simply ignored. TypeScript checks that the required properties exist and have the correct types. Extra properties are allowed when assigning from a variable (though TypeScript does flag extra properties in direct object literals, which is a separate safeguard).

### Why This Matters in Practice

Structural typing is why TypeScript interfaces work so well for API responses. When you call `fetchJson<Lead>(url)`, TypeScript does not verify at runtime that the JSON response actually has the right shape. It trusts the assertion. But during development, the type system ensures your code *uses* the data correctly:

```typescript
const lead = await getLead(42);  // TypeScript assumes this is Lead

// TypeScript checks all these at compile time:
console.log(lead.business_name);  // OK: business_name exists on Lead
console.log(lead.pos_score);      // OK: pos_score exists on Lead
console.log(lead.nonexistent);    // ERROR: nonexistent does not exist on Lead
lead.pos_score.toUpperCase();     // ERROR: number has no toUpperCase method
```

### Comparison to Python

If you know Python, structural typing is conceptually similar to **duck typing** ("if it walks like a duck and quacks like a duck, it is a duck"). The difference is that Python checks this at runtime (and crashes if it fails), while TypeScript checks it at compile time (and prevents the code from building if it fails). TypeScript gives you the flexibility of duck typing with the safety of compile-time checking.

---

## 10. The `type` Keyword vs `interface`

TypeScript provides two ways to define type shapes: `type` and `interface`. They overlap significantly but have different strengths.

### `interface` -- For Object Shapes

Use `interface` when defining the shape of an object (the properties it must have):

```typescript
export interface Stats {
  by_stage: Record<string, number>;
  by_county: Record<string, number>;
  by_type: Record<string, number>;
  avg_score: number;
  total_leads: number;
  last_run: PipelineRun | null;
}

export interface LeadsResponse {
  leads: Lead[];
  count: number;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
```

Interfaces can be **extended** (adding new fields to a base interface) and **merged** (declaring the same interface name twice adds the fields together -- useful for augmenting library types).

### `type` -- For Everything Else

Use `type` for unions, intersections, aliases for primitives, and other type expressions that cannot be expressed with `interface`:

```typescript
// Union of string literals -- interface cannot do this
export type Stage =
  | "New"
  | "Qualified"
  | "Contacted"
  | "Follow-up"
  | "Closed-Won"
  | "Closed-Lost";

// Union of string literals
export type BusinessType =
  | "restaurant"
  | "bar"
  | "retail"
  | "salon"
  | "cafe"
  | "bakery"
  | "gym"
  | "spa"
  | "other";

// Union of specific string literals for a status field
type DuplicateStatus = "pending" | "merged" | "dismissed";

// Extracting props type from a component
type ToasterProps = React.ComponentProps<typeof Sonner>;

// Accessing a nested type within another type
type ToasterTheme = ToasterProps["theme"];
```

### Convention in This Project

This project follows a common convention:

- **`interface`** for object shapes (data structures, component props, API responses).
- **`type`** for unions, aliases, and computed types.

Looking at `frontend/lib/types.ts`:

```typescript
// Object shapes use interface:
export interface Lead { ... }
export interface LeadsResponse { ... }
export interface Stats { ... }
export interface PipelineRun { ... }
export interface LeadFilters { ... }
export interface DuplicateSuggestion { ... }

// Unions and enumerations use type:
export type Stage = "New" | "Qualified" | ...;
export type BusinessType = "restaurant" | "bar" | ...;
```

### Can `type` Define Object Shapes?

Yes, and it works identically for most purposes:

```typescript
// These are functionally equivalent for most use cases:
interface Lead {
  id: number;
  name: string;
}

type Lead = {
  id: number;
  name: string;
};
```

The practical differences:

| Feature | `interface` | `type` |
|---------|-------------|--------|
| Object shapes | Yes | Yes |
| Union types | No | Yes |
| Extending/inheriting | `extends` keyword | Intersection (`&`) |
| Declaration merging | Yes (same name = merged) | No (same name = error) |
| Can represent primitives | No | Yes (`type ID = string`) |

For a C# developer: think of `interface` as your go-to for DTOs and data contracts, and `type` as a more flexible tool for everything else.

---

## 11. Importing Types

TypeScript has a special syntax for importing types that differs from regular imports.

### Regular Import vs Type Import

```typescript
// Regular import -- imports a runtime value (function, class, constant)
import { getStats } from "@/lib/api";

// Type-only import -- imports ONLY the type, not any runtime code
import type { Lead, Stats, Stage } from "@/lib/types";
```

The `import type` syntax tells the TypeScript compiler (and the bundler): "I only need this for type checking. Do not include it in the output JavaScript."

Here is the real import from `frontend/lib/api.ts`:

```typescript
import type {
  Lead,
  LeadsResponse,
  LeadsBatchResponse,
  Stats,
  PipelineRun,
  PipelineStatus,
  KanbanData,
  LeadFilters,
  LeadFieldUpdate,
  DuplicatesResponse,
  MergeRequest,
} from "./types";
```

All of these are interfaces and types -- they have no runtime representation. Using `import type` makes this explicit and ensures no unnecessary code ends up in the compiled JavaScript.

### You Can Also Import a Type Inline

```typescript
// Mixed import: a regular import with an inline type import
import { useState, type ReactNode } from "react";
```

This imports `useState` as a regular runtime value (it is a function) and `ReactNode` as a type only. This is exactly what the project does in `frontend/components/providers.tsx`:

```typescript
import { useState, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ ... }));
  // ...
}
```

### Why This Matters

In C#, all types exist at runtime, so there is no distinction between "importing a type" and "importing a value." When you write `using System.Collections.Generic;`, the `Dictionary<TKey, TValue>` type is available both for compilation and at runtime.

In TypeScript, since types are erased, `import type` communicates intent and enables better optimization:

1. **Tree shaking** -- The bundler can safely exclude type-only imports from the output.
2. **Circular dependency avoidance** -- If two files only depend on each other's types (not runtime values), `import type` breaks the circular dependency.
3. **Clarity** -- It is immediately obvious which imports are for types vs runtime values.

The TypeScript compiler option `"isolatedModules": true` (enabled in this project's `tsconfig.json`) enforces that type imports use `import type`. This ensures compatibility with tools like Next.js that compile files independently.

---

## 12. Constants with Type Safety

TypeScript lets you create typed constant arrays that enforce their values at compile time.

### Typed Constant Arrays

From `frontend/lib/types.ts`:

```typescript
export const STAGES: Stage[] = [
  "New",
  "Qualified",
  "Contacted",
  "Follow-up",
  "Closed-Won",
  "Closed-Lost",
];
```

Because `STAGES` is typed as `Stage[]`, TypeScript enforces that every element must be a valid `Stage` value. If you tried to add an invalid value:

```typescript
export const STAGES: Stage[] = [
  "New",
  "Qualified",
  "Contacted",
  "Follow-up",
  "Closed-Won",
  "Closed-Lost",
  "Invalid",          // ERROR: Type '"Invalid"' is not assignable to type 'Stage'
];
```

The same applies to `BUSINESS_TYPES`:

```typescript
export const BUSINESS_TYPES: BusinessType[] = [
  "restaurant",
  "bar",
  "retail",
  "salon",
  "cafe",
  "bakery",
  "gym",
  "spa",
  "other",
];
```

### Using Typed Constants

These typed constants are used in the UI for things like dropdown menus and filter options:

```typescript
import { STAGES } from "@/lib/types";

// In a component -- render a dropdown of valid stages
function StageSelect() {
  return (
    <select>
      {STAGES.map((stage) => (
        <option key={stage} value={stage}>
          {stage}
        </option>
      ))}
    </select>
  );
}
```

TypeScript knows that `stage` inside the `.map()` callback is of type `Stage`, not just `string`. This means autocomplete works and typos are caught.

### `as const` for Tuple-Like Arrays

When you want an array to be treated as a fixed, readonly tuple (not a mutable array), use `as const`:

```typescript
const STATUSES = ["pending", "merged", "dismissed"] as const;
// Type: readonly ["pending", "merged", "dismissed"]

// You can derive a union type from it:
type Status = typeof STATUSES[number];
// Type: "pending" | "merged" | "dismissed"
```

This is a powerful pattern that lets you define the values once and derive the type automatically, instead of defining both separately.

In C#, the closest equivalent is a combination of an enum and a static array:

```csharp
public enum Status { Pending, Merged, Dismissed }

public static readonly Status[] Statuses = { Status.Pending, Status.Merged, Status.Dismissed };
```

But with the `as const` pattern in TypeScript, you get the "enum" (union type) and the "array" (constant list) from a single source of truth.

---

## 13. Quick Reference Table

| Concept | TypeScript | C# Equivalent |
|---------|-----------|---------------|
| **String type** | `string` | `string` |
| **Number type** | `number` | `int`, `double`, `decimal` (TS has one type for all) |
| **Boolean type** | `boolean` | `bool` |
| **Null/undefined** | `string \| null`, `string \| undefined` | `string?` (nullable reference) |
| **Type inference** | `const x = 5` | `var x = 5` |
| **Array type** | `number[]` or `Array<number>` | `int[]` or `List<int>` |
| **Enum-like type** | `type Stage = "New" \| "Qualified"` | `enum Stage { New, Qualified }` |
| **Interface** | `interface Lead { id: number; }` | `record Lead(int Id);` or DTO class |
| **Optional property** | `name?: string` | `string? Name { get; set; }` |
| **Generic function** | `function f<T>(x: T): T` | `T F<T>(T x)` |
| **Async return** | `Promise<Stats>` | `Task<Stats>` |
| **Dictionary** | `Record<string, number>` | `Dictionary<string, int>` |
| **Make all optional** | `Partial<Lead>` | No built-in equivalent |
| **Make all readonly** | `Readonly<Lead>` | All properties `readonly` |
| **Select properties** | `Pick<Lead, "id" \| "name">` | No built-in equivalent |
| **Exclude properties** | `Omit<Lead, "created_at">` | No built-in equivalent |
| **Type assertion** | `value as string` | `(string)value` (but TS has no runtime check) |
| **Literal narrowing** | `as const` | No equivalent |
| **Type-only import** | `import type { Lead }` | No equivalent (C# types always exist at runtime) |
| **Void return** | `void` | `void` |
| **Any type (escape hatch)** | `any` | `dynamic` |
| **Unknown type (safe any)** | `unknown` | `object` |
| **Typing system** | Structural (shape-based) | Nominal (name-based) |
| **Types at runtime** | Erased (do not exist) | Preserved (reflection, typeof) |

---

## Summary

Coming from C#, TypeScript should feel remarkably familiar. The type system uses the same concepts -- generics, interfaces, type annotations, `void`, `readonly` -- with slightly different syntax. The two critical differences to internalize:

1. **Types are erased at runtime.** You cannot inspect types in running code. There is no reflection, no `typeof(Lead)`, no `is` pattern matching on TypeScript types. All type checking happens before your code runs.

2. **Structural typing, not nominal typing.** TypeScript does not care about the name of a type. It only cares about the shape. If an object has the right properties, it matches, regardless of whether it was ever declared as that type.

Everything else -- generics, interfaces, `async`/`await`, union types, optional parameters -- maps directly to concepts you already know from C#. The syntax is different, but the ideas are the same.

**Next up:** Document 03 will cover React fundamentals -- components, JSX, props, and state -- building on the JavaScript (Document 01) and TypeScript (this document) foundations.
