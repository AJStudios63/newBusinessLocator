# 05 -- Styling with Tailwind CSS

This is document 5 of 10 in a training series for a developer who already knows C# and Python. Documents 01 through 04 covered JavaScript, TypeScript, React, and Next.js. This document covers how styling works in the New Business Locator frontend using Tailwind CSS, and how this project layers a custom glassmorphism design system on top of it.

---

## 1. What is Tailwind CSS?

Tailwind CSS is a **utility-first** CSS framework. Instead of writing named CSS classes that bundle multiple style rules together, you compose many small, single-purpose utility classes directly on your HTML elements.

### Traditional CSS approach

```css
/* styles.css */
.card {
  padding: 24px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

```html
<div class="card">...</div>
```

### Tailwind approach

```html
<div class="p-6 rounded-xl bg-white shadow-md">...</div>
```

No separate CSS file. No inventing class names. The styling lives right on the element.

### Comparison to C# WPF

If you have worked with WPF, think of Tailwind classes as something similar to inline `Style` setters, but with a standardized shorthand vocabulary instead of verbose property names:

```xml
<!-- WPF inline styles -->
<Border Padding="24" CornerRadius="12" Background="White">
    <Border.Effect>
        <DropShadowEffect ShadowDepth="4" Opacity="0.1"/>
    </Border.Effect>
</Border>
```

```html
<!-- Tailwind equivalent -->
<div class="p-6 rounded-xl bg-white shadow-md">...</div>
```

### Why utility-first?

1. **Consistent spacing and colors.** Tailwind enforces a design scale (4px increments for spacing, a curated color palette). You cannot accidentally use `padding: 23px` -- you pick `p-5` (20px) or `p-6` (24px).
2. **No naming problem.** You never have to decide whether to call your class `.card-wrapper`, `.card-container`, or `.card-box`.
3. **No separate CSS files for most things.** The vast majority of styling lives right in your component. You only write custom CSS for effects that Tailwind does not cover out of the box (this project does so for glassmorphism).
4. **Dead code elimination.** Tailwind scans your source files at build time and generates CSS only for classes you actually use. Unused utilities are never shipped.

---

## 2. How to Read Tailwind Classes

Every Tailwind class maps to one (sometimes two) CSS properties. Once you learn the abbreviation system, you can read any Tailwind className the same way you read CSS.

### The Spacing Scale

Tailwind uses a numeric scale where each unit equals 0.25rem (4px at default browser font size):

| Tailwind | rem    | px   |
|----------|--------|------|
| `1`      | 0.25   | 4    |
| `2`      | 0.5    | 8    |
| `3`      | 0.75   | 12   |
| `4`      | 1      | 16   |
| `5`      | 1.25   | 20   |
| `6`      | 1.5    | 24   |
| `8`      | 2      | 32   |
| `10`     | 2.5    | 40   |
| `12`     | 3      | 48   |
| `16`     | 4      | 64   |

Half steps like `2.5` (0.625rem / 10px) and `1.5` (0.375rem / 6px) also exist.

### Spacing Classes

Real examples from the project:

| Class      | CSS equivalent                         | Where used |
|------------|----------------------------------------|------------|
| `p-6`      | `padding: 1.5rem` (24px all sides)    | `CardHeader`, `CardContent`, sidebar logo area |
| `p-5`      | `padding: 1.25rem` (20px all sides)   | Stats cards |
| `p-8`      | `padding: 2rem` (32px all sides)      | Main content area in `AppShell` |
| `px-3`     | `padding-left: 0.75rem; padding-right: 0.75rem` | Nav links, buttons |
| `py-2.5`   | `padding-top: 0.625rem; padding-bottom: 0.625rem` | Nav links |
| `pt-0`     | `padding-top: 0`                      | `CardContent` (`p-6 pt-0` = padding everywhere except top) |
| `pb-4`     | `padding-bottom: 1rem`                | Sidebar logo area |
| `pb-3`     | `padding-bottom: 0.75rem`             | Card headers in dashboard |
| `m-0`      | `margin: 0`                           | Reset margins |
| `mt-1`     | `margin-top: 0.25rem` (4px)           | Subtitle below "Dashboard" heading |
| `mt-3`     | `margin-top: 0.75rem` (12px)          | Value below label in stats cards |
| `mb-1`     | `margin-bottom: 0.25rem` (4px)        | Labels above values in pipeline run info |
| `mb-4`     | `margin-bottom: 1rem` (16px)          | Paragraph before "Review Now" button |
| `mr-2`     | `margin-right: 0.5rem` (8px)          | Icon before button text |
| `ml-auto`  | `margin-left: auto`                   | Active indicator dot pushed to the right |
| `mx-auto`  | `margin-left: auto; margin-right: auto` | Centering the max-width container |
| `gap-4`    | `gap: 1rem` (16px)                    | Grid gap in stats cards |
| `gap-6`    | `gap: 1.5rem` (24px)                  | Grid gap in chart section |
| `gap-2`    | `gap: 0.5rem` (8px)                   | Flex gap in card titles |
| `gap-2.5`  | `gap: 0.625rem` (10px)               | Logo icon and text |
| `gap-3`    | `gap: 0.75rem` (12px)                 | Nav link icon and label |
| `space-y-8`| Adds `margin-top: 2rem` to each child except the first | Main dashboard sections |
| `space-y-1`| Adds `margin-top: 0.25rem` to each child except the first | Nav items |
| `space-y-1.5` | Adds `margin-top: 0.375rem` | Card header inner spacing |

The prefix tells you which direction:
- `p` = padding, `m` = margin
- `x` = horizontal (left + right), `y` = vertical (top + bottom)
- `t` = top, `b` = bottom, `l` = left, `r` = right
- No suffix = all four sides

### Layout Classes

Here is how the main app shell is structured in `app-shell.tsx`:

```tsx
// frontend/components/app-shell.tsx
<div className="flex h-screen bg-background bg-mesh">
  <NavSidebar />
  <main className="flex-1 overflow-auto custom-scrollbar p-8">
    <div className="max-w-[1440px] mx-auto">
      {children}
    </div>
  </main>
</div>
```

Breaking that down:

| Class             | CSS equivalent                               | Purpose |
|-------------------|----------------------------------------------|---------|
| `flex`            | `display: flex`                              | Side-by-side layout (sidebar + main) |
| `h-screen`        | `height: 100vh`                             | Fill the entire viewport height |
| `flex-1`          | `flex: 1 1 0%`                              | Main area takes all remaining width after sidebar |
| `overflow-auto`   | `overflow: auto`                            | Scroll when content exceeds viewport |
| `max-w-[1440px]`  | `max-width: 1440px`                         | Cap content width on ultra-wide screens |
| `mx-auto`         | `margin-left: auto; margin-right: auto`     | Center the capped-width container |

The `[1440px]` syntax is Tailwind's **arbitrary value** escape hatch. When the built-in scale does not have the value you need, wrap a literal CSS value in square brackets.

More layout classes used in the project:

| Class             | CSS equivalent                               | Used in |
|-------------------|----------------------------------------------|---------|
| `flex-col`        | `flex-direction: column`                    | Sidebar (stacked vertically) |
| `items-center`    | `align-items: center`                       | Nav links (vertically center icon + text) |
| `justify-between` | `justify-content: space-between`            | Dashboard header (title left, button right) |
| `justify-center`  | `justify-content: center`                   | Centering spinner in loading state |
| `grid`            | `display: grid`                             | Stats cards, chart layout |
| `grid-cols-2`     | `grid-template-columns: repeat(2, minmax(0, 1fr))` | Pipeline run info (2-column grid) |
| `w-64`            | `width: 16rem` (256px)                      | Sidebar width |
| `w-full`          | `width: 100%`                               | Theme toggle button |
| `h-64`            | `height: 16rem` (256px)                     | Loading spinner container |
| `inline-flex`     | `display: inline-flex`                      | Buttons, badges |

### Typography Classes

From the dashboard page header in `page.tsx`:

```tsx
<h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
<p className="text-muted-foreground mt-1">
  Monitor your lead pipeline and business intelligence
</p>
```

| Class              | CSS equivalent                    | Purpose |
|--------------------|-----------------------------------|---------|
| `text-3xl`         | `font-size: 1.875rem` (30px)    | Page headings |
| `text-base`        | `font-size: 1rem` (16px)        | Card titles, sidebar brand name |
| `text-sm`          | `font-size: 0.875rem` (14px)    | Nav links, card descriptions, body text |
| `text-xs`          | `font-size: 0.75rem` (12px)     | Small buttons, badge text, labels |
| `text-[10px]`      | `font-size: 10px`               | "Lead Generation" subtitle, "Navigation" label |
| `font-bold`        | `font-weight: 700`              | Page headings, stat values |
| `font-semibold`    | `font-weight: 600`              | Card titles, badge text, section labels |
| `font-medium`      | `font-weight: 500`              | Nav links, data values |
| `tracking-tight`   | `letter-spacing: -0.025em`      | Headings (tighter looks more polished at large sizes) |
| `tracking-wider`   | `letter-spacing: 0.05em`        | "Started", "Status" labels in run info |
| `tracking-widest`  | `letter-spacing: 0.1em`         | "LEAD GENERATION", "NAVIGATION" micro-labels |
| `uppercase`        | `text-transform: uppercase`      | Micro-labels |
| `capitalize`       | `text-transform: capitalize`     | Pipeline status text |
| `leading-none`     | `line-height: 1`                | Card titles (no extra line spacing) |
| `whitespace-nowrap`| `white-space: nowrap`            | Prevent button text from wrapping |

### Color Classes

Tailwind generates color utilities from the theme configuration. This project defines custom semantic colors in `tailwind.config.ts`, so instead of `text-blue-500` you write `text-primary` and the actual blue value comes from a CSS variable.

| Class                  | What it does                        | Used for |
|------------------------|-------------------------------------|----------|
| `text-foreground`      | Main text color                    | Default body text |
| `text-muted-foreground`| Dimmer text                        | Labels, secondary text, nav links |
| `text-primary`         | Brand blue                         | Loading spinner, clock icon |
| `text-white`           | White (#fff)                       | Text on gradient backgrounds |
| `text-warning`         | Amber/yellow                       | Warning icons, warning badges |
| `text-success`         | Green                              | Success icons, success badges |
| `text-blue-400`        | Built-in Tailwind blue             | Stats card icon |
| `text-purple-400`      | Built-in Tailwind purple           | Stats card icon |
| `text-emerald-400`     | Built-in Tailwind emerald          | Stats card icon |
| `text-amber-400`       | Built-in Tailwind amber            | Stats card icon |
| `bg-background`        | Main page background               | App shell |
| `bg-primary`           | Brand blue as background           | Highlighted elements |
| `bg-white`             | White background                   | Light mode cards |
| `bg-secondary`         | Secondary surface color            | Secondary buttons |
| `bg-destructive`       | Red                                | Delete/destructive buttons |

**Opacity modifier syntax** -- Tailwind lets you append a slash and a number to any color class to set its opacity:

| Class              | What it does                                      | Used for |
|--------------------|---------------------------------------------------|----------|
| `bg-warning/15`    | Warning color at 15% opacity                     | Warning badge background |
| `bg-success/15`    | Success color at 15% opacity                     | Success badge background |
| `bg-info/15`       | Info color at 15% opacity                        | Info badge background |
| `bg-primary/15`    | Primary color at 15% opacity                     | Icon containers |
| `bg-accent/10`     | Accent color at 10% opacity                      | Hover background on nav links |
| `border-border/50` | Border color at 50% opacity                      | Theme toggle divider |
| `border-warning/20`| Warning color border at 20% opacity              | Duplicates card |
| `bg-white/70`      | White at 70% opacity                             | Active nav indicator dot |

This is one of the reasons the project defines HSL values without the `hsl()` wrapper in CSS variables -- it allows Tailwind to inject the opacity. More on that in section 6.

### Border and Rounding Classes

| Class          | CSS equivalent                    | Used for |
|----------------|-----------------------------------|----------|
| `border`       | `border-width: 1px`             | General borders (the color comes from the global `border-border` reset) |
| `border-t`     | `border-top-width: 1px`         | Theme toggle area top border |
| `border-r-0`   | `border-right-width: 0`         | Sidebar (no right border) |
| `border-transparent` | `border-color: transparent` | Badges (need border for spacing but invisible) |
| `rounded-xl`   | `border-radius: 0.75rem` (12px) | Cards, stats panels |
| `rounded-lg`   | `border-radius: 0.5rem` (8px)  | Buttons, nav links, icon containers |
| `rounded-md`   | `border-radius: calc(0.75rem - 2px)` | Small buttons |
| `rounded-full`  | `border-radius: 9999px`        | Badges (pill shape), active nav dot |
| `rounded-none`  | `border-radius: 0`             | Sidebar (flush with viewport edge) |

### Sizing Classes

| Class   | CSS equivalent              | Used for |
|---------|-----------------------------|----------|
| `h-4`   | `height: 1rem` (16px)      | Icons inside nav links |
| `w-4`   | `width: 1rem` (16px)       | Icons inside nav links |
| `h-8`   | `height: 2rem` (32px)      | Icon containers, small buttons |
| `w-8`   | `width: 2rem` (32px)       | Icon containers |
| `h-9`   | `height: 2.25rem` (36px)   | Default button height, icon-only button |
| `w-9`   | `width: 2.25rem` (36px)    | Icon-only button (square) |
| `h-10`  | `height: 2.5rem` (40px)    | Large button |
| `h-1.5` | `height: 0.375rem` (6px)   | Active nav indicator dot |
| `w-1.5` | `width: 0.375rem` (6px)    | Active nav indicator dot |
| `h-3.5` | `height: 0.875rem` (14px)  | Small icons in status text |
| `w-3.5` | `width: 0.875rem` (14px)   | Small icons in status text |
| `size-4`| `width: 1rem; height: 1rem` | SVG icons inside buttons (via `[&_svg]:size-4`) |

### Miscellaneous Classes

| Class             | CSS equivalent                          | Used for |
|-------------------|-----------------------------------------|----------|
| `overflow-auto`   | `overflow: auto`                       | Scrollable main area |
| `cursor-pointer`  | `cursor: pointer`                      | Clickable elements |
| `animate-spin`    | Continuous 360-degree rotation          | Loading spinner (`Loader2` icon) |
| `animate-slide-in`| Slide up 8px + fade in over 0.3s (custom) | Stats cards entrance |
| `transition-all`  | `transition-property: all`             | Smooth property changes |
| `duration-200`    | `transition-duration: 200ms`           | Nav links, buttons |
| `duration-300`    | `transition-duration: 300ms`           | Cards |
| `shadow-md`       | Medium box shadow                      | Active nav link, gradient buttons |
| `shadow-sm`       | Small box shadow                       | Badges, secondary buttons |
| `shadow-lg`       | Large box shadow                       | Button hover state |
| `antialiased`     | `-webkit-font-smoothing: antialiased`  | Body text rendering |
| `shrink-0`        | `flex-shrink: 0`                       | Prevent icons from compressing |
| `pointer-events-none` | `pointer-events: none`            | SVGs inside buttons, disabled state |

---

## 3. Responsive Design

Tailwind uses a **mobile-first** approach. Base classes (with no prefix) apply at all screen sizes. Prefixed classes apply at that breakpoint **and above**.

| Prefix | Min-width | Typical device |
|--------|-----------|---------------|
| (none) | 0px       | Mobile phones  |
| `sm:`  | 640px     | Large phones   |
| `md:`  | 768px     | Tablets        |
| `lg:`  | 1024px    | Desktops       |
| `xl:`  | 1280px    | Large desktops |
| `2xl:` | 1536px    | Ultra-wide     |

### Real example from the project

The stats cards grid in `stats-cards.tsx`:

```tsx
<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
  {statConfig.map((stat) => (
    <div key={stat.key} className="glass glow-hover rounded-xl p-5 ...">
      ...
    </div>
  ))}
</div>
```

How this reads:

| Screen width  | Active classes            | Result |
|---------------|---------------------------|--------|
| 0 -- 767px    | `grid gap-4`             | Single column (default grid is 1 column), 16px gap |
| 768 -- 1023px | + `md:grid-cols-2`       | Two columns |
| 1024px+       | + `lg:grid-cols-4`       | Four columns |

The chart grid on the dashboard (`page.tsx`):

```tsx
<div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
```

| Screen width  | Result |
|---------------|--------|
| 0 -- 767px    | 1 column, 24px gap |
| 768 -- 1023px | 2 columns |
| 1024px+       | 3 columns |

### Comparison to C# WPF and traditional CSS

In WPF, you would use `VisualStateManager` or `AdaptiveTrigger` to change layout at different window sizes. In plain CSS, you write `@media` queries:

```css
/* Traditional CSS */
.stats-grid {
  display: grid;
  gap: 16px;
}
@media (min-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .stats-grid { grid-template-columns: repeat(4, 1fr); }
}
```

Tailwind compiles `md:grid-cols-2 lg:grid-cols-4` into exactly those same media queries -- you just never have to write them by hand.

---

## 4. Dark Mode

Tailwind has a built-in `dark:` prefix that applies styles only when dark mode is active.

This project uses **class-based** dark mode, configured in `tailwind.config.ts`:

```typescript
// frontend/tailwind.config.ts
const config: Config = {
  darkMode: ["class"],
  // ...
};
```

This means dark mode activates when the `<html>` element has `class="dark"`:

```tsx
// frontend/app/layout.tsx
<html lang="en" className="dark" suppressHydrationWarning>
```

The `next-themes` library (used via `useTheme()` in the sidebar) toggles this class at runtime, and the `dark` default in `layout.tsx` ensures dark mode on first load.

### How the `dark:` prefix works

You can write:

```html
<div class="bg-white dark:bg-slate-900 text-black dark:text-white">
```

When `<html>` has `class="dark"`, the `dark:` variants activate. When it does not, the base variants apply.

### This project's approach

In practice, this project does **not** use `dark:` prefixed utility classes very often. Instead, it uses CSS custom properties that change between light and dark. All of the semantic color tokens (`--background`, `--foreground`, `--primary`, etc.) have separate values defined under `:root` (light) and `.dark` (dark) in `globals.css`. When you write `text-foreground`, Tailwind resolves it to `hsl(var(--foreground))`, and the variable itself changes depending on whether `.dark` is on `<html>`.

This pattern means you write each class name once and it automatically adapts to both themes. The `dark:` prefix is still available when you need a specific override, but the custom property approach handles the common case more cleanly.

---

## 5. Hover, Focus, and Other States

Tailwind uses **variant prefixes** for interactive states. The prefix goes before the utility class, separated by a colon.

### Real examples from the project

**Hover states** on nav links (from `nav-sidebar.tsx`):

```tsx
"text-muted-foreground hover:text-foreground hover:bg-accent/10"
```

| Class                    | CSS equivalent                                           |
|--------------------------|----------------------------------------------------------|
| `hover:text-foreground`  | `&:hover { color: hsl(var(--foreground)); }`            |
| `hover:bg-accent/10`    | `&:hover { background: hsl(var(--accent) / 0.1); }`    |
| `hover:opacity-80`      | `&:hover { opacity: 0.8; }`                             |
| `hover:shadow-lg`       | `&:hover { box-shadow: (large shadow); }`               |
| `hover:brightness-110`  | `&:hover { filter: brightness(1.1); }`                  |
| `hover:underline`       | `&:hover { text-decoration: underline; }`               |
| `hover:bg-destructive/90`| `&:hover { background: hsl(var(--destructive) / 0.9); }`|
| `hover:border-accent/30`| `&:hover { border-color: hsl(var(--accent) / 0.3); }`  |

**Focus states** on buttons (from `button.tsx`):

```tsx
"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
```

| Class                              | What it does |
|------------------------------------|-------------|
| `focus-visible:outline-none`       | Remove browser's default focus outline |
| `focus-visible:ring-2`             | Add a 2px ring (box-shadow based, not border) |
| `focus-visible:ring-ring`          | Ring color from `--ring` variable |
| `focus-visible:ring-offset-2`      | 2px gap between ring and element |
| `focus-visible:ring-offset-background` | Gap color matches page background |

`focus-visible` only triggers on keyboard navigation (Tab key), not on mouse clicks. This keeps the UI clean for mouse users while remaining accessible for keyboard users.

**Disabled states** on buttons (from `button.tsx`):

```tsx
"disabled:pointer-events-none disabled:opacity-50"
```

| Class                        | CSS equivalent                       | Purpose |
|------------------------------|--------------------------------------|---------|
| `disabled:pointer-events-none`| `&:disabled { pointer-events: none; }` | No clicks or hovers |
| `disabled:opacity-50`        | `&:disabled { opacity: 0.5; }`       | Visually dimmed |

**Active (pressed) state** on buttons:

```tsx
"active:brightness-95"
```

This slightly dims the button when clicked/pressed, giving tactile feedback.

### Child selectors

Tailwind supports arbitrary selectors. The button component uses this to style SVG icons inside it:

```tsx
"[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0"
```

`[&_svg]` means "any `<svg>` descendant of this element." This ensures all icons inside a button are 16x16, cannot be clicked independently, and do not shrink when space is tight.

---

## 6. CSS Custom Properties (Design Tokens)

Open `frontend/app/globals.css` and you will see two blocks of CSS variables -- one under `:root` (light mode) and one under `.dark` (dark mode). These are the project's **design tokens**.

### Light mode tokens (abbreviated)

```css
/* frontend/app/globals.css */
:root {
  --background: 220 20% 97%;         /* Light gray */
  --foreground: 224 71% 4%;          /* Near-black */
  --primary: 226 70% 55%;            /* Brand blue */
  --primary-foreground: 0 0% 100%;   /* White (text on blue buttons) */
  --muted-foreground: 220 9% 46%;    /* Gray (labels, secondary text) */
  --border: 220 13% 88%;             /* Light gray border */
  --success: 152 60% 42%;            /* Green */
  --warning: 38 92% 50%;             /* Amber */
  --info: 217 91% 60%;               /* Light blue */
  --radius: 0.75rem;                 /* Default border radius */
}
```

### Dark mode tokens (abbreviated)

```css
.dark {
  --background: 224 47% 7%;          /* Deep dark blue */
  --foreground: 213 31% 91%;         /* Light gray text */
  --primary: 226 70% 60%;            /* Brighter brand blue */
  --muted-foreground: 218 11% 55%;   /* Dimmer text */
  --border: 223 30% 16%;             /* Subtle dark border */
  --success: 152 55% 48%;            /* Slightly brighter green */
  --warning: 38 85% 55%;             /* Slightly brighter amber */
  --info: 217 85% 65%;               /* Slightly brighter blue */
}
```

### Why HSL values without `hsl()`?

Notice the values are bare numbers like `226 70% 60%` instead of `hsl(226, 70%, 60%)`. This is deliberate. In `tailwind.config.ts`, these variables are wrapped with `hsl()`:

```typescript
// frontend/tailwind.config.ts
colors: {
  primary: {
    DEFAULT: 'hsl(var(--primary))',
    foreground: 'hsl(var(--primary-foreground))'
  },
  // ...
}
```

By storing the raw HSL components, Tailwind can inject an alpha channel for the opacity modifier syntax. When you write `bg-primary/15`, Tailwind generates:

```css
background-color: hsl(var(--primary) / 0.15);
```

If the variable already contained `hsl(226, 70%, 60%)`, this would not work because you would end up with `hsl(hsl(226, 70%, 60%) / 0.15)` -- invalid CSS. The "raw values + wrapper in config" pattern is what makes `bg-primary/15` possible.

### How it all connects

Here is the chain from CSS variable to rendered pixel:

1. `globals.css` defines `--primary: 226 70% 60%;` under `.dark`
2. `tailwind.config.ts` maps `primary` to `hsl(var(--primary))`
3. You write `text-primary` in a component
4. Tailwind generates `color: hsl(var(--primary))` in the compiled CSS
5. The browser resolves `var(--primary)` to `226 70% 60%` and computes the final color

To switch themes, the `next-themes` library toggles the `dark` class on `<html>`. The CSS variables change, and every element that references them updates automatically. No JavaScript re-render is needed for the color change itself -- it is pure CSS.

### Why this matters

In a C# WPF application, you would define a `ResourceDictionary` with named `SolidColorBrush` resources and swap dictionaries for theming. This is the same idea: named tokens with swappable values. The advantage in CSS is that the browser handles the swap natively through the cascade.

---

## 7. Glassmorphism Design System

This project layers a custom "glassmorphism" design on top of Tailwind. Glassmorphism is a visual style where panels appear to be made of frosted glass -- semi-transparent with a blur effect on whatever is behind them.

### Glass tokens

Both light and dark modes define glass-specific variables:

```css
/* Light mode */
:root {
  --glass-bg: 0 0% 100% / 0.7;        /* White at 70% opacity */
  --glass-border: 0 0% 100% / 0.3;    /* White at 30% opacity */
  --glass-blur: 16px;
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
}

/* Dark mode */
.dark {
  --glass-bg: 224 47% 12% / 0.6;      /* Dark blue at 60% opacity */
  --glass-border: 224 30% 20% / 0.4;  /* Slightly lighter at 40% opacity */
  --glass-blur: 20px;
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
```

### The `.glass` classes

Defined in `globals.css` under `@layer components`:

```css
/* frontend/app/globals.css */

/* Standard glass panel */
.glass {
  background: hsl(var(--glass-bg));
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid hsl(var(--glass-border));
  box-shadow: var(--glass-shadow);
}

/* Stronger glass: more blur + subtle inset highlight on top edge */
.glass-strong {
  background: hsl(var(--glass-bg));
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid hsl(var(--glass-border));
  box-shadow: var(--glass-shadow), inset 0 1px 0 0 hsl(0 0% 100% / 0.05);
}

/* Subtle glass: less blur, for nested panels */
.glass-subtle {
  background: hsl(var(--glass-bg));
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid hsl(var(--glass-border));
}
```

The key CSS property here is `backdrop-filter: blur()`. It blurs whatever is rendered *behind* the element (not the element's own content). Combined with a semi-transparent background, it creates the frosted glass effect.

`-webkit-backdrop-filter` is the Safari-prefixed version, required for iOS and older macOS Safari.

### Where glass is used

The `Card` component (`frontend/components/ui/card.tsx`) applies `glass` by default:

```tsx
// frontend/components/ui/card.tsx
const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-xl glass glow-hover transition-all duration-300",
        className
      )}
      {...props}
    />
  )
);
```

Every `<Card>` in the application gets the glass effect, glow on hover, rounded corners, and smooth transitions automatically.

The sidebar uses `glass-strong` for more prominence:

```tsx
// frontend/components/nav-sidebar.tsx
<aside className="w-64 flex flex-col glass-strong border-r-0 border-l-0 border-t-0 border-b-0 rounded-none">
```

The outline button variant uses `glass-subtle`:

```tsx
// frontend/components/ui/button.tsx (outline variant)
"border border-border glass-subtle hover:bg-accent/10 hover:border-accent/30 hover:text-accent-foreground"
```

### Background mesh

The `bg-mesh` class creates a subtle colored radial gradient behind all content. This is what gives the glass panels something to blur against:

```css
/* frontend/app/globals.css */
.bg-mesh {
  background-image:
    radial-gradient(at 20% 20%, hsl(226 70% 55% / 0.08) 0px, transparent 50%),
    radial-gradient(at 80% 80%, hsl(262 60% 58% / 0.06) 0px, transparent 50%),
    radial-gradient(at 50% 0%, hsl(200 80% 60% / 0.05) 0px, transparent 50%);
}

.dark .bg-mesh {
  background-image:
    radial-gradient(at 20% 20%, hsl(226 70% 55% / 0.15) 0px, transparent 50%),
    radial-gradient(at 80% 80%, hsl(262 60% 58% / 0.12) 0px, transparent 50%),
    radial-gradient(at 50% 0%, hsl(200 80% 60% / 0.08) 0px, transparent 50%);
}
```

Three overlapping radial gradients (blue, purple, cyan) at different positions create a soft, colorful backdrop. In dark mode, the gradients are more visible (higher opacity) because they show through the glass panels more.

Applied in `app-shell.tsx`:

```tsx
<div className="flex h-screen bg-background bg-mesh">
```

### Accent gradient

The `bg-accent-gradient` class creates a blue-to-purple linear gradient, used for primary buttons and active nav links:

```css
.bg-accent-gradient {
  background: linear-gradient(135deg, hsl(var(--accent-gradient-from)), hsl(var(--accent-gradient-to)));
}
```

The `text-gradient` class applies the same gradient to text:

```css
.text-gradient {
  background: linear-gradient(135deg, hsl(var(--accent-gradient-from)), hsl(var(--accent-gradient-to)));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

This works by painting the gradient as the text's background, then clipping the background to only show through the text glyphs.

### Glow hover

Cards emit a subtle blue glow when hovered:

```css
.glow-hover {
  transition: box-shadow 0.3s ease;
}
.glow-hover:hover {
  box-shadow: 0 0 20px hsl(226 70% 55% / 0.15), var(--glass-shadow);
}
.dark .glow-hover:hover {
  box-shadow: 0 0 30px hsl(226 70% 55% / 0.2), var(--glass-shadow);
}
```

In dark mode, the glow is larger (30px spread vs 20px) and more opaque (0.2 vs 0.15) because it is more visible against the dark background.

### Custom scrollbar

```css
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.5);
}
```

This replaces the browser's default thick scrollbar with a thin 6px one that matches the design. Applied to the main content area.

---

## 8. The `cn()` Utility Function

Every component in this project imports `cn` from `@/lib/utils`. It is a small but critical function:

```typescript
// frontend/lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

This function does two things in sequence:

### Step 1: `clsx` -- conditional class joining

`clsx` takes any mix of strings, objects, arrays, and falsy values and joins the truthy ones into a single class string.

```typescript
clsx("base", false && "skip", undefined, "keep")
// Result: "base keep"

clsx("base", isActive && "active", !isActive && "inactive")
// if isActive is true:  "base active"
// if isActive is false: "base inactive"
```

This is how the project does conditional styling without ternary operators in every className:

```tsx
cn("flex items-center gap-3", isActive && "bg-accent-gradient text-white")
```

### Step 2: `tailwind-merge` -- conflict resolution

When two Tailwind classes target the same CSS property, `tailwind-merge` keeps only the last one:

```typescript
twMerge("px-2 py-1 px-4")
// Result: "py-1 px-4"   (px-2 is removed because px-4 overrides it)

twMerge("text-sm text-lg")
// Result: "text-lg"      (text-sm is removed)
```

This matters because components accept a `className` prop that gets merged with their defaults. Without `tailwind-merge`, both classes would be in the HTML and the result would depend on CSS source order (which is non-obvious with Tailwind). With `tailwind-merge`, the caller's class always wins:

```tsx
// Card component default: "rounded-xl glass glow-hover transition-all duration-300"
// Caller passes: className="rounded-none"

cn("rounded-xl glass glow-hover transition-all duration-300", "rounded-none")
// Result: "glass glow-hover transition-all duration-300 rounded-none"
// rounded-xl is removed because rounded-none overrides it
```

### Where it is used

Virtually every shadcn/ui component follows this pattern:

```tsx
const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  )
);
```

The component has default classes (`p-6 pt-0`), and the caller can override or extend them via the `className` prop. `cn()` merges them intelligently.

### Comparison to C#

In C# WPF, when you set a `Style` on an element, properties from the style and properties set directly on the element merge with direct-set values winning. `cn()` achieves the same precedence rule for Tailwind classes.

---

## 9. Reading a Complete Example

Here is the nav link from `nav-sidebar.tsx`. Let us break down every single class:

```tsx
// frontend/components/nav-sidebar.tsx (lines 60-75)
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
```

### Base classes (always applied)

| Class           | CSS                                     | Purpose |
|-----------------|-----------------------------------------|---------|
| `flex`          | `display: flex`                        | Horizontal layout for icon + text + dot |
| `items-center`  | `align-items: center`                  | Vertically center icon with text |
| `gap-3`         | `gap: 0.75rem` (12px)                 | Space between icon, label, and dot |
| `rounded-lg`    | `border-radius: 0.5rem` (8px)         | Rounded corners on the link |
| `px-3`          | `padding-left/right: 0.75rem` (12px)  | Horizontal padding inside the link |
| `py-2.5`        | `padding-top/bottom: 0.625rem` (10px) | Vertical padding inside the link |
| `text-sm`       | `font-size: 0.875rem` (14px)          | Standard nav text size |
| `font-medium`   | `font-weight: 500`                    | Medium weight (not bold, not regular) |
| `transition-all`| `transition-property: all`             | Animate any property change |
| `duration-200`  | `transition-duration: 200ms`           | Animation takes 200 milliseconds |

### When active (`isActive` is true)

| Class              | CSS                                              | Purpose |
|--------------------|--------------------------------------------------|---------|
| `bg-accent-gradient`| `background: linear-gradient(135deg, blue, purple)` | Gradient background highlights the active page |
| `text-white`       | `color: #fff`                                    | White text contrasts against gradient |
| `shadow-md`        | Medium box shadow                                | Lifts the active link off the surface |

### When inactive (`isActive` is false)

| Class                      | CSS                                                  | Purpose |
|----------------------------|------------------------------------------------------|---------|
| `text-muted-foreground`    | Dimmer gray text                                    | De-emphasizes non-active links |
| `hover:text-foreground`    | On hover: switch to full-brightness text            | Visual feedback |
| `hover:bg-accent/10`       | On hover: 10% opacity accent background             | Subtle highlight without being loud |

### Icon classes

```tsx
<Icon className="h-4 w-4" />
```

16px by 16px. Simple and consistent for all nav icons.

### Active indicator dot

```tsx
<div className="ml-auto h-1.5 w-1.5 rounded-full bg-white/70" />
```

| Class          | Purpose |
|----------------|---------|
| `ml-auto`      | Push the dot to the far right (flex auto-margin trick) |
| `h-1.5 w-1.5` | 6px by 6px -- a tiny dot |
| `rounded-full` | Perfect circle |
| `bg-white/70`  | White at 70% opacity -- visible but subtle |

### The visual result

- **Inactive link:** Gray text, no background. On hover, text brightens and a faint blue tint appears behind it. Transitions smoothly over 200ms.
- **Active link:** Blue-to-purple gradient background, white text, elevated with a shadow. A tiny white dot appears on the right edge to mark it as current. The transition from inactive to active animates smoothly.

---

## 10. Custom Animations

Tailwind includes a few built-in animations (`animate-spin`, `animate-pulse`, `animate-bounce`, `animate-ping`), but this project defines additional custom ones.

### Animation definitions

In `tailwind.config.ts`, custom keyframes and animations are registered:

```typescript
// frontend/tailwind.config.ts
keyframes: {
  'shimmer': {
    '0%': { backgroundPosition: '-200% 0' },
    '100%': { backgroundPosition: '200% 0' },
  },
  'float': {
    '0%, 100%': { transform: 'translateY(0)' },
    '50%': { transform: 'translateY(-4px)' },
  },
  'pulse-glow': {
    '0%, 100%': { opacity: '0.6' },
    '50%': { opacity: '1' },
  },
  'slide-in': {
    '0%': { opacity: '0', transform: 'translateY(8px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  },
},
animation: {
  'shimmer': 'shimmer 2s linear infinite',
  'float': 'float 3s ease-in-out infinite',
  'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
  'slide-in': 'slide-in 0.3s ease-out',
},
```

### What each animation does

| Animation class       | Duration | Repeats?   | Effect |
|-----------------------|----------|------------|--------|
| `animate-shimmer`     | 2s       | Infinite   | Sweeps background position left-to-right, creating a shimmering loading effect |
| `animate-float`       | 3s       | Infinite   | Gently bobs the element up 4px and back down |
| `animate-pulse-glow`  | 2s       | Infinite   | Fades opacity between 60% and 100%, creating a pulsing glow |
| `animate-slide-in`    | 0.3s     | Once       | Slides the element up 8px while fading in -- used for entrance effects |
| `animate-spin`        | (built-in) | Infinite | Continuous 360-degree rotation -- used for the `Loader2` spinner icon |

### Usage in the project

Stats cards use `animate-slide-in` for their entrance:

```tsx
// frontend/components/stats-cards.tsx
<div className="glass glow-hover rounded-xl p-5 transition-all duration-300 animate-slide-in">
```

When stats cards first render, they slide up 8px and fade in over 300ms, giving the dashboard a polished feel.

The loading spinner uses the built-in `animate-spin`:

```tsx
// frontend/app/page.tsx
<Loader2 className="h-8 w-8 animate-spin text-primary" />
```

### Duplicate keyframes in globals.css

The same keyframes are also defined in `globals.css` as regular CSS `@keyframes` rules. This is because the glassmorphism classes reference them in CSS. Both definitions work -- the Tailwind config makes them available as utility classes (`animate-shimmer`), and the CSS definitions ensure they work inside custom component classes.

### How to define your own

If you need a new animation:

1. Define the `@keyframes` in `tailwind.config.ts` under `theme.extend.keyframes`
2. Register it under `theme.extend.animation` with timing, easing, and repeat settings
3. Use it as `animate-yourname` in any className

---

## Quick Reference

The most commonly used Tailwind classes in this project, with their CSS equivalents:

### Spacing

| Tailwind   | CSS                                              |
|------------|--------------------------------------------------|
| `p-6`      | `padding: 1.5rem`                               |
| `p-5`      | `padding: 1.25rem`                              |
| `p-8`      | `padding: 2rem`                                 |
| `px-3`     | `padding-left: 0.75rem; padding-right: 0.75rem` |
| `py-2.5`   | `padding-top: 0.625rem; padding-bottom: 0.625rem` |
| `pt-0`     | `padding-top: 0`                                |
| `mt-1`     | `margin-top: 0.25rem`                           |
| `mt-3`     | `margin-top: 0.75rem`                           |
| `mb-1`     | `margin-bottom: 0.25rem`                        |
| `mb-4`     | `margin-bottom: 1rem`                           |
| `mr-2`     | `margin-right: 0.5rem`                          |
| `ml-auto`  | `margin-left: auto`                             |
| `mx-auto`  | `margin-left: auto; margin-right: auto`         |
| `gap-3`    | `gap: 0.75rem`                                  |
| `gap-4`    | `gap: 1rem`                                     |
| `gap-6`    | `gap: 1.5rem`                                   |
| `space-y-1`| `> * + * { margin-top: 0.25rem }`               |
| `space-y-8`| `> * + * { margin-top: 2rem }`                  |

### Layout

| Tailwind            | CSS                                           |
|---------------------|-----------------------------------------------|
| `flex`              | `display: flex`                              |
| `inline-flex`       | `display: inline-flex`                       |
| `flex-1`            | `flex: 1 1 0%`                               |
| `flex-col`          | `flex-direction: column`                     |
| `items-center`      | `align-items: center`                        |
| `justify-between`   | `justify-content: space-between`             |
| `justify-center`    | `justify-content: center`                    |
| `grid`              | `display: grid`                              |
| `grid-cols-2`       | `grid-template-columns: repeat(2, 1fr)`      |
| `md:grid-cols-2`    | `@media (min-width: 768px) { grid-template-columns: repeat(2, 1fr) }` |
| `lg:grid-cols-4`    | `@media (min-width: 1024px) { grid-template-columns: repeat(4, 1fr) }` |
| `h-screen`          | `height: 100vh`                              |
| `w-64`              | `width: 16rem`                               |
| `w-full`            | `width: 100%`                                |
| `max-w-[1440px]`    | `max-width: 1440px`                          |
| `overflow-auto`     | `overflow: auto`                             |
| `shrink-0`          | `flex-shrink: 0`                             |

### Typography

| Tailwind          | CSS                                  |
|-------------------|--------------------------------------|
| `text-3xl`        | `font-size: 1.875rem` (30px)        |
| `text-base`       | `font-size: 1rem` (16px)            |
| `text-sm`         | `font-size: 0.875rem` (14px)        |
| `text-xs`         | `font-size: 0.75rem` (12px)         |
| `text-[10px]`     | `font-size: 10px`                   |
| `font-bold`       | `font-weight: 700`                  |
| `font-semibold`   | `font-weight: 600`                  |
| `font-medium`     | `font-weight: 500`                  |
| `tracking-tight`  | `letter-spacing: -0.025em`          |
| `tracking-wider`  | `letter-spacing: 0.05em`            |
| `tracking-widest` | `letter-spacing: 0.1em`             |
| `uppercase`       | `text-transform: uppercase`          |
| `capitalize`      | `text-transform: capitalize`         |
| `leading-none`    | `line-height: 1`                    |
| `whitespace-nowrap`| `white-space: nowrap`               |

### Colors (project theme)

| Tailwind              | Resolves to                        |
|-----------------------|------------------------------------|
| `text-foreground`     | Main text color (near-black/light gray) |
| `text-muted-foreground`| Dimmer text (gray)                |
| `text-primary`        | Brand blue                         |
| `text-white`          | `#ffffff`                          |
| `text-warning`        | Amber                              |
| `text-success`        | Green                              |
| `bg-background`       | Main page background               |
| `bg-primary`          | Brand blue                         |
| `bg-accent-gradient`  | Blue-to-purple gradient (custom)   |
| `bg-warning/15`       | Warning color at 15% opacity       |
| `border-border/50`    | Border color at 50% opacity        |

### Borders and Rounding

| Tailwind           | CSS                          |
|--------------------|------------------------------|
| `border`           | `border-width: 1px`         |
| `border-t`         | `border-top-width: 1px`     |
| `border-transparent`| `border-color: transparent` |
| `rounded-xl`       | `border-radius: 0.75rem`    |
| `rounded-lg`       | `border-radius: 0.5rem`     |
| `rounded-full`     | `border-radius: 9999px`     |
| `rounded-none`     | `border-radius: 0`          |

### Sizing

| Tailwind  | CSS                              |
|-----------|----------------------------------|
| `h-4 w-4` | `height: 1rem; width: 1rem`     |
| `h-8 w-8` | `height: 2rem; width: 2rem`     |
| `h-9 w-9` | `height: 2.25rem; width: 2.25rem` |
| `h-1.5 w-1.5` | `height: 0.375rem; width: 0.375rem` |
| `size-4`  | `width: 1rem; height: 1rem`     |

### Effects and Transitions

| Tailwind            | CSS                                    |
|---------------------|----------------------------------------|
| `shadow-sm`         | Small box shadow                      |
| `shadow-md`         | Medium box shadow                     |
| `shadow-lg`         | Large box shadow                      |
| `transition-all`    | `transition-property: all`            |
| `duration-200`      | `transition-duration: 200ms`          |
| `duration-300`      | `transition-duration: 300ms`          |
| `animate-spin`      | Continuous rotation                   |
| `animate-slide-in`  | Slide up + fade in (custom, 0.3s)     |
| `antialiased`       | Font smoothing                        |

### State Variants

| Prefix             | When it applies                          |
|--------------------|------------------------------------------|
| `hover:`           | Mouse is over the element               |
| `focus-visible:`   | Element has keyboard focus              |
| `disabled:`        | Element has `disabled` attribute        |
| `active:`          | Element is being clicked/pressed        |
| `dark:`            | `.dark` class is on `<html>`            |
| `md:`              | Viewport is >= 768px                    |
| `lg:`              | Viewport is >= 1024px                   |

### Custom Classes (defined in globals.css)

| Class               | Purpose                                         |
|---------------------|--------------------------------------------------|
| `glass`             | Standard frosted-glass panel                    |
| `glass-strong`      | Heavier blur + inset highlight (sidebar)        |
| `glass-subtle`      | Lighter blur (nested elements, outline buttons) |
| `bg-mesh`           | Radial gradient background mesh                 |
| `bg-accent-gradient`| Blue-to-purple linear gradient                  |
| `text-gradient`     | Gradient applied to text glyphs                 |
| `glow-hover`        | Blue glow on hover                              |
| `custom-scrollbar`  | Thin 6px styled scrollbar                       |

---

**Next up:** [06 -- Component Libraries and shadcn/ui](./06-component-libraries-and-shadcn.md) -- how the project's UI components are built from Radix primitives, styled with Tailwind, and composed into the interface.
