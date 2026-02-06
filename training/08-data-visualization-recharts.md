# 08 - Data Visualization with Recharts

This is document 8 of a 10-part training guide. You already know C# and Python, and documents 01 through 07 covered JavaScript, TypeScript, React, Next.js, Tailwind CSS, React Query, and shadcn/ui. This document teaches you how to build interactive data visualizations using Recharts.

All examples come from one real file in the project: `frontend/components/charts.tsx`.

---

## 1. What is Recharts?

Recharts is a React charting library built on top of D3.js. Instead of writing imperative drawing commands (like Python's matplotlib where you call `plt.bar()`, `plt.xlabel()`, `plt.show()` in sequence), Recharts uses **declarative React components** that you compose together like building blocks.

```tsx
// Recharts: declarative composition
<BarChart data={data}>
  <XAxis dataKey="name" />
  <YAxis />
  <Bar dataKey="value" fill="blue" />
  <Tooltip />
</BarChart>
```

Compare this to the imperative approach you already know:

```python
# matplotlib: imperative sequence
fig, ax = plt.subplots()
ax.bar([d["name"] for d in data], [d["value"] for d in data], color="blue")
ax.set_xlabel("Name")
ax.set_ylabel("Value")
plt.show()
```

If you have used WPF charting in C#, Recharts will feel conceptually similar to XAML-based chart declarations. If you have used Python's Plotly library (which also supports declarative figure construction), the mental model is closer to that than to matplotlib.

The project uses **Recharts v3**. You compose a chart by nesting components: a chart-type container (`<BarChart>`, `<PieChart>`) wraps axis components (`<XAxis>`, `<YAxis>`), data-rendering components (`<Bar>`, `<Pie>`), and helper components (`<Tooltip>`, `<ResponsiveContainer>`). Each component accepts props that control its appearance and behavior. There is no canvas manipulation or SVG path generation on your part -- Recharts handles all of that.

---

## 2. Data Shape

Recharts charts expect their data as an **array of plain objects**. Each object represents one data point, and you tell Recharts which property to use for labels and which to use for values.

### The transform pattern used in this project

The stats API returns data in a dictionary-like shape:

```tsx
// The API returns: Record<string, number>
// Example: { "restaurant": 30, "bar": 15, "retail": 12 }
```

Recharts needs an array of objects. The project transforms the API response like this:

```tsx
const chartData: ChartData[] = Object.entries(data).map(([name, value]) => ({
  name: name || "other",
  value,
}));
// Result: [{ name: "restaurant", value: 30 }, { name: "bar", value: 15 }, ...]
```

Let's break this down piece by piece.

**`Object.entries(data)`** converts an object's key-value pairs into an array of two-element arrays. This is the JavaScript equivalent of:

- Python: `list(data.items())` -- returns `[("restaurant", 30), ("bar", 15), ...]`
- C#: `data.Select(kv => new { kv.Key, kv.Value })` on a `Dictionary<string, int>`

The result is `[["restaurant", 30], ["bar", 15], ["retail", 12]]`.

**`.map(([name, value]) => ...)`** iterates over that array and transforms each two-element array into an object. The `[name, value]` syntax is **array destructuring** -- it assigns the first element to `name` and the second to `value`. This is like Python's tuple unpacking: `for name, value in data.items()`.

**`name || "other"`** uses JavaScript's logical OR operator as a fallback. If `name` is an empty string (which is falsy in JavaScript), it substitutes `"other"`. This is equivalent to Python's `name or "other"`.

**`{ name, value }`** uses shorthand property syntax. When the variable name matches the property name, you can omit the colon: `{ name }` is the same as `{ name: name }`.

### Sorting and slicing

The `CountyBarChart` uses an additional transform to sort the data and take only the top 8 results:

```tsx
const chartData: ChartData[] = Object.entries(data)
  .map(([name, value]) => ({ name: name || "Unknown", value }))
  .sort((a, b) => b.value - a.value)  // Descending by value
  .slice(0, 8);                        // Top 8 only
```

**`.sort((a, b) => b.value - a.value)`** sorts in descending order. The comparison function returns a negative number if `a` should come first, positive if `b` should come first, and zero if they are equal. Since `b.value - a.value` is positive when `b` is larger, the larger values sort to the front. This is the same logic as Python's `sorted(data, key=lambda x: x["value"], reverse=True)` or C#'s `data.OrderByDescending(x => x.Value)`.

**`.slice(0, 8)`** takes the first 8 elements of the sorted array. This is like Python's `data[:8]` or C#'s `data.Take(8)`.

The reason for limiting to 8: a bar chart with 30 county names would be unreadable. Show only the most important ones.

---

## 3. The Pie/Donut Chart (TypePieChart)

This component renders a donut chart showing lead counts by business type (restaurant, bar, retail, etc.). Here is the complete implementation from the project:

```tsx
export function TypePieChart({ data, onSegmentClick }: TypeChartProps) {
  const router = useRouter();
  const chartData: ChartData[] = Object.entries(data).map(([name, value]) => ({
    name: name || "other",
    value,
  }));

  const handleClick = (entry: ChartData) => {
    if (onSegmentClick) {
      onSegmentClick("type", entry.name);
    } else {
      router.push(`/leads?q=${encodeURIComponent(entry.name)}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Leads by Type
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) =>
                `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`
              }
              outerRadius={80}
              innerRadius={40}
              fill="#8884d8"
              dataKey="value"
              onClick={(_, index) => handleClick(chartData[index])}
              style={{ cursor: "pointer" }}
              strokeWidth={0}
            >
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                  className="transition-opacity hover:opacity-80"
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color: "hsl(213, 31%, 91%)" }}
            />
          </PieChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Click a segment to filter leads
        </p>
      </CardContent>
    </Card>
  );
}
```

### Component-by-component explanation

**`<ResponsiveContainer width="100%" height={250}>`**

This wrapper makes the chart resize automatically when its parent container changes size. Without it, SVG charts render at a fixed pixel size and will not adapt to different screen widths. You set `width="100%"` to fill the container and `height={250}` as a fixed pixel height.

In C# WPF terms, this is like setting `HorizontalAlignment="Stretch"` on a chart control.

**`<PieChart>`**

The chart-type container. It does not render anything visible itself -- it establishes the coordinate system and provides context for its children. Every Recharts chart starts with one of these container components (`PieChart`, `BarChart`, `LineChart`, etc.).

**`<Pie>`**

This is the component that actually draws the pie/donut shape. Its props control everything about the visualization:

- **`data={chartData}`** -- the array of `{ name, value }` objects
- **`cx="50%" cy="50%"`** -- the center coordinates of the pie. `"50%"` means the center of the container, both horizontally and vertically
- **`innerRadius={40}`** -- this is what makes it a **donut** instead of a solid pie. If you set `innerRadius={0}`, you get a solid filled pie chart. Setting it to 40 creates a 40-pixel hole in the center
- **`outerRadius={80}`** -- the outer edge of the donut, 80 pixels from center
- **`dataKey="value"`** -- tells Recharts which property in each data object represents the numeric size of each segment. With `{ name: "restaurant", value: 30 }`, the `value` property determines segment size
- **`fill="#8884d8"`** -- the default fill color. This gets overridden by individual `<Cell>` components (explained below), but Recharts requires a default
- **`label`** -- a custom label function. Recharts calls this function for each segment, passing an object with properties like `name`, `value`, `percent`, etc. The function returns a string:
  ```tsx
  label={({ name, percent }) =>
    `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`
  }
  // Renders: "restaurant (42%)"
  ```
  Note `percent ?? 0`: the `??` is the **nullish coalescing operator** (covered in doc 02). It returns the right side only if the left side is `null` or `undefined`. Then `* 100` converts 0.42 to 42, and `.toFixed(0)` rounds to zero decimal places.
- **`labelLine={false}`** -- by default, Recharts draws small lines from each segment to its label. This disables those lines for a cleaner look
- **`strokeWidth={0}`** -- removes the border lines between segments. By default, each segment has a thin stroke separating it from neighbors
- **`onClick={(_, index) => handleClick(chartData[index])}`** -- fires when a user clicks a segment. The first argument is the Recharts event data (ignored with `_`), the second is the index. We use the index to look up the original data item
- **`style={{ cursor: "pointer" }}`** -- shows a pointer cursor on hover, signaling clickability

**`<Cell>`**

Each segment of the pie needs its own color. You do this by rendering a `<Cell>` component for each data point inside the `<Pie>`:

```tsx
{chartData.map((_, index) => (
  <Cell
    key={`cell-${index}`}
    fill={COLORS[index % COLORS.length]}
    className="transition-opacity hover:opacity-80"
  />
))}
```

`COLORS[index % COLORS.length]` cycles through the color palette. If there are 8 data points but only 6 colors, the modulo operator (`%`) wraps back around: index 6 uses `COLORS[0]`, index 7 uses `COLORS[1]`. This is the same as Python's `COLORS[index % len(COLORS)]`.

The `className="transition-opacity hover:opacity-80"` adds a Tailwind CSS hover effect: when the user hovers over a segment, its opacity smoothly transitions to 80%.

**`<Tooltip>`**

Renders a popup box when the user hovers over a chart segment showing the data value. The `contentStyle` prop accepts a CSS object to style the popup, and `itemStyle` styles the text within it. More on tooltip styling in Section 7.

**The wrapping `<Card>` components**

The chart is wrapped in shadcn/ui `<Card>`, `<CardHeader>`, `<CardTitle>`, and `<CardContent>` components. These provide the glass-panel container that matches the rest of the dashboard. The chart components handle only the visualization -- layout and framing is your responsibility.

---

## 4. The Vertical Bar Chart (CountyBarChart)

This component shows lead counts by county as vertical bars. Here is the chart portion:

```tsx
export function CountyBarChart({ data, onSegmentClick }: TypeChartProps) {
  const router = useRouter();
  const chartData: ChartData[] = Object.entries(data)
    .map(([name, value]) => ({ name: name || "Unknown", value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const handleClick = (entry: ChartData) => {
    if (onSegmentClick) {
      onSegmentClick("county", entry.name);
    } else {
      router.push(`/leads?county=${encodeURIComponent(entry.name)}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Leads by County
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color: "hsl(213, 31%, 91%)" }}
              cursor={{ fill: "hsl(226, 70%, 55%, 0.08)" }}
            />
            <Bar
              dataKey="value"
              fill="hsl(226, 70%, 60%)"
              radius={[6, 6, 0, 0]}
              onClick={(entry) => {
                if (entry.name) {
                  const value = Array.isArray(entry.value)
                    ? entry.value[0]
                    : entry.value;
                  handleClick({ name: entry.name, value });
                }
              }}
              style={{ cursor: "pointer" }}
            />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Click a bar to filter leads
        </p>
      </CardContent>
    </Card>
  );
}
```

### Component-by-component explanation

**`<BarChart data={chartData}>`**

The container for a bar chart. By default, bars are vertical (categories along the X-axis, values along the Y-axis). The `data` prop receives the array of objects.

**`<XAxis>`**

Renders the horizontal axis along the bottom of the chart.

```tsx
<XAxis
  dataKey="name"
  tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
  axisLine={false}
  tickLine={false}
/>
```

- `dataKey="name"` -- tells the axis which property in the data objects to use as labels. With `{ name: "Davidson", value: 30 }`, the label will be "Davidson"
- `tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}` -- styles the tick labels. This is a CSS-like object where `fill` controls text color (because SVG uses `fill` instead of `color`). The gray HSL value keeps the labels subtle
- `axisLine={false}` -- hides the horizontal line that normally runs along the bottom of the chart. This creates a cleaner, more modern look
- `tickLine={false}` -- hides the small perpendicular marks that normally appear at each label position

**`<YAxis>`**

Renders the vertical axis on the left. It automatically calculates the numeric scale from your data. Same styling props apply. There is no `dataKey` because the Y-axis automatically uses the numeric values.

**`<Tooltip>`**

Same as in the pie chart, with one addition:

```tsx
cursor={{ fill: "hsl(226, 70%, 55%, 0.08)" }}
```

The `cursor` prop on a bar chart's Tooltip renders a **highlight rectangle** behind the bar you are hovering over. The nearly-transparent blue fill (`0.08` alpha) provides a subtle visual cue without obscuring the bar itself.

**`<Bar>`**

The actual bar series.

```tsx
<Bar
  dataKey="value"
  fill="hsl(226, 70%, 60%)"
  radius={[6, 6, 0, 0]}
  onClick={...}
  style={{ cursor: "pointer" }}
/>
```

- `dataKey="value"` -- which property determines bar height
- `fill="hsl(226, 70%, 60%)"` -- bar color (a medium blue)
- `radius={[6, 6, 0, 0]}` -- rounded corners. The array specifies `[topLeft, topRight, bottomLeft, bottomRight]` radii in pixels. `[6, 6, 0, 0]` means the top of each bar is rounded while the bottom is flat (because vertical bars grow upward from the baseline)
- `onClick` -- fires when the user clicks a bar. Note the Recharts v3 click handler here differs slightly from the Pie chart pattern:
  ```tsx
  onClick={(entry) => {
    if (entry.name) {
      const value = Array.isArray(entry.value) ? entry.value[0] : entry.value;
      handleClick({ name: entry.name, value });
    }
  }}
  ```
  The `Array.isArray(entry.value) ? entry.value[0] : entry.value` guard handles the fact that Recharts may pass `value` as either a number or an array (in stacked bar charts, it passes `[start, end]`). This defensive check ensures the value is always a plain number.
- `style={{ cursor: "pointer" }}` -- pointer cursor on hover

---

## 5. The Horizontal Bar Chart (StageBarChart)

This component shows lead counts by pipeline stage (New, Qualified, Contacted, etc.) as horizontal bars:

```tsx
export function StageBarChart({ data, onSegmentClick }: TypeChartProps) {
  const router = useRouter();
  const chartData: ChartData[] = Object.entries(data).map(([name, value]) => ({
    name,
    value,
  }));

  const handleClick = (entry: ChartData) => {
    if (onSegmentClick) {
      onSegmentClick("stage", entry.name);
    } else {
      router.push(`/leads?stage=${encodeURIComponent(entry.name)}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Leads by Stage
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} layout="vertical">
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              dataKey="name"
              type="category"
              tick={{ fontSize: 11, fill: "hsl(218, 11%, 55%)" }}
              width={80}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color: "hsl(213, 31%, 91%)" }}
              cursor={{ fill: "hsl(173, 58%, 45%, 0.08)" }}
            />
            <Bar
              dataKey="value"
              fill="hsl(173, 58%, 45%)"
              radius={[0, 6, 6, 0]}
              onClick={(entry) => {
                if (entry.name) {
                  const value = Array.isArray(entry.value)
                    ? entry.value[0]
                    : entry.value;
                  handleClick({ name: entry.name, value });
                }
              }}
              style={{ cursor: "pointer" }}
            />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Click a bar to filter leads
        </p>
      </CardContent>
    </Card>
  );
}
```

### Key differences from the vertical bar chart

**`layout="vertical"` on `<BarChart>`**

This single prop flips the entire chart orientation. Bars now extend **horizontally** from left to right instead of vertically from bottom to top.

**The axes swap roles:**

```tsx
<XAxis type="number" ... />   // X-axis now shows numbers (was categories)
<YAxis dataKey="name" type="category" width={80} ... />  // Y-axis now shows categories (was numbers)
```

In the default (vertical) layout, the X-axis is categorical and the Y-axis is numeric. With `layout="vertical"`, this reverses: the X-axis becomes the numeric scale and the Y-axis shows the category labels.

The `width={80}` on `YAxis` is important -- it reserves 80 pixels of horizontal space for the stage name labels ("New", "Qualified", "Contacted", etc.). Without this, long labels might be clipped.

**`radius={[0, 6, 6, 0]}` -- rounded RIGHT corners**

Compare to the vertical chart's `[6, 6, 0, 0]` (rounded top). Since horizontal bars extend from left to right, the "end" of each bar is on the right side. The array `[topLeft, topRight, bottomRight, bottomLeft]` with values `[0, 6, 6, 0]` rounds the right side of each bar.

**`fill="hsl(173, 58%, 45%)"` -- teal color**

Each chart in the project uses a distinct color from the palette: the county chart uses blue, the stage chart uses teal, and the type chart uses multiple colors via the COLORS array. This makes the three charts visually distinguishable when they sit side by side on the dashboard.

**`cursor={{ fill: "hsl(173, 58%, 45%, 0.08)" }}`**

The tooltip cursor highlight also uses teal (matching the bar color) at very low opacity. The county chart's cursor used blue for the same reason -- the highlight color matches the bar color.

---

## 6. Color Palette

The project defines a shared color palette used across charts:

```tsx
const COLORS = [
  "hsl(226, 70%, 60%)",   // Blue
  "hsl(173, 58%, 45%)",   // Teal
  "hsl(262, 60%, 58%)",   // Purple
  "hsl(43, 74%, 56%)",    // Gold
  "hsl(340, 75%, 55%)",   // Pink
  "hsl(200, 70%, 55%)",   // Sky blue
];
```

### HSL color format

All colors in this project use HSL notation: `hsl(hue, saturation%, lightness%)`.

- **Hue** (0-360): Position on the color wheel. 0 is red, 120 is green, 240 is blue. The values here (226, 173, 262, 43, 340, 200) are spread around the wheel for visual diversity.
- **Saturation** (0-100%): Color intensity. 0% is gray, 100% is full color. These values (58-75%) produce rich but not neon colors.
- **Lightness** (0-100%): Brightness. 0% is black, 100% is white, 50% is the "pure" color. These values (45-60%) produce medium-brightness colors that work well on both dark and light backgrounds.

If you are used to hex colors (`#3B82F6`), HSL is more intuitive for creating harmonious palettes because you can adjust hue while keeping saturation and lightness consistent.

### Cycling through colors

```tsx
{chartData.map((_, index) => (
  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
))}
```

The expression `COLORS[index % COLORS.length]` uses the modulo operator to cycle through the palette no matter how many data points there are:

| index | index % 6 | Color   |
|-------|-----------|---------|
| 0     | 0         | Blue    |
| 1     | 1         | Teal    |
| 2     | 2         | Purple  |
| 3     | 3         | Gold    |
| 4     | 4         | Pink    |
| 5     | 5         | Sky blue|
| 6     | 0         | Blue    |
| 7     | 1         | Teal    |

This is the same pattern as C#'s `COLORS[index % COLORS.Length]` or Python's `COLORS[index % len(COLORS)]`.

---

## 7. Custom Tooltip Styling

The tooltip (the popup that appears on hover) is styled to match the dark glassmorphism theme of the application:

```tsx
const tooltipStyle = {
  backgroundColor: "hsl(224, 47%, 12%)",   // Very dark blue background
  border: "1px solid hsl(223, 30%, 20%)",   // Subtle border
  borderRadius: "8px",                       // Rounded corners
  fontSize: "12px",                          // Small text
  color: "hsl(213, 31%, 91%)",              // Light gray text
  boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)", // Deep shadow for depth
};
```

This is a plain JavaScript object of CSS properties, passed to the Recharts `<Tooltip>` component:

```tsx
<Tooltip contentStyle={tooltipStyle} itemStyle={{ color: "hsl(213, 31%, 91%)" }} />
```

The `contentStyle` prop controls the outer container of the tooltip. The `itemStyle` prop controls the text styling of each data item listed inside the tooltip. Both are set to the same light gray text color for consistency.

Note that this is **inline CSS via JavaScript objects**, not Tailwind classes. Recharts components do not support Tailwind's `className` for their internal rendered elements. When a third-party library generates its own DOM/SVG elements, you often need to style them with JavaScript CSS objects or custom CSS selectors rather than utility classes.

This is a common pattern across React charting libraries. The chart library owns the SVG rendering and exposes style customization through specific props.

---

## 8. Chart Interactivity -- Click to Filter

All three charts in the project support clicking on chart elements to navigate to a filtered leads view. This turns static visualizations into interactive dashboard controls.

### The pattern

Each chart component follows the same structure:

```tsx
const handleClick = (entry: ChartData) => {
  if (onSegmentClick) {
    onSegmentClick("county", entry.name);     // Use the callback if provided
  } else {
    router.push(`/leads?county=${encodeURIComponent(entry.name)}`);  // Otherwise, navigate
  }
};
```

**`useRouter()`** comes from Next.js (`next/navigation`). It provides programmatic navigation -- `router.push(url)` navigates the browser to that URL, just like clicking a link. This is analogous to C#'s `NavigationService.Navigate()` in WPF/MAUI.

**`encodeURIComponent(entry.name)`** encodes special characters in the URL. If a county name is "St. Mary's", it becomes `St.%20Mary%27s`. Without encoding, special characters like spaces, apostrophes, and ampersands could break the URL. This is like Python's `urllib.parse.quote()` or C#'s `Uri.EscapeDataString()`.

**The `onSegmentClick` optional callback** allows parent components to override the default navigation behavior. This is a common React pattern: provide a reasonable default (navigate to filtered leads) but let the parent supply an alternative. This prop is typed as optional with `?`:

```tsx
onSegmentClick?: (filterKey: string, filterValue: string) => void;
```

If the parent does not pass `onSegmentClick`, the expression `if (onSegmentClick)` is falsy and the `else` branch runs, performing default navigation.

### Each chart navigates to different filters

The three charts filter by different fields:

| Chart             | Navigation URL                              | Filter       |
|-------------------|---------------------------------------------|--------------|
| TypePieChart      | `/leads?q=restaurant`                       | Text search  |
| CountyBarChart    | `/leads?county=Davidson`                    | County       |
| StageBarChart     | `/leads?stage=New`                          | Stage        |

Notice that `TypePieChart` uses `q=` (the text search parameter) while the others use direct field filters (`county=`, `stage=`). This is because the API supports full-text search for type names but has dedicated filter parameters for county and stage.

### How clicks are wired up

The pie chart and bar charts wire up click handlers differently due to how Recharts exposes click events.

For the `<Pie>` component:

```tsx
<Pie onClick={(_, index) => handleClick(chartData[index])} />
```

The click handler receives the Recharts event data as the first argument (which we ignore with `_`) and the segment index as the second. We use the index to look up the original data item.

For the `<Bar>` component:

```tsx
<Bar
  onClick={(entry) => {
    if (entry.name) {
      const value = Array.isArray(entry.value) ? entry.value[0] : entry.value;
      handleClick({ name: entry.name, value });
    }
  }}
/>
```

The bar click handler receives a data entry object directly. The `Array.isArray` check handles a Recharts implementation detail where `value` might be an array `[start, end]` in stacked bar charts, even though this project does not use stacked bars. Defensive coding like this prevents runtime errors if the library's behavior changes.

---

## 9. TypeScript Patterns in Charts

### Data shape interface

```tsx
interface ChartData {
  name: string;
  value: number;
}
```

This interface describes the shape of each element in the data arrays that Recharts consumes. You have seen interfaces in doc 02 -- this is a straightforward example. Every chart data point has a string `name` and a numeric `value`.

In C# terms, this is like:

```csharp
public record ChartData(string Name, int Value);
```

In Python terms (using a TypedDict or dataclass):

```python
class ChartData(TypedDict):
    name: str
    value: int
```

### Component props interface

```tsx
interface TypeChartProps {
  data: Record<string, number>;
  onSegmentClick?: (filterKey: string, filterValue: string) => void;
}
```

This interface defines what props each chart component accepts.

**`data: Record<string, number>`** -- `Record<K, V>` is a TypeScript utility type that describes an object with keys of type `K` and values of type `V`. So `Record<string, number>` means "an object where every key is a string and every value is a number," like `{ "restaurant": 30, "bar": 15 }`.

This is equivalent to:
- C#: `Dictionary<string, int>`
- Python: `Dict[str, int]`

**`onSegmentClick?: (filterKey: string, filterValue: string) => void`** -- the `?` makes this prop optional. The type `(filterKey: string, filterValue: string) => void` describes a function that takes two string arguments and returns nothing. This is like:
- C#: `Action<string, string>?`
- Python: `Optional[Callable[[str, str], None]]`

### The "use client" directive

At the top of `charts.tsx`:

```tsx
"use client";
```

This Next.js directive marks the entire file as a Client Component (covered in doc 04). Charts must be Client Components because they use browser APIs (SVG rendering, DOM events, hover states) and React hooks (`useRouter`). Server Components cannot handle interactivity.

---

## 10. How Charts Are Used on the Dashboard

The dashboard page (`frontend/app/page.tsx`) fetches stats data with React Query and passes it to all three chart components:

```tsx
import { TypePieChart, CountyBarChart, StageBarChart } from "@/components/charts";

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  // ... loading state ...

  return (
    <AppShell>
      <div className="space-y-8">
        {/* ... header ... */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <TypePieChart data={stats.by_type} />
          <CountyBarChart data={stats.by_county} />
          <StageBarChart data={stats.by_stage} />
        </div>
      </div>
    </AppShell>
  );
}
```

Key observations:

1. **Data fetching is separate from visualization.** The dashboard fetches all stats once via `useQuery`, then passes different slices (`by_type`, `by_county`, `by_stage`) to each chart. The chart components do not fetch their own data. This is the same separation of concerns discussed in the React Query doc (doc 07).

2. **The grid layout** uses Tailwind's responsive grid: one column on mobile, two on medium screens (`md:grid-cols-2`), three on large screens (`lg:grid-cols-3`). Each chart fills one grid cell.

3. **No `onSegmentClick` is passed**, so all three charts use their default navigation behavior (routing to `/leads` with the appropriate filter).

---

## Key Takeaway Summary

- **Recharts uses declarative React components** to build charts. You compose building blocks (`<BarChart>`, `<Bar>`, `<XAxis>`, `<Tooltip>`) rather than writing drawing commands.
- **Data must be an array of objects.** The project transforms API responses from `Record<string, number>` to `ChartData[]` using `Object.entries()` and `.map()`.
- **`<ResponsiveContainer>`** handles automatic resizing. Always wrap your charts in one.
- **Charts are composed from nested components:** Chart container > Axes + Data series + Tooltip. Each component is configured via props.
- **Pie vs. Donut** is controlled by a single prop: `innerRadius={0}` for pie, `innerRadius={40}` for donut.
- **Vertical vs. Horizontal bars** is controlled by `layout="vertical"` on the `<BarChart>`, with the axes swapping their `type` props.
- **Click handlers enable navigation and filtering**, turning visualizations into interactive dashboard controls.
- **Styling Recharts internals** requires JavaScript CSS objects (not Tailwind classes), because the chart library renders its own SVG elements.
- **Color palettes** cycle through using the modulo operator: `COLORS[index % COLORS.length]`.
- **TypeScript interfaces** define both the data shape (`ChartData`) and the component API (`TypeChartProps`), giving you compile-time safety over both the data flowing into charts and the props passed to chart components.
