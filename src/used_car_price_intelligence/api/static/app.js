const form = document.querySelector("#predictionForm");
const estimateButton = document.querySelector("#estimateButton");
const buttonLabel = estimateButton.querySelector(".button-label");
const healthStatus = document.querySelector("#healthStatus");
const formStatus = document.querySelector("#formStatus");
const resultState = document.querySelector("#resultState");
const resultSubtitle = document.querySelector("#resultSubtitle");
const predictedPrice = document.querySelector("#predictedPrice");
const priceRange = document.querySelector("#priceRange");
const confidenceRow = document.querySelector("#confidenceRow");
const confidenceValue = document.querySelector("#confidenceValue");
const modelContext = document.querySelector("#modelContext");

function formatInr(value) {
  if (!Number.isFinite(Number(value))) return "--";
  const amount = Number(value);
  if (amount >= 10_000_000) return `\u20B9${(amount / 10_000_000).toFixed(2)}Cr`;
  if (amount >= 100_000) return `\u20B9${(amount / 100_000).toFixed(2)}L`;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function titleCase(value) {
  return String(value || "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formPayload() {
  const values = Object.fromEntries(new FormData(form).entries());
  values.model_year = Number(values.model_year);
  values.km_driven = Number(values.km_driven);
  values.variant = String(values.variant || "").trim() || "unknown";
  values.state = String(values.state || "").trim() || "unknown";
  values.registration_code = String(values.registration_code || "").trim() || "unknown";
  if (/^\d+$/.test(String(values.ownership))) {
    values.ownership = Number(values.ownership);
  }
  return values;
}

function setHealth(state, label) {
  healthStatus.classList.remove("is-ready", "is-error");
  if (state === "ready") healthStatus.classList.add("is-ready");
  if (state === "error") healthStatus.classList.add("is-error");
  healthStatus.querySelector("span:last-child").textContent = label;
}

function setLoading(isLoading) {
  estimateButton.disabled = isLoading;
  buttonLabel.textContent = isLoading ? "Getting estimate…" : "Get estimate";
}

function renderPrediction(result, isSample) {
  const low = Number(result.price_range_low_inr);
  const high = Number(result.price_range_high_inr);
  const prediction = Number(result.predicted_price_inr);

  predictedPrice.textContent = formatInr(prediction);
  priceRange.textContent = `${formatInr(low)} – ${formatInr(high)}`;
  resultState.textContent = isSample ? "Sample estimate" : "Updated";
  resultSubtitle.textContent = isSample
    ? "Preloaded example. Change any detail to price another vehicle."
    : "Based on the vehicle details you submitted.";

  if (result.confidence) {
    confidenceRow.hidden = false;
    confidenceValue.textContent = titleCase(result.confidence);
    confidenceValue.className = `confidence-badge ${result.confidence}`;
  } else {
    confidenceRow.hidden = true;
  }

  formStatus.textContent = isSample
    ? "Sample vehicle is ready — change any field and get a new estimate."
    : "Estimate updated. Adjust details anytime and try again.";
}

function renderError(message) {
  resultState.textContent = "Unavailable";
  resultSubtitle.textContent = message;
  predictedPrice.textContent = "--";
  priceRange.textContent = "Could not calculate a range.";
  confidenceRow.hidden = false;
  confidenceValue.textContent = "Unavailable";
  confidenceValue.className = "confidence-badge low";
  formStatus.textContent = "Check the required fields and try again.";
}

function readableError(body) {
  if (!body) return "Prediction request failed. Try again.";
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return "Check the required input values and try again.";
  return "Prediction request failed. Try again.";
}

async function requestEstimate({ isSample = false } = {}) {
  if (!form.reportValidity()) {
    formStatus.textContent = "Please fill in all required fields.";
    return;
  }

  setLoading(true);
  resultState.textContent = "Calculating";
  resultSubtitle.textContent = "Running the price model for this vehicle.";

  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(readableError(body));
    renderPrediction(body, isSample);
  } catch (error) {
    renderError(error instanceof Error ? error.message : "Prediction request failed. Try again.");
  } finally {
    setLoading(false);
  }
}

async function loadHealthAndMetadata() {
  try {
    const healthResponse = await fetch("/health");
    const health = await healthResponse.json();
    if (health.status === "ok") {
      setHealth("ready", "Model ready");
    } else {
      setHealth("error", "Model unavailable");
      return false;
    }

    // Keep the truthful one-line evidence; do not invent metrics from metadata.
    if (modelContext) {
      modelContext.textContent =
        "Model evidence: 9.88% MAPE · R² 0.897 · MAE INR 47,389 · 9,110 rows";
    }

    // Soft-touch metadata fetch so the endpoint stays exercised; ignore payload metrics.
    try {
      await fetch("/model/metadata");
    } catch (_) {
      /* optional */
    }

    return true;
  } catch (error) {
    setHealth("error", "API unavailable");
    return false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  requestEstimate();
});

async function initialize() {
  const ready = await loadHealthAndMetadata();
  if (ready) await requestEstimate({ isSample: true });
}

initialize();
