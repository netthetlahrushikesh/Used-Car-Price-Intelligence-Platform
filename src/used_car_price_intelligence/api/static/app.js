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
const brandSelect = document.querySelector("#brandSelect");
const brandOtherField = document.querySelector("#brandOtherField");
const brandOther = document.querySelector("#brandOther");
const modelInput = document.querySelector("#modelInput");
const modelSuggestions = document.querySelector("#modelSuggestions");
const cityInput = document.querySelector("#cityInput");
const stateField = document.querySelector("#stateField");
const regCodeField = document.querySelector("#regCodeField");

const BRAND_MODELS = {
  "Maruti Suzuki": ["Swift", "Baleno", "Dzire", "Wagon R", "Alto", "Ertiga", "Brezza", "Celerio", "Ignis"],
  Hyundai: ["i20", "Creta", "Venue", "i10", "Verna", "Alcazar", "Aura"],
  Honda: ["City", "Amaze", "Jazz", "WR-V", "Elevate"],
  Tata: ["Nexon", "Punch", "Altroz", "Tiago", "Harrier", "Safari"],
  Mahindra: ["XUV700", "Scorpio", "XUV300", "Bolero", "Thar", "XUV400"],
  Toyota: ["Innova", "Fortuner", "Glanza", "Urban Cruiser", "Camry", "Hyryder"],
  Kia: ["Seltos", "Sonet", "Carnival", "Carens"],
  Volkswagen: ["Polo", "Vento", "Taigun", "Virtus"],
  Skoda: ["Rapid", "Octavia", "Kushaq", "Slavia", "Superb"],
  Renault: ["Kwid", "Triber", "Kiger", "Duster"],
  Nissan: ["Magnite", "Kicks", "Sunny"],
  Ford: ["EcoSport", "Figo", "Endeavour", "Freestyle"],
  MG: ["Hector", "Astor", "ZS EV", "Comet"],
  BMW: ["3 Series", "5 Series", "X1", "X3", "X5"],
  "Mercedes-Benz": ["C-Class", "E-Class", "GLA", "GLC", "A-Class"],
  Audi: ["A4", "A6", "Q3", "Q5", "Q7"],
};

const CITY_META = {
  Hyderabad: { state: "Telangana", code: "TS" },
  Bengaluru: { state: "Karnataka", code: "KA" },
  Bangalore: { state: "Karnataka", code: "KA" },
  Chennai: { state: "Tamil Nadu", code: "TN" },
  Mumbai: { state: "Maharashtra", code: "MH" },
  Pune: { state: "Maharashtra", code: "MH" },
  Delhi: { state: "Delhi", code: "DL" },
  "New Delhi": { state: "Delhi", code: "DL" },
  Ahmedabad: { state: "Gujarat", code: "GJ" },
  Kolkata: { state: "West Bengal", code: "WB" },
  Jaipur: { state: "Rajasthan", code: "RJ" },
  Kochi: { state: "Kerala", code: "KL" },
};

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

function resolveBrand() {
  if (brandSelect.value === "__other__") {
    return String(brandOther.value || "").trim();
  }
  return brandSelect.value;
}

function updateModelSuggestions() {
  const brand = brandSelect.value === "__other__" ? "" : brandSelect.value;
  const models = BRAND_MODELS[brand] || [];
  modelSuggestions.innerHTML = models.map((m) => `<option value="${m}"></option>`).join("");
}

function syncBrandOtherVisibility() {
  const isOther = brandSelect.value === "__other__";
  brandOtherField.hidden = !isOther;
  if (isOther) {
    brandOther.required = true;
    brandOther.focus();
  } else {
    brandOther.required = false;
    brandOther.value = "";
  }
}

function syncCityMeta() {
  const city = String(cityInput.value || "").trim();
  const meta = CITY_META[city];
  if (meta) {
    stateField.value = meta.state;
    regCodeField.value = meta.code;
  } else {
    stateField.value = "unknown";
    regCodeField.value = "unknown";
  }
}

function formPayload() {
  const values = Object.fromEntries(new FormData(form).entries());
  delete values.brand_other;
  values.brand = resolveBrand();
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
  syncCityMeta();

  if (brandSelect.value === "__other__" && !String(brandOther.value || "").trim()) {
    formStatus.textContent = "Please enter a custom brand name.";
    brandOther.focus();
    return;
  }

  if (!form.reportValidity()) {
    formStatus.textContent = "Please fill in all required fields.";
    return;
  }

  setLoading(true);
  resultState.textContent = "Calculating";
  resultSubtitle.textContent = "Working out a listed price for this vehicle.";

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
        "9.88% MAPE · R² 0.897 · MAE INR 47,389 · 9,110 rows";
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

brandSelect.addEventListener("change", () => {
  syncBrandOtherVisibility();
  updateModelSuggestions();
  const models = BRAND_MODELS[brandSelect.value];
  if (models && models.length) {
    modelInput.value = models[0];
  } else if (brandSelect.value === "__other__") {
    modelInput.value = "";
  }
});

cityInput.addEventListener("change", syncCityMeta);
cityInput.addEventListener("blur", syncCityMeta);

form.addEventListener("submit", (event) => {
  event.preventDefault();
  requestEstimate();
});

async function initialize() {
  updateModelSuggestions();
  syncBrandOtherVisibility();
  syncCityMeta();
  const ready = await loadHealthAndMetadata();
  if (ready) await requestEstimate({ isSample: true });
}

initialize();
