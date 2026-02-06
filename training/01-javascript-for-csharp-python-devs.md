# JavaScript for C# and Python Developers

This guide assumes you are proficient in C# and Python but have never written JavaScript. It covers every concept you will encounter in this project's Next.js frontend, with side-by-side comparisons to the languages you already know. Read this document from top to bottom before touching any `.js`, `.ts`, `.jsx`, or `.tsx` file.

---

## 1. Variables and Constants

JavaScript has three keywords for declaring variables. In practice you will use two of them.

### `const` — Your Default Choice

`const` declares a variable whose **reference** cannot be reassigned. Think of it as C# `readonly` or the Python convention of `UPPER_CASE` naming for constants, except the runtime actually enforces it.

```javascript
const maxScore = 100;
maxScore = 200; // ERROR: Assignment to constant variable
```

```csharp
// C# equivalent
readonly int maxScore = 100;
```

```python
# Python — convention only, not enforced
MAX_SCORE = 100
```

**Critical nuance:** `const` protects the *reference*, not the *contents*. When you assign an object or array to a `const`, you cannot point the variable at a different object, but you can freely modify properties and elements inside it.

```javascript
const lead = { name: "Acme", score: 85 };
lead.name = "Foo";           // OK — modifying a property on the same object
lead.score = 90;             // OK — same object, different property value
lead = { name: "Bar" };      // ERROR — trying to point `lead` at a new object

const items = [1, 2, 3];
items.push(4);               // OK — mutating the array's contents
items[0] = 99;               // OK — replacing an element
items = [5, 6, 7];           // ERROR — reassigning the reference
```

This is identical to how C# `readonly` works on reference types:

```csharp
// C#
readonly List<int> items = new List<int> { 1, 2, 3 };
items.Add(4);                // OK — mutating contents
items = new List<int>();     // ERROR — reassigning readonly field
```

### `let` — When You Must Reassign

`let` declares a variable whose reference **can** change. Use it for counters, accumulators, or values that update inside loops.

```javascript
let count = 0;
count += 1;   // OK
count = 10;   // OK
```

```csharp
// C#
int count = 0;
count += 1;
```

```python
# Python
count = 0
count += 1
```

### `var` — Legacy, Never Use

`var` is the original variable keyword from 1995. It has confusing scoping rules (function-scoped instead of block-scoped) and is hoisted in surprising ways. You will see it in old tutorials. Do not use it in new code.

```javascript
// DO NOT DO THIS
var name = "Acme";

// DO THIS INSTEAD
const name = "Acme";   // if the value never changes
let name = "Acme";     // if you must reassign later
```

### Rule of Thumb

Use `const` for everything. Switch to `let` only when the linter or compiler tells you the value must be reassigned. Never use `var`.

---

## 2. Primitive Types

JavaScript has fewer primitive types than C# and collapses some distinctions that exist in both C# and Python.

### The Six Primitives

| JavaScript | C# Equivalent | Python Equivalent |
|---|---|---|
| `string` | `string` | `str` |
| `number` | `double` (always 64-bit float) | `float` (roughly) |
| `boolean` | `bool` | `bool` |
| `null` | `null` | `None` |
| `undefined` | *(no equivalent)* | *(no equivalent)* |
| `bigint` | `BigInteger` | `int` (arbitrary precision) |

### No int/float Distinction

This is the single most surprising difference. JavaScript has **one** numeric type: `number`, which is always a 64-bit IEEE 754 floating-point value. There is no `int`, no `long`, no `decimal`.

```javascript
const count = 42;          // This is a number (float under the hood)
const price = 19.99;       // This is also a number
const result = 1 / 3;      // 0.3333333333333333
typeof count;              // "number"
typeof price;              // "number"
```

```csharp
// C# — distinct types
int count = 42;
double price = 19.99;
```

```python
# Python — distinct types
count = 42         # int
price = 19.99      # float
```

For lead scores in this project, values like `85` look like integers but are technically floats. This rarely causes problems, but be aware that `0.1 + 0.2 !== 0.3` in JavaScript, just as in C# with `double` and Python with `float`.

### Template Literals (String Interpolation)

All three languages support embedding expressions inside strings, but the syntax differs.

```javascript
// JavaScript — backticks and ${...}
const name = "Acme Cafe";
const score = 85;
const message = `Lead "${name}" scored ${score} out of 100`;
// Can span multiple lines without any special characters
const multiline = `
  Name: ${name}
  Score: ${score}
`;
```

```csharp
// C# — dollar sign prefix and {...}
string message = $"Lead \"{name}\" scored {score} out of 100";
```

```python
# Python — f prefix and {...}
message = f'Lead "{name}" scored {score} out of 100'
```

Note that JavaScript uses **backticks** (`` ` ``), not regular quotes. Single quotes (`'`) and double quotes (`"`) create plain strings without interpolation.

### `null` vs `undefined`

JavaScript has two "empty" values. This is a source of frequent confusion.

| Value | Meaning | When You See It |
|---|---|---|
| `null` | Intentionally empty. A developer explicitly set this. | `const result = null;` |
| `undefined` | Not yet assigned. The runtime produced this. | Accessing a missing property: `obj.missing` |

```javascript
let x;                    // x is undefined — declared but never assigned
const obj = { name: "Acme" };
console.log(obj.score);   // undefined — property does not exist
console.log(obj.name);    // "Acme"

let y = null;             // y is null — explicitly set to "nothing"
```

In C#, there is only `null`. In Python, there is only `None`. JavaScript forces you to handle both. In practice, use `== null` (loose equality, the one exception to the "always use `===`" rule) to catch both at once:

```javascript
if (value == null) {
  // This catches BOTH null AND undefined
}
```

Or use the `??` operator (covered in Section 6).

---

## 3. Objects and Arrays

### Object Literals

JavaScript objects are the workhorses of the language. They are key-value collections created with curly braces, similar to Python dictionaries but with dot-access syntax like C# objects.

```javascript
const lead = {
  name: "Acme Cafe",
  score: 85,
  county: "Davidson",
  stage: "New",
};

// Access with dot notation (like C# properties)
console.log(lead.name);       // "Acme Cafe"

// Access with bracket notation (like Python dict)
console.log(lead["county"]);  // "Davidson"

// Add new properties at any time
lead.phone = "615-555-0100";
```

```csharp
// C# — closest equivalent is an anonymous type or dictionary
var lead = new { Name = "Acme Cafe", Score = 85 };   // anonymous, immutable
var dict = new Dictionary<string, object> {           // mutable
    ["name"] = "Acme Cafe",
    ["score"] = 85
};
```

```python
# Python — dictionary
lead = {
    "name": "Acme Cafe",
    "score": 85,
    "county": "Davidson",
}
lead["name"]   # "Acme Cafe" — bracket access only
```

### Arrays

JavaScript arrays are ordered, zero-indexed, dynamically sized collections. They behave like Python lists.

```javascript
const scores = [85, 72, 91, 45];
scores.length;          // 4
scores[0];              // 85
scores.push(100);       // adds to end: [85, 72, 91, 45, 100]
scores.includes(72);    // true
```

```csharp
// C#
var scores = new List<int> { 85, 72, 91, 45 };
scores.Count;
scores[0];
scores.Add(100);
scores.Contains(72);
```

```python
# Python
scores = [85, 72, 91, 45]
len(scores)
scores[0]
scores.append(100)
72 in scores
```

### Destructuring Objects

Destructuring lets you unpack properties from an object into individual variables in a single statement. This is used **everywhere** in React code.

```javascript
const lead = { name: "Acme Cafe", score: 85, county: "Davidson" };

// Without destructuring
const name = lead.name;
const score = lead.score;

// With destructuring — equivalent to the two lines above
const { name, score } = lead;
console.log(name);    // "Acme Cafe"
console.log(score);   // 85
```

C# has no direct equivalent for this. Python has no direct equivalent for dictionary destructuring either (tuple unpacking is different).

**Renaming during destructuring** is common in this project. The syntax is `{ originalName: newName }`:

```javascript
// From the dashboard page.tsx in this project:
const { data: stats, isLoading } = useQuery({
  queryKey: ["stats"],
  queryFn: getStats,
});
// `data` is the property name from React Query
// `stats` is what we want to call it in our code
// `isLoading` keeps its original name
```

This is equivalent to:

```javascript
const result = useQuery({ queryKey: ["stats"], queryFn: getStats });
const stats = result.data;
const isLoading = result.isLoading;
```

### Destructuring Arrays

Array destructuring unpacks by position instead of by name.

```javascript
const pair = ["Davidson", 42];
const [county, count] = pair;
console.log(county);   // "Davidson"
console.log(count);    // 42
```

```python
# Python — identical concept, different name (tuple unpacking)
county, count = ("Davidson", 42)
```

```csharp
// C# — tuple deconstruction (C# 7+)
var (county, count) = ("Davidson", 42);
```

### The Spread Operator (`...`)

The spread operator unpacks an object or array into a new one. It is used constantly in React to create modified copies without mutating the original.

**Objects:**

```javascript
const lead = { name: "Acme", score: 85, stage: "New" };
const updated = { ...lead, stage: "Qualified", note: "Called owner" };
// Result: { name: "Acme", score: 85, stage: "Qualified", note: "Called owner" }
// The original `lead` is unchanged
```

```python
# Python — dictionary unpacking
updated = {**lead, "stage": "Qualified", "note": "Called owner"}
```

```csharp
// C# — no direct equivalent; typically use object initializer with `with` for records
var updated = lead with { Stage = "Qualified" };
```

**Arrays:**

```javascript
const first = [1, 2, 3];
const second = [4, 5, 6];
const combined = [...first, ...second];   // [1, 2, 3, 4, 5, 6]
const withExtra = [0, ...first, 99];      // [0, 1, 2, 3, 99]
```

```python
# Python — list unpacking
combined = [*first, *second]
```

A real example from this project's API client, where spread merges default headers with caller-provided headers:

```javascript
const response = await fetch(url, {
  ...options,
  headers: { "Content-Type": "application/json", ...options?.headers },
});
```

---

## 4. Functions

JavaScript offers multiple ways to define functions. You will see two forms in this project.

### Function Declarations

The traditional form, similar to function definitions in C# and Python.

```javascript
function calculateScore(typeScore, sourceScore, addressScore) {
  return typeScore + sourceScore + addressScore;
}
```

```csharp
// C#
int CalculateScore(int typeScore, int sourceScore, int addressScore) {
    return typeScore + sourceScore + addressScore;
}
```

```python
# Python
def calculate_score(type_score, source_score, address_score):
    return type_score + source_score + address_score
```

### Arrow Functions

Arrow functions are the dominant form in React codebases. They use `=>` syntax, similar to C# lambdas and Python lambdas.

```javascript
// Full form with body
const calculateScore = (typeScore, sourceScore, addressScore) => {
  return typeScore + sourceScore + addressScore;
};

// Implicit return — no braces, no `return` keyword
const double = (x) => x * 2;

// Single parameter — parentheses optional (but TypeScript requires them)
const greet = name => `Hello, ${name}`;
```

```csharp
// C# lambda
Func<int, int> double = x => x * 2;
// C# lambda with body
Func<int, int> double = (x) => { return x * 2; };
```

```python
# Python lambda (single expression only)
double = lambda x: x * 2
```

**Key difference from Python:** JavaScript arrow functions can have full multi-line bodies with `{ }`. Python lambdas are limited to a single expression.

### Default Parameters

All three languages support default parameter values with identical syntax concepts.

```javascript
function greet(name = "World") {
  return `Hello, ${name}`;
}
greet();        // "Hello, World"
greet("Acme");  // "Hello, Acme"
```

```csharp
// C#
string Greet(string name = "World") => $"Hello, {name}";
```

```python
# Python
def greet(name="World"):
    return f"Hello, {name}"
```

### Async Arrow Functions

When a function needs to perform asynchronous work (API calls, database queries), prefix it with `async`. This project uses async arrow functions heavily.

```javascript
// From this project's pipeline page
const handleRunPipeline = async () => {
  try {
    await triggerPipelineRun();
    toast.success("Pipeline started");
  } catch (error) {
    toast.error("Failed to start pipeline");
  }
};
```

```csharp
// C# — very similar
var handleRunPipeline = async () => {
    try {
        await TriggerPipelineRun();
    } catch (Exception) {
        // handle error
    }
};
```

```python
# Python
async def handle_run_pipeline():
    try:
        await trigger_pipeline_run()
    except Exception:
        pass
```

---

## 5. Modules (Import/Export)

JavaScript uses `import`/`export` to share code between files. This is conceptually identical to C# `using` and Python `import`, but the syntax is different.

### Named Exports and Imports

A file can export multiple values by name. The importing file picks the ones it needs.

```javascript
// lib/api.ts — exporting
export async function getStats(): Promise<Stats> { /* ... */ }
export async function getLeads(params): Promise<LeadsResponse> { /* ... */ }
export async function triggerPipelineRun(): Promise<void> { /* ... */ }

// app/page.tsx — importing specific names
import { getStats, triggerPipelineRun } from "@/lib/api";
```

```csharp
// C# — the `using` directive imports an entire namespace
using MyApp.Lib;   // imports everything from the namespace
// No syntax to import only specific members
```

```python
# Python — closest equivalent
from lib.api import get_stats, trigger_pipeline_run
```

### Default Exports and Imports

A file can also export a single "default" value. The importer chooses what to call it.

```javascript
// next/link exports a default component
import Link from "next/link";

// You could name it anything (but don't)
import MyLink from "next/link";  // Same thing, different local name
```

```python
# Python — no direct equivalent; closest is importing a module
import link  # then use link.default
```

### Type-Only Imports

TypeScript (covered in the next document) allows importing types that exist only at compile time and are erased from the runtime bundle.

```javascript
import type { Stats, Lead } from "@/lib/types";
```

This has no C# or Python equivalent because types are always available at runtime in those languages.

### The `@/` Path Alias

In this project, `@/` is configured as an alias for the project's `frontend/` root directory. It avoids fragile relative paths.

```javascript
// Instead of this (brittle, breaks if file moves)
import { getStats } from "../../lib/api";

// Use this (always works from any depth)
import { getStats } from "@/lib/api";
```

This is similar to how C# namespaces and Python package paths work — absolute references that do not depend on the importing file's location.

---

## 6. Equality and Truthiness

### Strict vs Loose Equality

JavaScript has two equality operators. **Always use strict equality.**

| Operator | Name | Behavior |
|---|---|---|
| `===` | Strict equality | Compares value AND type. No coercion. |
| `==` | Loose equality | Coerces types before comparing. Surprising results. |

```javascript
// Strict equality — predictable
42 === 42       // true
"42" === 42     // false (string vs number)
null === undefined // false

// Loose equality — surprising
"42" == 42      // true (!)  — string coerced to number
null == undefined // true (!) — special case
"" == false     // true (!)  — both coerced to 0
```

**Rule:** Always use `===` and `!==`. The only exception is `value == null` to catch both `null` and `undefined`, and even that is a style choice — `value === null || value === undefined` is clearer.

C# and Python do not have this problem. `==` in C# does type-safe comparison. `==` in Python compares by value without coercion.

### Truthiness and Falsiness

JavaScript evaluates non-boolean values in boolean contexts (if statements, logical operators). This is similar to Python but different from C#.

**Falsy values** (evaluate to `false`):

| Value | Note |
|---|---|
| `false` | The boolean |
| `0` | Zero |
| `""` | Empty string |
| `null` | Null |
| `undefined` | Undefined |
| `NaN` | Not-a-Number |

**Everything else is truthy**, including `[]` (empty array) and `{}` (empty object). This differs from Python, where empty lists and dicts are falsy.

```javascript
// JavaScript
if ([]) { /* THIS RUNS — empty array is truthy */ }
if ({}) { /* THIS RUNS — empty object is truthy */ }
if ("") { /* THIS DOES NOT RUN — empty string is falsy */ }
```

```python
# Python — different!
if []:   # Does NOT run — empty list is falsy
if {}:   # Does NOT run — empty dict is falsy
if "":   # Does NOT run — same as JS
```

```csharp
// C# — no implicit truthiness; only bool allowed in conditions
if (list.Count > 0) { /* explicit check required */ }
```

### Logical OR for Defaults (`||`)

The `||` operator returns the first truthy value, or the last value if all are falsy. This is used for providing fallback values.

```javascript
const displayName = lead.name || "Unknown Business";
// If lead.name is "", null, undefined, or 0, uses "Unknown Business"
```

```python
# Python — same behavior
display_name = lead.name or "Unknown Business"
```

**Problem:** `||` treats `0` and `""` as falsy, which is sometimes wrong. If a score of `0` is a valid value, `score || 50` would incorrectly return `50`.

### Nullish Coalescing (`??`)

The `??` operator solves the `||` problem. It only falls back when the left side is `null` or `undefined` — not `0`, not `""`.

```javascript
const score = lead.score ?? 50;
// Only uses 50 if lead.score is null or undefined
// If lead.score is 0, keeps 0

const name = lead.name ?? "Unknown";
// Only uses "Unknown" if lead.name is null or undefined
// If lead.name is "", keeps ""
```

```csharp
// C# — identical behavior with the same operator
var score = lead.Score ?? 50;
```

```python
# Python — no direct equivalent; must be explicit
score = lead.score if lead.score is not None else 50
```

### Optional Chaining (`?.`)

The `?.` operator safely accesses nested properties without throwing if an intermediate value is `null` or `undefined`. It short-circuits and returns `undefined` instead.

```javascript
// Without optional chaining — verbose and fragile
let startedAt;
if (stats && stats.last_run && stats.last_run.run_started_at) {
  startedAt = stats.last_run.run_started_at;
}

// With optional chaining — one line
const startedAt = stats?.last_run?.run_started_at;
// Returns the value if the full chain exists, otherwise undefined
```

Real examples from this project:

```javascript
pipelineStatus?.running           // undefined if pipelineStatus is null
stats.last_run?.run_started_at    // undefined if last_run is null
error?.message                    // undefined if error is null
```

```csharp
// C# — identical syntax and behavior
pipelineStatus?.Running
stats.LastRun?.RunStartedAt
```

```python
# Python — no equivalent operator; must use getattr or try/except
getattr(pipeline_status, 'running', None)
```

---

## 7. Array Methods (Critical for React)

In React, you almost never write `for` loops. Instead, you use array methods that take callback functions and return new arrays. If you know C# LINQ, this will feel very natural.

### Reference Table

| JavaScript | C# LINQ | Python | Description |
|---|---|---|---|
| `.map(x => ...)` | `.Select(x => ...)` | `[f(x) for x in items]` | Transform each element |
| `.filter(x => ...)` | `.Where(x => ...)` | `[x for x in items if ...]` | Keep elements matching condition |
| `.find(x => ...)` | `.FirstOrDefault(x => ...)` | `next((x for x in items if ...), None)` | First match or undefined |
| `.findIndex(x => ...)` | `.FindIndex(x => ...)` | `next((i for i,x in enumerate(items) if ...), -1)` | Index of first match or -1 |
| `.some(x => ...)` | `.Any(x => ...)` | `any(... for x in items)` | True if any element matches |
| `.every(x => ...)` | `.All(x => ...)` | `all(... for x in items)` | True if all elements match |
| `.reduce(fn, init)` | `.Aggregate(init, fn)` | `functools.reduce(fn, items, init)` | Accumulate into single value |
| `.sort((a,b) => ...)` | `.OrderBy(x => ...)` | `sorted(items, key=...)` | Sort (mutates in place!) |
| `.slice(start, end)` | `.Skip(start).Take(end-start)` | `items[start:end]` | Extract sub-array |
| `.flat()` | `.SelectMany(x => x)` | `[item for sub in items for item in sub]` | Flatten nested arrays |
| `.includes(x)` | `.Contains(x)` | `x in items` | Check if element exists |
| `.join(sep)` | `string.Join(sep, items)` | `sep.join(items)` | Concatenate to string |
| `.forEach(x => ...)` | `.ForEach(x => ...)` / `foreach` | `for x in items:` | Side effect per element |
| `.length` | `.Count` / `.Length` | `len(items)` | Number of elements |

### `.map()` — Transform Every Element

The most important array method in React. It creates a **new** array by running a function on each element.

```javascript
const scores = [85, 72, 91, 45];
const doubled = scores.map(s => s * 2);
// [170, 144, 182, 90]

const leads = [
  { name: "Acme", score: 85 },
  { name: "Beta", score: 72 },
];
const names = leads.map(lead => lead.name);
// ["Acme", "Beta"]
```

```csharp
// C# LINQ
var doubled = scores.Select(s => s * 2).ToList();
var names = leads.Select(lead => lead.Name).ToList();
```

```python
# Python
doubled = [s * 2 for s in scores]
names = [lead["name"] for lead in leads]
```

### `.filter()` — Keep Matching Elements

Creates a new array with only the elements for which the callback returns `true`.

```javascript
const scores = [85, 72, 91, 45, 60];
const highScores = scores.filter(s => s >= 80);
// [85, 91]

const leads = [
  { name: "Acme", stage: "New" },
  { name: "Beta", stage: "Qualified" },
  { name: "Gamma", stage: "New" },
];
const newLeads = leads.filter(lead => lead.stage === "New");
// [{ name: "Acme", stage: "New" }, { name: "Gamma", stage: "New" }]
```

```csharp
// C# LINQ
var highScores = scores.Where(s => s >= 80).ToList();
var newLeads = leads.Where(lead => lead.Stage == "New").ToList();
```

```python
# Python
high_scores = [s for s in scores if s >= 80]
new_leads = [lead for lead in leads if lead["stage"] == "New"]
```

### `.find()` — First Match

Returns the first element matching the condition, or `undefined` if nothing matches.

```javascript
const lead = leads.find(l => l.name === "Acme");
// { name: "Acme", stage: "New" } or undefined
```

```csharp
// C#
var lead = leads.FirstOrDefault(l => l.Name == "Acme");
// Returns null if not found (for reference types)
```

```python
# Python
lead = next((l for l in leads if l["name"] == "Acme"), None)
```

### `.sort()` — Sorting (Warning: Mutates!)

Unlike `.map()` and `.filter()`, `.sort()` modifies the array **in place** and returns a reference to the same array. The comparison function receives two elements and must return:
- Negative number: `a` comes first
- Positive number: `b` comes first
- Zero: order unchanged

```javascript
const scores = [85, 72, 91, 45];

// Ascending
scores.sort((a, b) => a - b);     // [45, 72, 85, 91]

// Descending
scores.sort((a, b) => b - a);     // [91, 85, 72, 45]
```

```csharp
// C# — does not mutate; returns new sequence
var sorted = scores.OrderBy(s => s).ToList();
var descending = scores.OrderByDescending(s => s).ToList();
```

```python
# Python — sorted() returns new list; list.sort() mutates
sorted_scores = sorted(scores)
scores.sort()  # mutates
```

### `.reduce()` — Accumulate into a Single Value

Reduce takes an accumulator function and an initial value, then processes each element to produce a single result. Think of it as a fold.

```javascript
const scores = [85, 72, 91, 45];
const total = scores.reduce((sum, score) => sum + score, 0);
// 293
```

```csharp
// C# LINQ
var total = scores.Aggregate(0, (sum, score) => sum + score);
```

```python
# Python
from functools import reduce
total = reduce(lambda sum, score: sum + score, scores, 0)
# Or simply: total = sum(scores)
```

### Chaining Methods

The real power comes from chaining these methods together. Each method returns a new array, so you can pipeline transformations.

Here is a real example from this project's chart component:

```javascript
const chartData = Object.entries(data)
  .map(([name, value]) => ({ name: name || "Unknown", value }))
  .sort((a, b) => b.value - a.value)
  .slice(0, 8);
```

Let us break this down step by step:

1. **`Object.entries(data)`** converts an object like `{ "Davidson": 42, "Williamson": 18 }` into an array of `[key, value]` pairs: `[["Davidson", 42], ["Williamson", 18]]`. This is like Python's `dict.items()` or C#'s `dictionary.Select(kvp => ...)`.

2. **`.map(([name, value]) => ({ name: name || "Unknown", value }))`** transforms each pair into an object. Note the destructuring `[name, value]` in the parameter and the parentheses around the object literal `({...})` to distinguish it from a function body.

3. **`.sort((a, b) => b.value - a.value)`** sorts by value in descending order.

4. **`.slice(0, 8)`** takes the first 8 elements, like Python's `[:8]` or C# LINQ's `.Take(8)`.

The equivalent in C# LINQ:

```csharp
var chartData = data
    .Select(kvp => new { Name = kvp.Key ?? "Unknown", Value = kvp.Value })
    .OrderByDescending(x => x.Value)
    .Take(8)
    .ToList();
```

The equivalent in Python:

```python
chart_data = sorted(
    [{"name": name or "Unknown", "value": value} for name, value in data.items()],
    key=lambda x: x["value"],
    reverse=True
)[:8]
```

### `Object.entries()`, `Object.keys()`, `Object.values()`

These static methods convert objects into arrays so you can use array methods on them.

| JavaScript | Python | Description |
|---|---|---|
| `Object.entries(obj)` | `obj.items()` | Array of `[key, value]` pairs |
| `Object.keys(obj)` | `obj.keys()` | Array of keys |
| `Object.values(obj)` | `obj.values()` | Array of values |

```javascript
const scores = { Davidson: 42, Williamson: 18, Rutherford: 25 };

Object.keys(scores);      // ["Davidson", "Williamson", "Rutherford"]
Object.values(scores);    // [42, 18, 25]
Object.entries(scores);   // [["Davidson", 42], ["Williamson", 18], ["Rutherford", 25]]
```

C# dictionaries have similar members: `.Keys`, `.Values`, and iteration over `KeyValuePair`.

---

## 8. Async/Await and Promises

If you have used `async`/`await` in C# or Python, JavaScript's version will feel immediately familiar. The concepts map almost one-to-one.

### Concept Mapping

| JavaScript | C# | Python |
|---|---|---|
| `Promise<T>` | `Task<T>` | `Coroutine` / `Awaitable` |
| `async function` | `async Task<T> Method()` | `async def function()` |
| `await promise` | `await task` | `await coroutine` |
| `Promise.all([...])` | `Task.WhenAll(...)` | `asyncio.gather(...)` |
| `Promise.race([...])` | `Task.WhenAny(...)` | `asyncio.wait(..., FIRST_COMPLETED)` |
| `.then().catch()` | `.ContinueWith()` | *(no equivalent; use await)* |
| `try/catch` with `await` | `try/catch` with `await` | `try/except` with `await` |

### The `fetch()` API

JavaScript has a built-in HTTP client called `fetch()`. It returns a `Promise` that resolves to a `Response` object.

```javascript
// Basic GET request
const response = await fetch("http://localhost:8000/api/stats");
const data = await response.json();   // parse JSON body — also returns a Promise!
```

Note that `fetch()` does **not** throw on HTTP error statuses (404, 500, etc.). You must check `response.ok` yourself.

Here is the real `fetchJson` helper from this project's `lib/api.ts`:

```javascript
async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}
```

Line by line:
1. `async function fetchJson<T>` — declares an async generic function (the `<T>` is TypeScript, covered in the next document).
2. `await fetch(url, {...})` — makes the HTTP request. The spread operator merges default options with caller-provided options.
3. `...options?.headers` — optional chaining ensures this does not throw if `options` is undefined.
4. `if (!response.ok)` — checks for HTTP errors (status outside 200-299).
5. `await response.json().catch(...)` — tries to parse the error body; falls back to a generic message if parsing fails. The `.catch()` is a Promise method for handling errors inline.
6. `throw new Error(...)` — throws an exception, just like C# and Python.
7. `return response.json()` — returns the parsed JSON. Since this is an async function, the return value is automatically wrapped in a `Promise`.

The equivalent in C#:

```csharp
async Task<T> FetchJson<T>(string url) {
    var response = await httpClient.GetAsync(url);
    if (!response.IsSuccessStatusCode) {
        throw new HttpRequestException($"HTTP {(int)response.StatusCode}");
    }
    var json = await response.Content.ReadAsStringAsync();
    return JsonSerializer.Deserialize<T>(json);
}
```

The equivalent in Python:

```python
async def fetch_json(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status >= 400:
                raise Exception(f"HTTP {response.status}")
            return await response.json()
```

### Error Handling

`try`/`catch` with `async`/`await` works identically across all three languages.

```javascript
try {
  const data = await fetchJson("/api/stats");
  console.log(data);
} catch (error) {
  console.error("Failed:", error.message);
}
```

```csharp
try {
    var data = await FetchJson<Stats>("/api/stats");
} catch (Exception ex) {
    Console.Error.WriteLine($"Failed: {ex.Message}");
}
```

```python
try:
    data = await fetch_json("/api/stats")
except Exception as e:
    print(f"Failed: {e}")
```

---

## 9. Destructuring in Function Parameters

React components commonly receive a single "props" object. Destructuring it in the function signature is idiomatic JavaScript.

### Basic Pattern

```javascript
// Without destructuring — you access props.stats, props.isLoading, etc.
function StatsCards(props) {
  return <div>{props.stats.total}</div>;
}

// With destructuring — cleaner, and you see exactly what data the component uses
function StatsCards({ stats, isLoading }) {
  return <div>{stats.total}</div>;
}
```

This is equivalent to:

```python
# Python — no direct equivalent, but similar to unpacking a dict
def stats_cards(*, stats, is_loading):
    return stats["total"]
```

### Renaming During Destructuring

Sometimes a property name from an API does not match what you want to call it locally.

```javascript
const { data: stats, isLoading, error } = useQuery({
  queryKey: ["stats"],
  queryFn: getStats,
});
// `data` (from useQuery's return value) is now called `stats`
// `isLoading` keeps its original name
// `error` keeps its original name
```

### Default Values in Destructuring

You can provide defaults for properties that might be missing.

```javascript
function LeadCard({ name, score = 0, stage = "New" }) {
  // If score or stage are undefined, the defaults apply
}
```

```python
# Python equivalent
def lead_card(name, score=0, stage="New"):
    pass
```

### The Rest Operator in Parameters (`...`)

The rest operator collects "everything else" into a new object. This is common in wrapper components that pass unknown props through to a child element.

```javascript
function CustomButton({ className, children, ...props }) {
  // className and children are extracted
  // everything else (onClick, disabled, type, etc.) is in `props`
  return <button className={className} {...props}>{children}</button>;
}
```

```python
# Python equivalent
def custom_button(class_name, children, **props):
    # props is a dict of remaining keyword arguments
    pass
```

```csharp
// C# — no direct equivalent; closest is params or Dictionary<string, object>
```

---

## 10. Ternary Expressions and Short-Circuit Rendering

### Ternary Operator

The ternary operator works the same as in C#, with different syntax from Python.

```javascript
// JavaScript
const label = score >= 80 ? "Hot" : "Cold";

// Inside JSX (React template syntax)
{isLoading ? <Spinner /> : <DataTable />}
```

```csharp
// C# — identical syntax
var label = score >= 80 ? "Hot" : "Cold";
```

```python
# Python — reversed word order
label = "Hot" if score >= 80 else "Cold"
```

Nested ternaries from this project for status display:

```javascript
{pipelineStatus?.running ? (
  <><Loader2 className="animate-spin" /> Running...</>
) : (
  <><Play /> Run Pipeline</>
)}
```

The `<>...</>` is a React "fragment" (grouping element that produces no DOM node). `<Loader2 />` and `<Play />` are icon components.

### Short-Circuit Rendering with `&&`

In React, `&&` is used to conditionally render content. If the left side is truthy, the right side is returned. If the left side is falsy, the expression short-circuits and returns the left side (which React ignores).

```javascript
// Only renders the Card if duplicatesData exists AND count > 0
{duplicatesData && duplicatesData.count > 0 && (
  <Card>
    <p>{duplicatesData.count} duplicates found</p>
  </Card>
)}
```

This is conceptually similar to:

```python
# Python
if duplicates_data and duplicates_data.count > 0:
    render_card()
```

```csharp
// C#
if (duplicatesData != null && duplicatesData.Count > 0) {
    RenderCard();
}
```

**Warning:** Be careful with numeric values. `{count && <span>{count}</span>}` will render `0` on screen when count is 0 because `0` is falsy but is still a valid React child. Use `{count > 0 && ...}` or a ternary instead.

---

## 11. URLSearchParams

JavaScript provides a built-in `URLSearchParams` class for constructing query strings. This project uses it to build API URLs with filters.

```javascript
const params = new URLSearchParams();
if (filters.q) params.set("q", filters.q);
if (filters.stage) params.set("stage", filters.stage);
if (filters.county) params.set("county", filters.county);
if (filters.minScore) params.set("minScore", String(filters.minScore));

const query = params.toString();
// "q=pizza&stage=New&county=Davidson&minScore=40"

const url = `${API_BASE}/leads?${query}`;
// "http://localhost:8000/api/leads?q=pizza&stage=New&county=Davidson&minScore=40"
```

The `URLSearchParams` class handles encoding special characters (`&`, `=`, spaces, etc.) automatically.

```csharp
// C# — using QueryString helper or manual string building
var query = $"q={Uri.EscapeDataString(q)}&stage={stage}";
// Or with a query builder library
```

```python
# Python
from urllib.parse import urlencode
query = urlencode({"q": "pizza", "stage": "New", "county": "Davidson"})
```

### Reading Query Parameters

```javascript
const params = new URLSearchParams("q=pizza&stage=New");
params.get("q");          // "pizza"
params.get("stage");      // "New"
params.get("missing");    // null
params.has("q");          // true
```

---

## 12. Key Takeaway: Comprehensive Comparison Table

This table maps the most common concepts across all three languages. Refer back to it as you read the project's frontend code.

| Concept | JavaScript | C# | Python |
|---|---|---|---|
| **Immutable variable** | `const x = 5` | `readonly int x = 5` / `const int x = 5` | `X = 5` (convention) |
| **Mutable variable** | `let x = 5` | `int x = 5` / `var x = 5` | `x = 5` |
| **String interpolation** | `` `Hello ${name}` `` | `$"Hello {name}"` | `f"Hello {name}"` |
| **Null check** | `x === null`, `x == null` | `x == null`, `x is null` | `x is None` |
| **Null coalescing** | `x ?? fallback` | `x ?? fallback` | `x if x is not None else fallback` |
| **Optional chaining** | `obj?.prop` | `obj?.Prop` | `getattr(obj, 'prop', None)` |
| **Arrow function / Lambda** | `(x) => x * 2` | `x => x * 2` | `lambda x: x * 2` |
| **Async function** | `async () => { await ... }` | `async Task Method() { await ... }` | `async def func(): await ...` |
| **Map / Select** | `.map(x => ...)` | `.Select(x => ...)` | `[f(x) for x in ...]` |
| **Filter / Where** | `.filter(x => ...)` | `.Where(x => ...)` | `[x for x in ... if ...]` |
| **Find / FirstOrDefault** | `.find(x => ...)` | `.FirstOrDefault(x => ...)` | `next((x for x if ...), None)` |
| **Any / Some** | `.some(x => ...)` | `.Any(x => ...)` | `any(...)` |
| **All / Every** | `.every(x => ...)` | `.All(x => ...)` | `all(...)` |
| **Reduce / Aggregate** | `.reduce(fn, init)` | `.Aggregate(init, fn)` | `functools.reduce(fn, items, init)` |
| **Sort** | `.sort((a,b) => a - b)` | `.OrderBy(x => x)` | `sorted(items)` |
| **Slice / Take** | `.slice(0, n)` | `.Take(n)` | `items[:n]` |
| **Spread / Unpack** | `{ ...obj }`, `[...arr]` | `record with { }` | `{**d}`, `[*l]` |
| **Destructuring** | `const { a, b } = obj` | `var (a, b) = tuple` | `a, b = tuple` |
| **Ternary** | `c ? a : b` | `c ? a : b` | `a if c else b` |
| **HTTP client** | `fetch(url)` | `HttpClient.GetAsync(url)` | `requests.get(url)` |
| **Promise / Task** | `Promise<T>` | `Task<T>` | `Coroutine` |
| **Import** | `import { x } from "mod"` | `using Namespace` | `from mod import x` |
| **Dict/Object to pairs** | `Object.entries(obj)` | `dict.Select(kvp => ...)` | `dict.items()` |
| **String includes** | `str.includes("sub")` | `str.Contains("sub")` | `"sub" in str` |
| **Array includes** | `arr.includes(x)` | `arr.Contains(x)` | `x in arr` |
| **Console output** | `console.log(x)` | `Console.WriteLine(x)` | `print(x)` |
| **Exception handling** | `try { } catch (e) { }` | `try { } catch (Exception e) { }` | `try: ... except Exception as e:` |
| **Typeof check** | `typeof x === "string"` | `x is string` | `isinstance(x, str)` |
| **For-each loop** | `for (const x of arr)` | `foreach (var x in arr)` | `for x in arr:` |
| **Object keys** | `Object.keys(obj)` | `dict.Keys` | `dict.keys()` |
| **JSON parse** | `JSON.parse(str)` | `JsonSerializer.Deserialize<T>(str)` | `json.loads(str)` |
| **JSON stringify** | `JSON.stringify(obj)` | `JsonSerializer.Serialize(obj)` | `json.dumps(obj)` |

---

## What Comes Next

This document covered the JavaScript language features you will encounter in this project. The next document, [02 - TypeScript Essentials](./02-typescript-essentials.md), builds on this foundation by adding static types. TypeScript is to JavaScript what type hints are to Python — except TypeScript's types are enforced at compile time, much closer to C#'s type system.
