# Stage 2 Web Prediction Workspace

Created: 2026-07-02
Revised: 2026-07-10

## Goal

Create a usable pricing workspace connected to the FastAPI model endpoint. The
screen must let a user move from vehicle details to an evidence-aware listed-
price estimate without exposing notebook or service-layer complexity.

The implemented workflow is:

1. enter vehicle and market fields
2. call the deployed model artifact through `/predict`
3. display estimated listed price, range, confidence, coverage, and warnings
4. explain that the output is a listed-price estimate, not a sale price or quote

## Implementation

The screen is served by FastAPI:

```text
GET /
```

Static files:

```text
src/used_car_price_intelligence/api/static/index.html
src/used_car_price_intelligence/api/static/styles.css
src/used_car_price_intelligence/api/static/app.js
src/used_car_price_intelligence/api/static/assets/inspection-bay.jpg
src/used_car_price_intelligence/api/static/assets/lucide.min.js
```

The UI calls:

```text
GET /health
GET /model/metadata
POST /predict
```

## Product Design

The screen is an operational pricing tool rather than a marketing landing page.
Its desktop composition has three connected regions:

1. a compact navigation rail
2. a guided vehicle form and pricing result workspace
3. a real inspection-bay visual that reinforces the trusted-source context

The result surface includes the model estimate, lower and upper guides, range
position, confidence, input-specific reasoning, price-band coverage, warnings,
and validation context. It does not invent comparable listings, transaction
prices, demand scores, or dealer activity that the API does not return.

## Responsive Behavior

- At wide desktop widths, the form, result, and inspection visual are visible
  together.
- At medium desktop and tablet widths, the visual panel is removed so the form
  and result retain usable dimensions.
- At mobile widths, the rail becomes a top toolbar and the form/result stack in
  one column.
- The 390 px verification viewport has no horizontal document overflow.

## Model Runtime Compatibility

The serialized artifact was produced with scikit-learn 1.8.0. The modeling and
notebook dependency groups therefore pin `scikit-learn==1.8.0` so the artifact
loads reproducibly instead of relying on a newer incompatible runtime.

## Local Run

```powershell
python scripts/run_prediction_api.py --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

API docs remain available at:

```text
http://127.0.0.1:8000/docs
```

## Verification Evidence

```text
docs/assets/stage2-web-revamp-desktop.png
docs/assets/stage2-web-revamp-mobile.png
docs/assets/stage2-web-revamp-design-qa-comparison.png
design-qa.md
```

The final browser pass covered the preloaded market example and a premium BMW
X1 scenario that returned a wider range and premium-segment warning. No browser
console errors or warnings were present in the verified states.

## Next Step

Package the API and local model artifact for deployment, then add monitoring,
saved comparisons, and real market-comparable services as separate product
capabilities. The current screen must not present those future capabilities as
already available.
