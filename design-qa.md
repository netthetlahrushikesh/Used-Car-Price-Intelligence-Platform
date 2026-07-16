# Design QA

Date: 2026-07-10

## Evidence

- Source visual truth: preserved in the left side of
  `docs/assets/stage2-web-revamp-design-qa-comparison.png`
- Desktop implementation:
  `docs/assets/stage2-web-revamp-desktop.png`
- Mobile implementation:
  `docs/assets/stage2-web-revamp-mobile.png`
- Full-view comparison:
  `docs/assets/stage2-web-revamp-design-qa-comparison.png`
- Desktop viewport override: 1487 x 1058; captured page content: 1472 x 868
- Mobile viewport: 390 x 844
- State: API-backed Maruti Suzuki Swift VXI, 2019, 45,000 km, Petrol,
  Manual, Hyderabad sample estimate

The comparison uses the selected source and rendered implementation in one
side-by-side image. A separate focused-region composite was not required: the
full-view comparison preserves the input controls, result hierarchy, range
ruler, and inspection visual at readable resolution, while the original desktop
and mobile captures were also inspected independently.

## Findings

No actionable P0, P1, or P2 findings remain.

### Fonts And Typography

- The implementation uses Inter with Segoe UI and Arial fallbacks, matching the
  neutral operational character of the source.
- Heading, form, label, result, and supporting-copy weights form a clear
  hierarchy without viewport-scaled typography or negative letter spacing.
- Mobile headings and context labels fit after the final breakpoint correction.

### Spacing And Layout Rhythm

- The wide layout preserves the source's navigation, input, result, and visual
  regions with stable grid tracks and restrained radii.
- The 390 px mobile layout stacks content without document-level horizontal
  overflow (`scrollWidth == clientWidth == 390`).
- The mobile header child now owns the full available width; the breadcrumb can
  wrap and the title uses safe overflow wrapping.

### Colors And Visual Tokens

- The forest navigation/result palette, paper background, neutral dividers,
  orange range marker, and semantic warning colors remain consistent.
- Contrast is sufficient for the verified primary labels, controls, status
  badges, and warning content.

### Image Quality And Asset Fidelity

- A real raster inspection-bay image is used in the desktop visual region.
- The image is sharp at the verified viewport, uses a compatible subject and
  palette, and is not replaced by a placeholder, CSS drawing, emoji, or custom
  SVG.
- Lucide icons are bundled locally and render without external-network reliance.

### Copy And Content

- Copy consistently says listed-price estimate and avoids a final-sale-price
  promise.
- Result values, confidence, range, coverage, and warning text come from or are
  derived from the API response.
- The implementation intentionally omits the mock's fabricated `9/10 data
  points` and comparable-listing claims because those are not present in the
  current API contract.

## Primary Interactions Tested

- Automatic sample estimate loaded successfully from the local prediction API.
- Editing the form to a premium BMW X1 scenario returned a new estimate, wider
  range, medium confidence, and premium/high-price warning.
- Desktop and mobile layouts were rendered from the running FastAPI app.
- Browser console errors and warnings checked: none in the verified states.

## Comparison History

### Iteration 1

- Earlier finding: the desktop evidence was captured below the wide-layout
  breakpoint, so the intended inspection panel was missing from the comparison.
- Resolution: repeated verification at the intended 1487 px source viewport and
  replaced the screenshot with a capture containing all three regions.
- Post-fix evidence: `docs/assets/stage2-web-revamp-desktop.png` and the final
  side-by-side comparison.

### Iteration 2

- Earlier finding: the first mobile capture exposed a narrow header-width risk.
- Resolution: set the mobile header content to full width, enabled breadcrumb
  wrapping, added safe title wrapping, and refreshed the stylesheet asset key.
- Post-fix evidence: `docs/assets/stage2-web-revamp-mobile.png`; the 390 px DOM
  check confirmed no horizontal overflow.

## Follow-up Polish

- P3: add loading skeletons if prediction latency becomes visible after remote
  deployment.
- P3: add a dedicated empty/error illustration only if real user testing shows
  the current inline error treatment is insufficient.

final result: passed
