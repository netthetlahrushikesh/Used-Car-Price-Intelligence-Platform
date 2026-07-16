const form = document.querySelector("#predictionForm");
const estimateButton = document.querySelector("#estimateButton");
const buttonLabel = estimateButton.querySelector(".button-label");
const healthStatus = document.querySelector("#healthStatus");
const formStatus = document.querySelector("#formStatus span");
const resultState = document.querySelector("#resultState");
const resultSubtitle = document.querySelector("#resultSubtitle");
const predictedPrice = document.querySelector("#predictedPrice");
const priceRange = document.querySelector("#priceRange");
const rangePct = document.querySelector("#rangePct");
const rangeMarker = document.querySelector("#rangeMarker");
const rangeLow = document.querySelector("#rangeLow");
const rangeMid = document.querySelector("#rangeMid");
const rangeHigh = document.querySelector("#rangeHigh");
const rangeNote = document.querySelector("#rangeNote");
const confidenceValue = document.querySelector("#confidenceValue");
const priceBand = document.querySelector("#priceBand");
const insightList = document.querySelector("#insightList");
const coverageCopy = document.querySelector("#coverageCopy");
const warningChips = document.querySelector("#warningChips");
const modelContext = document.querySelector("#modelContext");
const journeySteps = [...document.querySelectorAll(".journey-step")];

const warningLabels = {
  rare_or_unseen_brand_model: "Rare or unseen brand-model",
  unseen_brand: "Unseen brand",
  unseen_model: "Unseen model",
  unseen_city: "Unseen city",
  premium_or_high_price_segment: "Premium/high-price segment",
  km_outside_training_policy: "Km outside training policy",
  model_year_outside_training_policy: "Model year outside training policy",
};

function initializeIcons() {
  if (window.lucide) {
    window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
  }
}

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

function formatNumber(value) {
  return Number(value).toLocaleString("en-IN");
}

function titleCase(value) {
  return String(value || "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatPriceBand(value) {
  const labels = {
    "0_2.5L": "Under 2.5L",
    "2.5L_5L": "2.5L - 5L",
    "5L_7.5L": "5L - 7.5L",
    "7.5L_10L": "7.5L - 10L",
    "10L_20L": "10L - 20L",
    "20L_plus": "20L+",
  };
  return labels[value] || titleCase(value);
}

function formPayload() {
  const values = Object.fromEntries(new FormData(form).entries());
  values.model_year = Number(values.model_year);
  values.km_driven = Number(values.km_driven);
  values.variant = values.variant.trim() || "unknown";
  values.state = values.state.trim() || "unknown";
  values.registration_code = values.registration_code.trim() || "unknown";
  if (/^\d+$/.test(String(values.ownership))) {
    values.ownership = Number(values.ownership);
  }
  return values;
}

function validRequiredFields() {
  const payload = formPayload();
  return [
    payload.brand.trim(),
    payload.model.trim(),
    payload.city.trim(),
    Number.isFinite(payload.model_year) && payload.model_year >= 2000 && payload.model_year <= 2026,
    Number.isFinite(payload.km_driven) && payload.km_driven >= 0 && payload.km_driven <= 300_000,
    payload.fuel_type,
    payload.transmission,
  ].every(Boolean);
}

function updateJourney() {
  const payload = formPayload();
  const completed = [
    Boolean(payload.brand.trim() && payload.model.trim()),
    Number.isFinite(payload.model_year) && Number.isFinite(payload.km_driven),
    Boolean(payload.city.trim() && payload.fuel_type && payload.transmission),
  ];

  journeySteps.forEach((step, index) => {
    const complete = completed[index];
    step.classList.toggle("is-complete", complete);
    step.classList.toggle("is-active", !complete && index === completed.findIndex((value) => !value));
  });

  formStatus.textContent = validRequiredFields()
    ? "Required estimate details are ready."
    : "Complete the required vehicle, usage, and market details.";
}

function setHealth(state, label) {
  healthStatus.classList.remove("is-ready", "is-error");
  if (state === "ready") healthStatus.classList.add("is-ready");
  if (state === "error") healthStatus.classList.add("is-error");
  healthStatus.querySelector("span:last-child").textContent = label;
}

function setLoading(isLoading) {
  estimateButton.disabled = isLoading;
  buttonLabel.textContent = isLoading ? "Calculating estimate" : "Estimate fair price";
}

function clearChildren(element) {
  while (element.firstChild) element.removeChild(element.firstChild);
}

function appendListItem(list, text) {
  const item = document.createElement("li");
  item.textContent = text;
  list.append(item);
}

function renderWarnings(codes) {
  clearChildren(warningChips);

  if (!codes.length) {
    const chip = document.createElement("span");
    chip.className = "warning-chip is-clear";
    chip.textContent = "No material model warnings";
    warningChips.append(chip);
    coverageCopy.textContent = "This configuration returned no material model risk flags. Confidence is based on observed training coverage and known segment limits.";
    return;
  }

  coverageCopy.textContent = "Review these coverage notes before using the estimate as a pricing reference. They indicate inputs or segments with less reliable model coverage.";
  codes.forEach((code) => {
    const chip = document.createElement("span");
    chip.className = "warning-chip";
    chip.textContent = warningLabels[code] || titleCase(code);
    warningChips.append(chip);
  });
}

function renderInsights(input, explanation) {
  clearChildren(insightList);
  const snapshotYear = Number(input.market_snapshot_year || new Date().getFullYear());
  const age = Math.max(0, snapshotYear - Number(input.model_year));
  const vehicleName = [input.brand, input.model, input.variant !== "unknown" ? input.variant : ""]
    .filter(Boolean)
    .join(" ");

  appendListItem(insightList, `${vehicleName}, ${input.model_year} model.`);
  appendListItem(
    insightList,
    `${formatNumber(input.km_driven)} km driven, ${titleCase(input.fuel_type)}, ${titleCase(input.transmission)}.`
  );
  appendListItem(insightList, `${age} years old in the model market snapshot, priced for ${input.city}.`);
  if (explanation && explanation[1]) appendListItem(insightList, explanation[1]);
}

function renderPrediction(result, isSample) {
  const low = Number(result.price_range_low_inr);
  const high = Number(result.price_range_high_inr);
  const prediction = Number(result.predicted_price_inr);
  const markerPosition = high > low ? Math.min(95, Math.max(5, ((prediction - low) / (high - low)) * 100)) : 50;

  predictedPrice.textContent = formatInr(prediction);
  priceRange.textContent = `${formatInr(low)} to ${formatInr(high)}`;
  rangeLow.textContent = formatInr(low);
  rangeMid.textContent = formatInr(prediction);
  rangeHigh.textContent = formatInr(high);
  rangePct.textContent = `${Number(result.price_range_pct).toFixed(1)}% range width`;
  rangeMarker.style.left = `${markerPosition}%`;
  rangeNote.textContent = `This is the model's listed-price range for the submitted configuration. Range width: ${Number(result.price_range_pct).toFixed(1)}%.`;

  confidenceValue.textContent = titleCase(result.confidence);
  confidenceValue.className = `confidence-badge ${result.confidence}`;
  priceBand.textContent = formatPriceBand(result.price_band);
  resultState.textContent = isSample ? "Sample estimate" : "Estimate updated";
  resultSubtitle.textContent = isSample
    ? "Preloaded example. Change any detail to price another vehicle."
    : "Calculated from the deployed final model using your submitted details.";

  renderWarnings(result.warning_codes || []);
  renderInsights(result.input_normalized || {}, result.explanation || []);
}

function renderError(message) {
  resultState.textContent = "Estimate unavailable";
  resultSubtitle.textContent = message;
  confidenceValue.textContent = "Unavailable";
  confidenceValue.className = "confidence-badge low";
  coverageCopy.textContent = "The estimate could not be calculated. Check required fields and try again.";
  clearChildren(warningChips);
  const chip = document.createElement("span");
  chip.className = "warning-chip";
  chip.textContent = "Request needs attention";
  warningChips.append(chip);
}

function readableError(body) {
  if (!body) return "Prediction request failed. Try again.";
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return "Check the required input values and try again.";
  return "Prediction request failed. Try again.";
}

async function requestEstimate({ isSample = false } = {}) {
  if (!form.reportValidity()) {
    updateJourney();
    return;
  }

  setLoading(true);
  resultState.textContent = "Calculating";
  resultSubtitle.textContent = "Running the final price model for this vehicle.";

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
      setHealth("error", "Model artifact missing");
      return false;
    }

    const metadataResponse = await fetch("/model/metadata");
    if (metadataResponse.ok) {
      const metadata = await metadataResponse.json();
      const metrics = metadata.validation_metrics || {};
      const primaryMape = metrics.primary_split_mape || "9.88";
      const repeatedMape = metrics.repeated_split_mean_mape || "10.33";
      const rows = Number(metadata.training_rows || 9110).toLocaleString("en-IN");
      modelContext.textContent = `Final model: ${metadata.model_name || "Combined Trusted Lineage Target-Encoded Native HGB"}. Validated on ${rows} trusted listings: ${primaryMape}% primary MAPE and ${repeatedMape}% repeated-split mean MAPE.`;
    }
    return true;
  } catch (error) {
    setHealth("error", "API unavailable");
    modelContext.textContent = "Model validation context is unavailable because the local API is not responding.";
    return false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  requestEstimate();
});

form.addEventListener("input", updateJourney);
form.addEventListener("change", updateJourney);

async function initialize() {
  initializeIcons();
  updateJourney();
  const ready = await loadHealthAndMetadata();
  if (ready) await requestEstimate({ isSample: true });
}

initialize();
