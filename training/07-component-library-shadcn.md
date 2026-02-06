# 07 -- Component Libraries: shadcn/ui, Radix UI, and CVA

This is document 7 of 10. You already know JavaScript, TypeScript, React, Next.js, Tailwind CSS, and React Query from the previous six docs. This document covers the component library layer that sits on top of all of those: **shadcn/ui**, the accessibility primitives it is built on (**Radix UI**), the variant system it uses (**CVA**), and the supporting utilities that tie them together.

By the end you will understand every line of the `Button`, `Card`, `Dialog`, `Select`, `Badge`, and `Toaster` components in this project, and you will be able to modify them or create new ones.

---

## Table of Contents

1. [What is shadcn/ui?](#1-what-is-shadcnui)
2. [The Button Component -- A Deep Dive](#2-the-button-component----a-deep-dive)
3. [The Card Component and Compound Components](#3-the-card-component-and-compound-components)
4. [The Dialog Component and Radix UI Primitives](#4-the-dialog-component-and-radix-ui-primitives)
5. [The Select Component](#5-the-select-component)
6. [The Badge Component -- CVA Without forwardRef](#6-the-badge-component----cva-without-forwardref)
7. [The Toaster (Sonner)](#7-the-toaster-sonner)
8. [Lucide Icons](#8-lucide-icons)
9. [The cn() Utility](#9-the-cn-utility)
10. [Key Patterns Summary](#10-key-patterns-summary)

---

## 1. What is shadcn/ui?

### The Mental Model

shadcn/ui is **not** a traditional component library that you install from npm. There is no `npm install shadcn-ui` that gives you a `<Button>` import. Instead, shadcn/ui is a **collection of copy-pasteable component source files** that you add directly into your project. You run a CLI command like `npx shadcn-ui@latest add button`, and it drops a `button.tsx` file into your `components/ui/` directory. From that point on, **you own that file**. It is your code. You can change anything about it.

### How It Differs from Traditional Libraries

| Traditional Library (e.g., Material UI) | shadcn/ui |
|----------------------------------------|-----------|
| Installed as an npm dependency | Source files copied into your project |
| Updates come from `npm update` | You manually update or modify files |
| Styling is constrained by the library's API | You edit the Tailwind classes directly |
| Bug in the library? Wait for a release | Bug in the component? Fix it yourself, right now |
| Components live in `node_modules/` | Components live in `components/ui/` |

### C# and Python Analogies

If you have used WPF in C#, think of shadcn/ui components like WPF control templates that you have extracted and placed in your own ResourceDictionary. You can change the template without touching the framework. In Python terms, imagine copying a PyQt widget's source code into your project instead of importing it -- you get full control but also full responsibility.

### What This Project Uses

This project has 16 shadcn/ui component files in `frontend/components/ui/`:

```
button.tsx        card.tsx          badge.tsx
dialog.tsx        select.tsx        tabs.tsx
table.tsx         input.tsx         textarea.tsx
checkbox.tsx      radio-group.tsx   label.tsx
tooltip.tsx       dropdown-menu.tsx sheet.tsx
sonner.tsx
```

Each one is a thin wrapper that combines:
- **Radix UI** -- unstyled, accessible behavior primitives (keyboard navigation, focus management, ARIA attributes)
- **Tailwind CSS** -- utility classes for visual styling
- **CVA** -- variant management (different sizes, colors, states)

### The Three Layers

```
 Your Application Code
        |
        v
 shadcn/ui components  (components/ui/*.tsx -- YOUR files, editable)
        |
        v
 Radix UI primitives   (node_modules/@radix-ui/* -- handles accessibility,
                         keyboard nav, focus trapping, ARIA roles)
        |
        v
 HTML DOM elements      (<button>, <div>, <select>, etc.)
```

You write `<Button variant="outline">`. shadcn/ui translates that into Tailwind classes. Radix UI (where applicable) ensures the underlying HTML element has correct ARIA attributes and keyboard behavior. The browser renders it.

---

## 2. The Button Component -- A Deep Dive

This is the most instructive component to study because it demonstrates every major pattern at once: CVA variants, TypeScript interface composition, `forwardRef`, the `Slot` pattern, and the `cn()` utility.

Here is the complete, unedited `frontend/components/ui/button.tsx` from this project:

```tsx
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-accent-gradient text-white shadow-md hover:shadow-lg hover:brightness-110 active:brightness-95",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:
          "border border-border glass-subtle hover:bg-accent/10 hover:border-accent/30 hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "hover:bg-accent/10 hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-lg px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

We will break this down section by section.

---

### 2.1 CVA (Class Variance Authority)

CVA is a small library that solves one problem: **how do you manage multiple visual variants of a component without writing a mess of if/else chains to pick CSS classes?**

#### The Problem CVA Solves

Without CVA, you would write something like this:

```tsx
// Without CVA -- messy conditional logic
function Button({ variant, size, className }) {
  let classes = "inline-flex items-center justify-center rounded-lg text-sm font-medium";

  if (variant === "default") {
    classes += " bg-accent-gradient text-white shadow-md";
  } else if (variant === "destructive") {
    classes += " bg-destructive text-destructive-foreground";
  } else if (variant === "outline") {
    classes += " border border-border glass-subtle";
  }
  // ... more variants ...

  if (size === "default") {
    classes += " h-9 px-4 py-2";
  } else if (size === "sm") {
    classes += " h-8 rounded-md px-3 text-xs";
  }
  // ... more sizes ...

  return <button className={`${classes} ${className}`} />;
}
```

That gets unwieldy fast. CVA replaces it with a declarative configuration object.

#### How cva() Works

```tsx
const buttonVariants = cva(
  // 1. BASE CLASSES -- applied to every button regardless of variant or size
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg ...",

  // 2. CONFIGURATION OBJECT
  {
    variants: {
      // Each key here becomes a prop on the component
      variant: {
        default: "bg-accent-gradient text-white shadow-md ...",
        destructive: "bg-destructive text-destructive-foreground ...",
        outline: "border border-border glass-subtle ...",
        // ... more named variants
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-lg px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)
```

`cva()` returns a **function**. When you call that function, it combines the base classes with the classes for the selected variant and size:

```tsx
buttonVariants({ variant: "outline", size: "sm" })
// Returns: "inline-flex items-center ... border border-border glass-subtle ... h-8 rounded-md px-3 text-xs"

buttonVariants({})
// Uses defaults: returns base + "bg-accent-gradient text-white ..." + "h-9 px-4 py-2"
```

#### Breaking Down the Base Classes

```
inline-flex items-center justify-center    -- flexbox layout, centered content
gap-2                                      -- 8px gap between children (icon + text)
whitespace-nowrap                          -- text never wraps to next line
rounded-lg                                 -- rounded corners
text-sm font-medium                        -- 14px font, medium weight
transition-all duration-200                -- smooth animation on hover/focus (200ms)
focus-visible:outline-none                 -- remove default browser outline
focus-visible:ring-2                       -- show a ring when focused via keyboard
focus-visible:ring-ring                    -- ring color from theme token
focus-visible:ring-offset-2                -- gap between ring and button edge
focus-visible:ring-offset-background       -- gap color matches page background
disabled:pointer-events-none               -- disabled buttons ignore clicks
disabled:opacity-50                        -- disabled buttons look faded
[&_svg]:pointer-events-none                -- SVG icons inside don't capture clicks
[&_svg]:size-4                             -- SVG icons are 16x16px
[&_svg]:shrink-0                           -- SVG icons don't shrink in flex
```

The `[&_svg]` syntax is a Tailwind arbitrary variant. `&` means "this element" and `_svg` means "descendant svg elements." So `[&_svg]:size-4` translates roughly to `.button svg { width: 1rem; height: 1rem; }`.

#### Breaking Down the Variant Classes

```tsx
variant: {
  default:
    "bg-accent-gradient text-white shadow-md hover:shadow-lg hover:brightness-110 active:brightness-95",
    // The primary action button. Uses the project's blue-to-purple gradient.
    // Gets brighter on hover, slightly darker on click (active).

  destructive:
    "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
    // Red button for delete actions. Fades to 90% opacity on hover.

  outline:
    "border border-border glass-subtle hover:bg-accent/10 hover:border-accent/30 hover:text-accent-foreground",
    // Transparent with a border. Uses the project's glass effect. Gains a subtle
    // tint on hover. The most common secondary action button.

  secondary:
    "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
    // A muted solid button.

  ghost:
    "hover:bg-accent/10 hover:text-accent-foreground",
    // Completely invisible until hovered. No background, no border.
    // Used for toolbar actions and icon buttons that should not be visually heavy.

  link:
    "text-primary underline-offset-4 hover:underline",
    // Looks like a text link, not a button.
},
```

#### C# Analogy

In WPF, you would define button styles with `<Style>` elements and `<Trigger>` blocks:

```xml
<Style x:Key="DestructiveButton" TargetType="Button">
    <Setter Property="Background" Value="Red"/>
    <Style.Triggers>
        <Trigger Property="IsMouseOver" Value="True">
            <Setter Property="Opacity" Value="0.9"/>
        </Trigger>
    </Style.Triggers>
</Style>
```

CVA is the same idea -- pre-defined named style sets -- but expressed as a JavaScript object instead of XAML. The key advantage is that the configuration is collocated with the component, type-safe (TypeScript extracts the valid variant names), and uses the same Tailwind classes you already know.

---

### 2.2 The Interface -- TypeScript Type Composition

```tsx
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}
```

This interface uses **multiple inheritance** (TypeScript interfaces can extend multiple other interfaces). Let us break down each part.

#### `React.ButtonHTMLAttributes<HTMLButtonElement>`

This is a built-in React type that includes every standard HTML attribute a `<button>` element accepts: `onClick`, `disabled`, `type`, `aria-label`, `className`, `id`, `tabIndex`, and dozens more. By extending this, the `Button` component automatically accepts all of those props without you having to declare them.

In C# terms, this is like inheriting from `System.Windows.Controls.Button` -- you get all the base properties for free.

#### `VariantProps<typeof buttonVariants>`

This is a utility type from CVA. It reads the `buttonVariants` configuration and extracts the prop types:

```tsx
// VariantProps<typeof buttonVariants> produces:
{
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | null | undefined;
  size?: "default" | "sm" | "lg" | "icon" | null | undefined;
}
```

The `typeof` keyword here is TypeScript's type-level `typeof` -- it extracts the type of a value at compile time. `typeof buttonVariants` gives you the type of the CVA function, and `VariantProps<>` pulls out the variant options from that type.

This means if you later add a new variant to the `cva()` call (say, `warning: "bg-warning ..."`), the TypeScript type automatically includes `"warning"` as a valid option. No manual synchronization needed.

#### `asChild?: boolean`

A custom prop specific to this component. The `?` means optional. We will cover what `asChild` does in the Slot Pattern section below.

#### How They Combine

The final `ButtonProps` type is the union of all three. A `Button` component accepts:
- Every standard HTML button attribute (`onClick`, `disabled`, `type`, etc.)
- `variant` and `size` from CVA
- `asChild` for the Slot pattern
- `className` for additional Tailwind overrides (comes from `HTMLAttributes`)

---

### 2.3 forwardRef -- Passing DOM References Through Components

```tsx
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    // ... component body
  }
)
Button.displayName = "Button"
```

#### What Problem Does forwardRef Solve?

In React, a `ref` is a way to get a direct reference to a DOM element. You might need this to:
- Focus an input programmatically: `inputRef.current.focus()`
- Measure an element's dimensions: `elementRef.current.getBoundingClientRect()`
- Integrate with third-party libraries that need DOM access

Without `forwardRef`, if a parent component passes a `ref` to your custom component, the ref does not automatically reach the underlying `<button>` element. `forwardRef` bridges that gap.

#### C# Analogy

In WPF, if you create a custom `UserControl` that wraps a `TextBox`, and the parent window wants a reference to that inner `TextBox` (to call `.Focus()` on it), you would expose it as a public property. `forwardRef` is the React equivalent of that pattern.

#### The Syntax

```tsx
React.forwardRef<HTMLButtonElement, ButtonProps>(
  (props, ref) => { ... }
)
```

- First generic parameter `HTMLButtonElement`: the type of DOM element the ref will point to
- Second generic parameter `ButtonProps`: the type of props the component accepts
- The function receives two arguments: `props` (destructured) and `ref`

#### Destructuring with Rest/Spread

```tsx
({ className, variant, size, asChild = false, ...props }, ref) => { ... }
```

This pulls out `className`, `variant`, `size`, and `asChild` by name, and gathers **every other prop** into a single object called `props`. Those remaining props (like `onClick`, `disabled`, `children`, `aria-label`, etc.) are then spread onto the underlying element with `{...props}`.

In C# terms, this is like using a `params` keyword to capture remaining arguments, except it works with named properties. In Python, it is like `**kwargs`:

```python
def button(className=None, variant=None, size=None, asChild=False, **props):
    # props contains everything else: onClick, disabled, etc.
```

#### displayName

```tsx
Button.displayName = "Button"
```

React DevTools uses `displayName` to show component names in the component tree. `forwardRef` wraps the component in a way that can lose the name, so setting `displayName` restores it. Without this, you would see "ForwardRef" in your DevTools instead of "Button."

---

### 2.4 The Slot Pattern (asChild)

```tsx
const Comp = asChild ? Slot : "button"
return (
  <Comp
    className={cn(buttonVariants({ variant, size, className }))}
    ref={ref}
    {...props}
  />
)
```

#### What is Slot?

`Slot` is a component from `@radix-ui/react-slot`. When rendered, it does not create a new DOM element. Instead, it takes its props (className, onClick, ref, etc.) and **merges them onto its single child element**.

#### Why Would You Want This?

The most common use case: wrapping a Next.js `<Link>` inside a `<Button>`. Without `asChild`, you would get this DOM structure:

```html
<!-- Without asChild: nested <button> and <a> -- INVALID HTML -->
<button class="bg-accent-gradient ...">
  <a href="/leads">View Leads</a>
</button>
```

A `<button>` containing an `<a>` is invalid HTML. With `asChild`, the `<Link>` (which renders an `<a>`) receives the button's className and other props directly:

```html
<!-- With asChild: the <a> gets the button styling -->
<a href="/leads" class="bg-accent-gradient ...">View Leads</a>
```

#### Real Usage in This Project

From `frontend/components/lead-filters.tsx`:

```tsx
<Button variant="outline" asChild>
  <a href={getExportUrl(filters)} download>
    <Download className="mr-2 h-4 w-4" />
    Export
  </a>
</Button>
```

Here, `asChild` tells Button: "Do not render a `<button>` element. Instead, take the `<a>` element that is my child and give it all my props (the outline variant classes, the ref, etc.)." The result in the DOM is a single `<a>` tag with button styling, which is semantically correct because this is a download link, not a button action.

#### The Variable Component Pattern

```tsx
const Comp = asChild ? Slot : "button"
```

In React, JSX tags can be variables. If `Comp` holds the string `"button"`, React renders a `<button>`. If `Comp` holds the `Slot` component, React renders that instead. This is a common pattern in component libraries.

---

### 2.5 Putting It All Together -- How a Button Renders

When you write:

```tsx
<Button variant="outline" size="sm" onClick={handleClick} disabled={isLoading}>
  Save Lead
</Button>
```

Here is what happens step by step:

1. React calls the `Button` component with props: `{ variant: "outline", size: "sm", onClick: handleClick, disabled: true, children: "Save Lead" }`
2. Destructuring extracts `variant="outline"`, `size="sm"`, `className=undefined`, `asChild=false`
3. `...props` captures `{ onClick: handleClick, disabled: true, children: "Save Lead" }`
4. `asChild` is false, so `Comp` is `"button"`
5. `buttonVariants({ variant: "outline", size: "sm", className: undefined })` generates: `"inline-flex items-center justify-center ... border border-border glass-subtle hover:bg-accent/10 ... h-8 rounded-md px-3 text-xs"`
6. `cn()` passes that through `twMerge()` to resolve any conflicting classes
7. React renders: `<button className="..." onClick={handleClick} disabled={true}>Save Lead</button>`

---

### 2.6 Real Button Usage in This Project

**Dashboard "Run Pipeline" button** (from `frontend/app/page.tsx`):

```tsx
<Button
  onClick={handleRunPipeline}
  disabled={pipelineStatus?.running}
  size="lg"
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
```

This uses the `default` variant (omitted, so defaultVariants kicks in) and `lg` size. The content switches between a spinning loader and a play icon based on the pipeline state. The `disabled` prop is a standard HTML button attribute that passes through via `...props`.

**Outline "Review Now" button** (from `frontend/app/page.tsx`):

```tsx
<Button variant="outline" size="sm">
  Review Now
  <ArrowRight className="ml-2 h-3.5 w-3.5" />
</Button>
```

**Destructive "Delete" button** (from `frontend/components/lead-table.tsx`):

```tsx
<Button
  variant="destructive"
  onClick={() => bulkDeleteMutation.mutate()}
  disabled={bulkDeleteMutation.isPending}
>
  {bulkDeleteMutation.isPending ? "Deleting..." : "Delete"}
</Button>
```

**Ghost icon button** (from `frontend/components/lead-detail-panel.tsx`):

```tsx
<Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
  <Pencil className="h-3.5 w-3.5" />
</Button>
```

**asChild with anchor** (from `frontend/components/lead-filters.tsx`):

```tsx
<Button variant="outline" asChild>
  <a href={getExportUrl(filters)} download>
    <Download className="mr-2 h-4 w-4" />
    Export
  </a>
</Button>
```

---

## 3. The Card Component and Compound Components

### The Complete card.tsx

Here is the full `frontend/components/ui/card.tsx`:

```tsx
import * as React from "react"

import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-xl glass glow-hover transition-all duration-300",
      className
    )}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("font-semibold leading-none tracking-tight", className)}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
```

### Why No CVA?

The Card component does not use CVA because it does not need variant props. There is only one visual style for a card (the glass effect). All variation happens through the `className` override -- the caller can add extra classes. Not every component needs CVA. Use it when you have named variants; skip it when you do not.

### The Compound Component Pattern

Notice that `Card` is not one component. It is **six related components** that are designed to be used together:

```tsx
<Card>                              {/* Outer glass container */}
  <CardHeader>                      {/* Top section with padding */}
    <CardTitle>Title</CardTitle>    {/* Bold heading */}
    <CardDescription>              {/* Muted subtext */}
      Some description
    </CardDescription>
  </CardHeader>
  <CardContent>                     {/* Main body (no top padding) */}
    <p>Content goes here</p>
  </CardContent>
  <CardFooter>                      {/* Bottom section with flex row */}
    <Button>Action</Button>
  </CardFooter>
</Card>
```

This is the **Compound Component** pattern. Each sub-component handles its own spacing and layout so the overall card structure stays consistent. You cannot accidentally forget padding because `CardHeader` adds `p-6`, `CardContent` adds `p-6 pt-0` (all sides except top, because the header already handles the top), and `CardFooter` adds `p-6 pt-0` similarly.

#### C# WPF Analogy

This is like WPF's `Grid` with `Grid.Row` and `Grid.Column`, or `Expander` with `Expander.Header` and `Expander.Content`. The parent defines the container, and nested elements fill specific roles within that container.

#### Python Analogy

In PyQt, this would be like a `QGroupBox` with a `QVBoxLayout` where you add a `QLabel` (title), another `QLabel` (description), a `QWidget` (content), and a `QHBoxLayout` (footer). The compound component pattern pre-defines these slots so every card in the app is structurally consistent.

### Understanding the Card's Default Classes

```tsx
className={cn("rounded-xl glass glow-hover transition-all duration-300", className)}
```

- `rounded-xl` -- larger rounded corners (12px)
- `glass` -- a custom utility class defined in this project's `globals.css`. It applies `backdrop-blur`, a semi-transparent background, and a subtle border to create the glassmorphism effect
- `glow-hover` -- another custom class that adds a soft glow on hover
- `transition-all duration-300` -- smooth 300ms animation for the hover glow

The `className` parameter at the end allows callers to add or override classes:

```tsx
<Card className="border-warning/20">
  {/* The warning border color is merged with the default glass classes */}
</Card>
```

### Real Card Usage in This Project

**Dashboard stats with last pipeline run** (from `frontend/app/page.tsx`):

```tsx
{stats.last_run && (
  <Card>
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-base">
        <div className="h-8 w-8 rounded-lg bg-primary/15 flex items-center justify-center">
          <Clock className="h-4 w-4 text-primary" />
        </div>
        Last Pipeline Run
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-3xl font-bold tracking-tight">
        {stats.last_run.leads_added} leads
      </p>
      <p className="text-sm text-muted-foreground mb-4">
        added {formatLocalDateTime(stats.last_run.run_started_at)}
      </p>
    </CardContent>
  </Card>
)}
```

Notice that `CardHeader` has `className="pb-3"`. This **overrides** the default bottom padding (which would be part of the `p-6` padding) with a smaller value. That is the `cn()` utility at work -- it knows that `pb-3` should override the bottom portion of `p-6`.

**Chart card** (from `frontend/components/charts.tsx`):

```tsx
<Card>
  <CardHeader>
    <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
      Leads by Type
    </CardTitle>
  </CardHeader>
  <CardContent>
    {/* Recharts pie chart goes here */}
  </CardContent>
</Card>
```

---

## 4. The Dialog Component and Radix UI Primitives

The Dialog component is where you first see **Radix UI** doing heavy lifting. Unlike Button (which only uses Radix's `Slot`) or Card (which does not use Radix at all), Dialog uses a full Radix primitive with focus trapping, overlay management, animations, and keyboard navigation.

### How Radix UI Works

Radix UI provides **unstyled, accessible behavior primitives**. For example, `@radix-ui/react-dialog` gives you:

- A trigger that opens the dialog when clicked
- A portal that renders the dialog outside the normal DOM hierarchy (so it sits on top of everything)
- An overlay that covers the page behind the dialog
- Focus trapping -- tabbing stays within the dialog while it is open
- Escape key to close
- Correct ARIA roles (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, etc.)
- Open/close animations with `data-[state=open]` and `data-[state=closed]` attributes

All of that behavior comes for free. The shadcn/ui dialog component adds the visual styling on top.

### The Architecture

```tsx
import * as DialogPrimitive from "@radix-ui/react-dialog"

// These are just renamed re-exports of the Radix primitives -- no styling added
const Dialog = DialogPrimitive.Root          // The state container (open/closed)
const DialogTrigger = DialogPrimitive.Trigger // Button that opens the dialog
const DialogPortal = DialogPrimitive.Portal   // Renders children in a portal
const DialogClose = DialogPrimitive.Close     // Button that closes the dialog
```

The interesting parts are the components that add styling:

```tsx
const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
))
```

Breaking that down:
- `fixed inset-0` -- covers the entire viewport
- `z-50` -- high z-index so it sits above everything
- `bg-black/80` -- black at 80% opacity (the dark overlay behind the dialog)
- `data-[state=open]:animate-in` -- Radix sets `data-state="open"` when the dialog opens; Tailwind's `animate-in` class triggers a CSS animation
- `data-[state=closed]:fade-out-0` -- when closing, fade to 0 opacity

The `data-[state=...]` syntax is a Tailwind **data attribute variant**. Radix UI sets `data-state="open"` or `data-state="closed"` on the element, and Tailwind applies the corresponding classes. This is how you get open/close animations without managing state yourself.

### New TypeScript Pattern: ElementRef and ComponentPropsWithoutRef

```tsx
React.ElementRef<typeof DialogPrimitive.Overlay>
```

This extracts the DOM element type that a Radix component renders to. For `DialogPrimitive.Overlay`, that is `HTMLDivElement`. It is like asking "what DOM element does this component ultimately create?"

```tsx
React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
```

This extracts all the props that the Radix component accepts, minus the `ref` prop (because `forwardRef` handles that separately). This is the standard pattern for wrapping Radix primitives: you get all of Radix's props, add your styling, and pass everything through.

### DialogContent -- The Main Panel

```tsx
const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ...">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
))
```

Key details:
- `left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%]` -- the standard CSS centering trick (place at 50% of viewport, then pull back by 50% of own size)
- `max-w-lg` -- maximum width of 512px
- The close button (`X` icon) is positioned absolutely in the top-right corner
- `<span className="sr-only">Close</span>` -- screen-reader-only text for accessibility. The `sr-only` class hides it visually but keeps it in the accessibility tree

### DialogHeader, DialogFooter, DialogTitle, DialogDescription

These follow the same compound component pattern as Card:

```tsx
// DialogHeader: centered text on mobile, left-aligned on desktop
"flex flex-col space-y-1.5 text-center sm:text-left"

// DialogFooter: stacked buttons on mobile, row on desktop
"flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2"

// DialogTitle: large semibold heading
"text-lg font-semibold leading-none tracking-tight"

// DialogDescription: muted smaller text
"text-sm text-muted-foreground"
```

### Real Dialog Usage in This Project

**Delete confirmation dialog** (from `frontend/components/lead-table.tsx`):

```tsx
<Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
  <DialogContent className="glass-strong">
    <DialogHeader>
      <DialogTitle>Delete Leads</DialogTitle>
      <DialogDescription>
        Are you sure you want to delete {selectedIds.size} lead
        {selectedIds.size === 1 ? "" : "s"}?
        This action can be undone by an administrator.
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
        Cancel
      </Button>
      <Button
        variant="destructive"
        onClick={() => bulkDeleteMutation.mutate()}
        disabled={bulkDeleteMutation.isPending}
      >
        {bulkDeleteMutation.isPending ? "Deleting..." : "Delete"}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

Notice:
- `open` and `onOpenChange` are Radix's **controlled** state props (like a C# dependency property with two-way binding)
- `className="glass-strong"` adds a stronger glassmorphism effect to the dialog panel
- The footer has two buttons: an outline cancel and a destructive confirm
- The destructive button shows "Deleting..." while the mutation is in progress

---

## 5. The Select Component

The Select component is another Radix UI primitive wrapper, more complex than Dialog because it has more sub-components.

### The Architecture

```tsx
import * as SelectPrimitive from "@radix-ui/react-select"

// Simple re-exports (no added styling)
const Select = SelectPrimitive.Root        // State container
const SelectGroup = SelectPrimitive.Group  // Groups of related options
const SelectValue = SelectPrimitive.Value  // Displays the selected value

// Styled wrappers
const SelectTrigger    // The clickable dropdown button
const SelectContent    // The dropdown panel that appears
const SelectItem       // Each option in the dropdown
const SelectLabel      // Section headers within the dropdown
const SelectSeparator  // Horizontal line between sections
```

Radix handles all the hard parts: keyboard navigation (arrow keys to move between options, Enter to select, Escape to close), proper ARIA roles (`role="listbox"`, `role="option"`), and positioning the dropdown relative to the trigger.

### SelectTrigger

```tsx
const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background data-[placeholder]:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
```

Notice `data-[placeholder]:text-muted-foreground` -- when no value is selected, Radix sets a `data-placeholder` attribute, and the text appears in a muted color. When a value is selected, the attribute is removed and the text appears in the normal color.

Also notice `asChild` being used on `SelectPrimitive.Icon` -- the Radix icon wrapper uses Slot internally, so the `ChevronDown` icon receives the icon wrapper's props directly.

### SelectItem -- The Checkbox Pattern

```tsx
const SelectItem = React.forwardRef<...>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
```

The `ItemIndicator` is a Radix component that only renders its children when the item is selected. So the `Check` icon appears next to the currently selected option and is invisible for all others. No conditional logic needed -- Radix handles it.

### Real Select Usage in This Project

**Stage filter dropdown** (from `frontend/components/lead-filters.tsx`):

```tsx
<Select
  value={filters.stage || "all"}
  onValueChange={(value) =>
    onFilterChange({ ...filters, stage: value === "all" ? undefined : value })
  }
>
  <SelectTrigger className="w-[150px] glass-subtle">
    <SelectValue placeholder="All Stages" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All Stages</SelectItem>
    {STAGES.map((stage) => (
      <SelectItem key={stage} value={stage}>
        {stage}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

This is a **controlled** select: the parent manages the `value` and receives changes through `onValueChange`. When the user selects "all", the filter is set to `undefined` (showing all stages). When they pick a specific stage like "New" or "Qualified", that value is passed to the filter.

---

## 6. The Badge Component -- CVA Without forwardRef

The Badge shows a simpler variant of the CVA pattern without `forwardRef`:

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-accent-gradient text-white shadow-sm",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-sm",
        outline: "text-foreground border-border/50",
        success:
          "border-transparent bg-success/15 text-success",
        warning:
          "border-transparent bg-warning/15 text-warning",
        info:
          "border-transparent bg-info/15 text-info",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
```

### What is Different from Button?

1. **No `forwardRef`** -- Badge is a simple function component. It does not need ref forwarding because nobody typically needs a DOM reference to a badge. This is a design choice: use `forwardRef` when the component is interactive and might need DOM access, skip it for purely presentational components.

2. **No `asChild` / Slot** -- A badge is always a `<div>`. There is no use case for rendering it as a different element.

3. **Only one variant axis** -- There is no `size` dimension, just `variant`. CVA handles any number of variant axes, including just one.

4. **Semantic variants** -- Notice `success`, `warning`, and `info` alongside the standard `default`/`secondary`/`destructive`/`outline`. These use semi-transparent backgrounds (`bg-success/15`) to create colored tags. The `/15` means 15% opacity -- a very subtle tint.

### The Pattern for Simple CVA Components

If you need to create a new styled component with variants, Badge is your simplest template:

```tsx
// 1. Define variants with cva()
const myVariants = cva("base classes", { variants: { ... }, defaultVariants: { ... } })

// 2. Define props interface
export interface MyProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof myVariants> {}

// 3. Create the component
function MyComponent({ className, variant, ...props }: MyProps) {
  return <div className={cn(myVariants({ variant }), className)} {...props} />
}

// 4. Export both the component and the variants function
export { MyComponent, myVariants }
```

---

## 7. The Toaster (Sonner)

Sonner is a third-party toast notification library. Unlike the other components in this section, it is a full npm package (not copied source code). However, the shadcn/ui wrapper component in `components/ui/sonner.tsx` bridges it into the project's design system.

### The Wrapper Component

Here is the complete `frontend/components/ui/sonner.tsx`:

```tsx
"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
```

### Breaking It Down

#### "use client"

This is a Next.js directive. `useTheme()` is a client-side hook (it reads the browser's DOM), so this component must be marked as a client component.

#### Theme Integration

```tsx
const { theme = "system" } = useTheme()
```

This reads the current theme from `next-themes` (which this project uses for dark/light mode). The `= "system"` is a default value in case `useTheme()` returns undefined. The theme is passed to Sonner so toast notifications match the current color scheme.

#### The group-[.toaster] Pattern

```tsx
"group-[.toaster]:bg-background"
```

This is a Tailwind **group variant** with a modifier. Here is how it works:

1. The outer `Sonner` component has `className="toaster group"`
2. `group` marks it as a Tailwind group container
3. `group-[.toaster]:bg-background` on the toast means: "Apply `bg-background` when my ancestor group element also has the `.toaster` class"

This specificity trick ensures the toast styles only apply within the project's Toaster wrapper, not in other contexts. It is a way to scope styles without CSS modules.

#### ComponentProps

```tsx
type ToasterProps = React.ComponentProps<typeof Sonner>
```

`React.ComponentProps<typeof Sonner>` extracts the props type from the Sonner component. This is the "I do not know what props this library component accepts, but I want my wrapper to accept the same ones" pattern. It is like reflection in C# -- inspecting a type at compile time to derive another type.

### Global Placement

The Toaster is rendered once, globally, in `frontend/components/providers.tsx`:

```tsx
export function Providers({ children }: { children: ReactNode }) {
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

`position="top-right"` puts notifications in the upper-right corner. `richColors` enables color-coded toasts (green for success, red for error).

### Triggering Toasts From Anywhere

Once the `<Toaster>` is rendered globally, any component in the app can trigger a notification by importing and calling the `toast` function from `sonner`:

```tsx
import { toast } from "sonner";

// In a mutation's onSuccess callback:
toast.success("Pipeline started");

// In a mutation's onError callback:
toast.error("Failed to start pipeline");

// Other variants:
toast.info("Processing...");
toast.warning("API rate limit approaching");
```

This is a **module-level singleton** pattern. The `toast` function is not a React hook -- it is a plain function that communicates with the `<Toaster>` component through a shared internal event bus. You do not need to pass props, use context, or manage state. Just call `toast.success("message")` and the notification appears.

#### C# Analogy

This is similar to the `MessageBox.Show()` pattern in WinForms or WPF, except the notifications are non-blocking and auto-dismiss.

### Real Toast Usage

**Pipeline page** (from `frontend/app/pipeline/page.tsx`):

```tsx
const runPipeline = useMutation({
  mutationFn: triggerPipeline,
  onSuccess: () => {
    toast.success("Pipeline started");
    queryClient.invalidateQueries({ queryKey: ["pipeline-status"] });
  },
  onError: (error: Error) => {
    toast.error(error.message || "Failed to start pipeline");
  },
});
```

**Bulk operations** (from `frontend/components/lead-table.tsx`):

```tsx
onSuccess: (data) => {
  toast.success(`Updated ${data.updated.length} leads`);
  queryClient.invalidateQueries({ queryKey: ["leads"] });
},
onError: (error: Error) => {
  toast.error(error.message || "Failed to update leads");
},
```

**Filter presets** (from `frontend/components/filter-presets.tsx`):

```tsx
toast.success(`Saved preset "${newPreset.name}"`);
toast.success(`Deleted preset "${preset?.name}"`);
toast.success(`Applied preset "${preset.name}"`);
toast.error("Please enter a preset name");
```

---

## 8. Lucide Icons

Lucide is an icon library with hundreds of icons, each available as an individual React component. The project imports only the icons it needs:

```tsx
import { Loader2, Play, Copy, ArrowRight, Clock, Zap, TrendingUp } from "lucide-react";
import { Users, Target, Sparkles, CheckCircle2 } from "lucide-react";
import { Download, Search, X } from "lucide-react";
import { Pencil, ExternalLink } from "lucide-react";
import { Save, Trash2 } from "lucide-react";
import { Check, ChevronDown, ChevronUp } from "lucide-react";
```

### Using Icons as Components

Each import is a React component. You use it like any other JSX element:

```tsx
<Loader2 className="h-4 w-4 animate-spin" />
<Play className="mr-2 h-4 w-4" />
<X className="h-4 w-4" />
```

### Sizing

Icons are sized with Tailwind height/width classes, not with a `size` prop:

| Class | Size |
|-------|------|
| `h-3 w-3` | 12px |
| `h-3.5 w-3.5` | 14px |
| `h-4 w-4` | 16px (most common) |
| `h-5 w-5` | 20px |
| `h-8 w-8` | 32px |

### Coloring

Icons inherit the text color of their parent by default, or you can set it explicitly:

```tsx
<Clock className="h-4 w-4 text-primary" />      {/* Blue */}
<Copy className="h-4 w-4 text-warning" />        {/* Yellow/amber */}
<Zap className="h-4 w-4 text-white" />           {/* White */}
<Sparkles className="h-4.5 w-4.5 text-emerald-400" />  {/* Green */}
```

### Animation

```tsx
<Loader2 className="h-4 w-4 animate-spin" />
```

The `animate-spin` class applies a continuous rotation. `Loader2` is a circular arrow icon that looks like a loading spinner when rotated.

### Dynamic Icon Selection

You can store icon components in variables and render them dynamically. This project does this in the stats cards:

```tsx
// In the configuration array:
const statConfig = [
  {
    key: "total_leads" as const,
    label: "Total Leads",
    icon: Users,               // <-- The component itself, not JSX
    iconColor: "text-blue-400",
    // ...
  },
  {
    key: "avg_score" as const,
    label: "Avg Score",
    icon: Target,
    iconColor: "text-purple-400",
    // ...
  },
  // ...
];

// In the render:
{statConfig.map((stat) => {
  const Icon = stat.icon;    // Assign the component to a variable
  return (
    <div key={stat.key} className="...">
      <Icon className={`h-4.5 w-4.5 ${stat.iconColor}`} />
      {/* ^^ Render it like any component */}
    </div>
  );
})}
```

The key insight: React components are just values (functions or classes). You can store them in arrays, pass them as props, or assign them to variables. The only rule is that the variable name must start with an uppercase letter when used as a JSX tag (otherwise React treats it as an HTML element).

#### C# Analogy

In WPF, you might store `Type` objects and instantiate them with `Activator.CreateInstance()`. In React, you just store the component function and render it with `<Component />`. It is much simpler because components are just functions.

### Why Icons Live in Button Base Classes

Remember this from the Button's CVA base classes?

```
[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0
```

This means every SVG inside a button is automatically sized to 16px and cannot receive clicks. This is why you can drop a Lucide icon inside a button and it just works:

```tsx
<Button>
  <Play className="mr-2 h-4 w-4" />
  Run Pipeline
</Button>
```

The `mr-2` adds a right margin to separate the icon from the text. The `h-4 w-4` is technically redundant here (the button base already sets `[&_svg]:size-4`), but it makes the intent explicit.

---

## 9. The cn() Utility

The `cn()` function is a small but critical utility used in every single shadcn/ui component:

```tsx
// frontend/lib/utils.ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

It composes two libraries:

### clsx -- Conditional Class Joining

`clsx` takes any combination of strings, objects, arrays, and falsy values and joins them into a single class string:

```tsx
clsx("foo", "bar")                          // "foo bar"
clsx("foo", undefined, "bar")               // "foo bar" (undefined ignored)
clsx("foo", false && "bar", "baz")          // "foo baz" (false ignored)
clsx("foo", { bar: true, baz: false })      // "foo bar" (object form)
clsx(["foo", "bar"])                        // "foo bar" (array form)
```

#### C# Analogy

This is like `string.Join(" ", list.Where(s => s != null))` but with support for conditional inclusion via objects and booleans.

### tailwind-merge -- Smart Class Conflict Resolution

`twMerge` understands Tailwind's class structure and resolves conflicts. Without it:

```tsx
// Without twMerge:
"p-6 pt-0"  // PROBLEM: does pt-0 override the top part of p-6? The browser sees both.
             // CSS specificity says last-defined wins, but Tailwind utility order
             // is determined by the stylesheet, not the class attribute order.

// With twMerge:
twMerge("p-6 pt-0")  // "p-6 pt-0" -- twMerge knows pt-0 should win for padding-top
```

More importantly, it handles overrides when components merge default classes with caller-provided classes:

```tsx
// Card default: "rounded-xl glass glow-hover"
// Caller adds: "rounded-none"

cn("rounded-xl glass glow-hover", "rounded-none")
// Without twMerge: "rounded-xl glass glow-hover rounded-none" -- conflicting rounded values!
// With twMerge:    "glass glow-hover rounded-none" -- rounded-xl removed, rounded-none wins
```

This is why every component passes `className` through `cn()` -- it allows callers to override any default class without duplicates or conflicts.

### The Pattern in Every Component

```tsx
// Inside a component:
className={cn("default classes here", className)}
//              ^^ component defaults     ^^ caller overrides
```

The caller's `className` comes second, so it takes priority. `twMerge` ensures no conflicting classes remain.

---

## 10. Key Patterns Summary

Here are the six patterns you have learned, with a one-line reminder of each:

### CVA (Class Variance Authority)

Define visual variants as a declarative configuration object. The function `cva()` returns a class-name generator that picks the right classes based on the variant and size you pass. Eliminates if/else chains for styling.

```tsx
const variants = cva("base classes", {
  variants: { variant: { default: "...", outline: "..." } },
  defaultVariants: { variant: "default" },
})
// Usage: variants({ variant: "outline" }) returns the combined class string
```

### forwardRef

Pass DOM element references through custom components so parents can call methods like `.focus()` or `.getBoundingClientRect()` on the underlying HTML element. Required for interactive components that might need direct DOM access.

```tsx
const MyComponent = React.forwardRef<HTMLDivElement, MyProps>(
  (props, ref) => <div ref={ref} {...props} />
)
```

### Compound Components

Group related sub-components (Card + CardHeader + CardTitle + CardContent + CardFooter) into a family that is designed to be used together. Each sub-component manages its own spacing and layout. The result is consistent structure across the entire application without duplicating layout logic.

### Spread Props (`{...props}`)

After destructuring the props you need, pass everything else through to the underlying element. This ensures standard HTML attributes like `onClick`, `disabled`, `aria-label`, and `id` work without being explicitly declared.

```tsx
function MyComponent({ variant, className, ...props }) {
  return <div className={cn(myVariants({ variant }), className)} {...props} />
  //                                                              ^^^^^^^^
  //                                  onClick, children, id, aria-label, etc.
}
```

### The Slot Pattern (asChild)

When `asChild` is true, the component does not render its own DOM element. Instead, Radix's `Slot` merges all props onto the single child element. Use this when you need a component's styling on a semantically different element (like giving button styles to an anchor tag).

### cn() -- Class Merging

Always wrap class strings in `cn()` to safely merge default classes with caller-provided overrides. Under the hood, `clsx` handles conditional values and `twMerge` resolves Tailwind class conflicts so the last value wins.

---

## Quick Reference: When to Use What

| I want to... | Use this pattern |
|---|---|
| Create a component with named visual variants | CVA (`cva()`) |
| Let parents access the DOM element | `forwardRef` |
| Build a multi-part component (header, body, footer) | Compound Components |
| Accept any standard HTML attribute | `{...props}` spread |
| Render a different element with this component's styling | `asChild` + Slot |
| Merge default and override Tailwind classes | `cn()` |
| Show a non-blocking notification | `toast.success()` / `toast.error()` from Sonner |
| Add an icon | Import from `lucide-react`, size with `h-4 w-4` |
| Wrap a Radix primitive with styling | `forwardRef` + `React.ComponentPropsWithoutRef` + `cn()` |

---

## Next Up

Document 08 will cover the project's custom application components that are built on top of these primitives: the lead table, the Kanban board, the filter system, and how they compose shadcn/ui components with React Query data fetching.
