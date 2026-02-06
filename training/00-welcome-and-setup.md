# Welcome & Project Setup

## What This Training Covers

This training teaches Next.js, React, and TypeScript by walking through a real production dashboard homepage -- not toy examples, but the actual code behind a working application. By the end, you will be able to read, modify, and extend a modern frontend codebase with confidence.

The application is the **New Business Locator**, an ETL pipeline dashboard that discovers new businesses in Nashville and Middle Tennessee, scores them for POS-system sales relevance, and manages them as sales leads. The homepage is a dashboard featuring stats cards, interactive charts, a navigation sidebar, and pipeline controls. It is a representative single-page-app surface that exercises every major concept in the stack.

### Training Series

This guide is organized into 10 documents. Each one builds on the last.

| # | Document | Description |
|---|----------|-------------|
| 00 | **Welcome & Setup** (this file) | Project overview, environment setup, and how to use the guide |
| 01 | **JavaScript for C# and Python Developers** | Core JavaScript syntax and idioms mapped to concepts you already know |
| 02 | **TypeScript Essentials** | Static typing, interfaces, generics, and how TypeScript relates to C# |
| 03 | **React Core Concepts** | Components, JSX, props, state, hooks, and the component lifecycle |
| 04 | **Next.js and the App Router** | File-based routing, layouts, server vs. client components, and rendering strategies |
| 05 | **Styling with Tailwind CSS** | Utility-first CSS, responsive design, dark mode, and the glassmorphism design system |
| 06 | **Data Fetching with React Query** | Async state management, caching, refetching, and loading/error states |
| 07 | **Component Libraries (shadcn/ui)** | Pre-built accessible components, Radix UI primitives, and composition patterns |
| 08 | **Data Visualization with Recharts** | Building pie charts, bar charts, and responsive chart containers |
| 09 | **Homepage Complete Walkthrough** | A line-by-line reading of the dashboard page, tying every concept together |

---

## Recommended Reading Order

The documents are numbered intentionally. Follow this progression:

1. **Start with language fundamentals (01-02).** Documents 01 and 02 cover JavaScript and TypeScript. If you are coming from C# and Python, these two will ground you in the syntax and type system before any framework concepts appear. Do not skip them -- React and Next.js code will make far more sense once you are comfortable with arrow functions, destructuring, `async`/`await`, interfaces, and generics.

2. **Move to the framework layer (03-04).** Documents 03 and 04 introduce React and Next.js. React is the component model; Next.js is the framework built on top of it. Understanding components, props, state, and hooks (03) before learning about routing and layouts (04) keeps the learning curve manageable.

3. **Learn the libraries (05-08).** Documents 05 through 08 each cover one library used on the homepage: Tailwind CSS for styling, React Query for data fetching, shadcn/ui for pre-built components, and Recharts for data visualization. These can be read in any order, but the numbered sequence introduces them from most foundational (styling) to most specialized (charts).

4. **Finish with the full walkthrough (09).** Document 09 reads through the homepage file top to bottom, referencing every concept from the prior eight documents. This is where everything clicks into place.

---

## Prerequisites

Before starting, make sure you have the following installed and configured.

### Required Software

- **Node.js v18 or later** -- This is the JavaScript runtime. It includes `npm`, the package manager. Verify with `node --version` and `npm --version`.
- **Python 3.10+** -- Needed for the backend API server. You likely have this already.
- **Git** -- The project repo must be cloned locally.

### Recommended Editor Setup

**VS Code** is strongly recommended. Install these extensions:

- **ESLint** -- Catches JavaScript/TypeScript errors and enforces style rules in real time.
- **Prettier** -- Auto-formats code on save so you do not have to think about indentation or semicolons.
- **Tailwind CSS IntelliSense** -- Autocompletes Tailwind utility classes and shows their CSS on hover. This is indispensable when learning Tailwind.
- **TypeScript** -- VS Code has built-in TypeScript support, but make sure it is enabled. You should see type errors underlined in red as you edit.

### Assumed Knowledge

- Comfortable reading and writing C# or Python
- Basic terminal/command line familiarity (navigating directories, running commands)
- General understanding of HTTP requests and JSON
- No prior JavaScript, TypeScript, React, or Next.js experience required

---

## Project Structure

Here is the layout of the `frontend/` directory. Every file the training references lives here.

```
frontend/
├── app/                        # Next.js App Router pages
│   ├── layout.tsx              # Root layout (wraps every page)
│   ├── page.tsx                # Homepage (the dashboard we study)
│   ├── error.tsx               # Global error boundary
│   ├── globals.css             # Global styles and design tokens
│   ├── favicon.ico             # Browser tab icon
│   ├── fonts/                  # Custom font files (Geist)
│   │   ├── GeistVF.woff
│   │   └── GeistMonoVF.woff
│   ├── leads/page.tsx          # Leads table page
│   ├── kanban/page.tsx         # Kanban board page
│   ├── pipeline/page.tsx       # Pipeline runs page
│   ├── duplicates/page.tsx     # Duplicate detection page
│   └── batch/[id]/page.tsx     # Batch detail page (dynamic route)
├── components/                 # Reusable React components
│   ├── app-shell.tsx           # Main layout shell (sidebar + content area)
│   ├── nav-sidebar.tsx         # Left navigation sidebar
│   ├── stats-cards.tsx         # Stats card grid on the dashboard
│   ├── charts.tsx              # Chart components (pie, bar)
│   ├── providers.tsx           # App-wide context providers
│   ├── lead-table.tsx          # Paginated lead list table
│   ├── lead-detail-panel.tsx   # Slide-out lead detail view
│   ├── lead-filters.tsx        # Filter controls for leads
│   ├── filter-presets.tsx       # Saved filter presets
│   ├── kanban-board.tsx        # Kanban drag-drop board
│   ├── kanban-card.tsx         # Individual kanban card
│   ├── score-badge.tsx         # Color-coded score indicator
│   └── ui/                     # shadcn/ui base components
│       ├── button.tsx
│       ├── card.tsx
│       ├── badge.tsx
│       ├── table.tsx
│       ├── input.tsx
│       ├── select.tsx
│       ├── dialog.tsx
│       ├── sheet.tsx
│       ├── tabs.tsx
│       ├── dropdown-menu.tsx
│       ├── checkbox.tsx
│       ├── radio-group.tsx
│       ├── label.tsx
│       ├── textarea.tsx
│       ├── tooltip.tsx
│       └── sonner.tsx          # Toast notifications
├── lib/                        # Shared utilities and API client
│   ├── api.ts                  # API client functions (fetch wrappers)
│   ├── types.ts                # TypeScript type definitions
│   └── utils.ts                # General utility functions
├── package.json                # Dependencies and npm scripts
├── tailwind.config.ts          # Tailwind CSS configuration
├── tsconfig.json               # TypeScript compiler configuration
├── next.config.mjs             # Next.js framework configuration
└── postcss.config.mjs          # PostCSS configuration (used by Tailwind)
```

### What Each Directory Does

**`app/`** -- This is the Next.js App Router directory. Every file named `page.tsx` inside it becomes a route. For example, `app/leads/page.tsx` serves the `/leads` URL. The `layout.tsx` file defines the shared wrapper (HTML head, fonts, providers) that surrounds every page. If you are familiar with ASP.NET MVC, think of `layout.tsx` as `_Layout.cshtml` and each `page.tsx` as a controller action's view.

**`components/`** -- Reusable UI building blocks. These are React components that get imported into pages. The top-level files (`stats-cards.tsx`, `charts.tsx`, etc.) are feature-specific components. The `ui/` subdirectory contains generic, low-level components from the shadcn/ui library -- buttons, cards, inputs, and so on. In C# terms, `ui/` is like a shared component library, while the top-level files are the application-specific controls that use it.

**`lib/`** -- Shared non-component code. `api.ts` contains functions that call the backend REST API. `types.ts` defines TypeScript interfaces for the data shapes (similar to C# DTOs or Python dataclasses). `utils.ts` holds small helper functions.

**`package.json`** -- The equivalent of a `.csproj` file (C#) or `requirements.txt` (Python). It lists every dependency and defines scripts like `npm run dev`.

**Configuration files** (`tailwind.config.ts`, `tsconfig.json`, `next.config.mjs`, `postcss.config.mjs`) -- These configure the build toolchain. You rarely edit them day-to-day, but understanding what they control helps when debugging build issues.

---

## Running the Project

Open two terminal windows. The frontend and backend run as separate processes.

**Terminal 1 -- Backend API server:**

```bash
# From the project root
uvicorn api.main:app --reload --port 8000
```

This starts the Python FastAPI server on port 8000. The `--reload` flag watches for file changes and restarts automatically. You can verify it is running by visiting `http://localhost:8000/docs` in your browser -- this shows the auto-generated API documentation.

**Terminal 2 -- Frontend development server:**

```bash
# From the project root
cd frontend && npm install   # Only needed the first time, or after dependency changes
npm run dev
```

This starts the Next.js development server on port 3000. Open `http://localhost:3000` in your browser to see the dashboard. The dev server supports hot module replacement -- when you save a file, the browser updates instantly without a full page reload.

**Alternatively**, you can start both servers with a single command:

```bash
# From the project root
./scripts/dev.sh
```

### Verifying Everything Works

Once both servers are running:

1. Open `http://localhost:3000` in your browser.
2. You should see the dashboard with stats cards across the top and charts below.
3. The sidebar on the left should list navigation links (Dashboard, Leads, Kanban, etc.).
4. If the stats show real numbers, the API connection is working. If you see loading spinners that never resolve, check that the backend is running on port 8000.

---

## How to Use This Guide

**Open the actual files.** Each document references specific files from this project with their full paths (for example, `frontend/app/page.tsx`). Open them in your editor alongside the guide. Reading code in context is far more effective than reading excerpts alone.

**Code examples come from the codebase.** The snippets in this training are taken directly from the project source. They are not simplified pseudocode. When a document says "look at line 15 of `stats-cards.tsx`," you can open that file and see exactly the same code.

**Watch for C# and Python comparisons.** Throughout the series, side-by-side comparisons show how JavaScript/TypeScript concepts map to patterns you already know. These look like this:

```csharp
// C# -- defining a data shape
public class Lead
{
    public int Id { get; set; }
    public string Name { get; set; }
    public int Score { get; set; }
}
```

```typescript
// TypeScript -- the equivalent
interface Lead {
  id: number;
  name: string;
  score: number;
}
```

These comparisons appear wherever a concept has a direct analog in C# or Python. They are meant to accelerate your understanding, not to suggest the languages are identical.

**Look for "Key Takeaway" boxes.** Each major section ends with a summary of the most important points. If you are reviewing a document for the second time, these boxes are a quick way to refresh your memory.

> **Key Takeaway:** This guide is designed to be read alongside the source code. Keep your editor open, follow the file references, and experiment by making small changes to see what happens.

---

## Next Steps

Proceed to [01 - JavaScript for C# and Python Developers](./01-javascript-for-csharp-and-python-devs.md) to begin learning the language that powers everything in the `frontend/` directory.
