"""Core source-independent parsers for used-car listing fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any
from urllib.parse import unquote, urlparse


NULL_TOKENS = {
    "",
    " ",
    "-",
    "--",
    "na",
    "n/a",
    "not available",
    "null",
    "none",
    "call for price",
    "ask for price",
}

PRICE_UNITS = {
    "k": 1_000,
    "thousand": 1_000,
    "l": 100_000,
    "lac": 100_000,
    "lacs": 100_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "cr": 10_000_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
}

SPINNY_LOCATION_SLUG_SUFFIXES = (
    "btm-layout",
    "dadar-west",
    "dwarka-sector-21",
    "kukatpally",
    "vadapalani",
)

SPINNY_VARIANT_UPPERCASE_TOKENS = {
    "abs",
    "amt",
    "at",
    "bs",
    "cng",
    "crdi",
    "cvt",
    "dct",
    "dsg",
    "ev",
    "gt",
    "gtx",
    "htk",
    "htx",
    "imt",
    "ivt",
    "ldi",
    "lpg",
    "lxi",
    "mt",
    "suv",
    "sx",
    "tdci",
    "tdi",
    "tsi",
    "vdi",
    "vtvt",
    "vxi",
    "xv",
    "zdi",
    "zx",
    "zxi",
}

KM_UNITS = {
    "k": 1_000,
    "thousand": 1_000,
}

FUEL_SYNONYMS = {
    "petrol_cng": ("petrol cng", "petrol + cng", "petrol/cng", "cng petrol", "cng + petrol"),
    "petrol_lpg": ("petrol lpg", "petrol + lpg", "petrol/lpg", "lpg petrol", "lpg + petrol"),
    "electric": ("electric", "ev"),
    "hybrid": ("petrol hybrid", "strong hybrid", "mild hybrid", "hybrid"),
    "petrol": ("petrol", "gasoline"),
    "diesel": ("diesel",),
    "cng": ("cng",),
    "lpg": ("lpg",),
}

TRANSMISSION_SYNONYMS = {
    "amt": ("amt", "automated manual"),
    "imt": ("imt", "intelligent manual"),
    "cvt": ("cvt",),
    "ivt": ("ivt", "intelligent variable"),
    "dct": ("dct", "dsg"),
    "automatic": ("automatic", "auto", "at"),
    "manual": ("manual", "mt"),
}

STATE_PREFIXES = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DD": "Daman and Diu",
    "DL": "Delhi",
    "DN": "Dadra and Nagar Haveli",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "TS": "Telangana",
    "TG": "Telangana",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
}

LEGACY_STATE_PREFIX_ALIASES = {
    "OR": {
        "canonical_prefix": "OD",
        "registration_state": "Odisha",
    },
    "UA": {
        "canonical_prefix": "UK",
        "registration_state": "Uttarakhand",
    },
}

RTO_LOCATION_ALIASES = {
    "PORT BLAIR": {
        "registration_code": "AN01",
        "registration_state": "Andaman and Nicobar Islands",
    },
}

KNOWN_BRAND_ALIASES = {
    "Maruti Suzuki": ("Maruti Suzuki", "Maruti"),
    "Mercedes-Benz": ("Mercedes-Benz", "Mercedes Benz", "Mercedes"),
    "Volkswagen": ("Volkswagen",),
    "Mahindra": ("Mahindra",),
    "Hyundai": ("Hyundai",),
    "Toyota": ("Toyota",),
    "Renault": ("Renault",),
    "Nissan": ("Nissan",),
    "Honda": ("Honda",),
    "Skoda": ("Skoda",),
    "Tata": ("Tata",),
    "Ford": ("Ford",),
    "Kia": ("Kia",),
    "MG": ("MG", "MG Motors"),
    "BMW": ("BMW",),
    "Audi": ("Audi",),
    "Jeep": ("Jeep",),
    "Volvo": ("Volvo",),
    "Isuzu": ("Isuzu",),
    "Datsun": ("Datsun",),
    "Fiat": ("Fiat",),
    "Chevrolet": ("Chevrolet",),
    "Mitsubishi": ("Mitsubishi",),
    "Citroen": ("Citroen",),
    "BYD": ("BYD",),
    "Jaguar": ("Jaguar",),
    "Lexus": ("Lexus",),
    "Mini": ("Mini", "MINI"),
}

KNOWN_MODELS_BY_BRAND = {
    "Honda": {
        "Jazz": ("Jazz",),
        "City": ("City",),
        "Amaze": ("Amaze",),
        "Elevate": ("Elevate",),
        "Civic": ("Civic",),
        "WR-V": ("WR-V", "WR V"),
        "BR-V": ("BR-V", "BR V"),
    },
    "Hyundai": {
        "Elite i20": ("Elite i20",),
        "i20 Active": ("i20 Active",),
        "Grand i10 Nios": ("Grand i10 Nios",),
        "i20": ("i20",),
        "Fluidic Verna 4S": ("Fluidic Verna 4S",),
        "New Santro": ("New Santro",),
        "Venue": ("Venue",),
        "Xcent": ("Xcent",),
        "Creta": ("Creta",),
        "Grand i10": ("Grand i10",),
        "Alcazar": ("Alcazar",),
        "Aura": ("Aura",),
        "Eon": ("Eon",),
        "i10": ("i10",),
        "Santro": ("Santro", "Santro Xing"),
        "Verna": ("Verna",),
    },
    "Kia": {
        "Carens": ("Carens",),
        "Seltos": ("Seltos",),
        "Sonet": ("Sonet",),
    },
    "Mahindra": {
        "Bolero Neo": ("Bolero Neo",),
        "TUV300": ("TUV300", "TUV 300"),
        "XUV 3XO": ("XUV 3XO", "XUV3XO"),
        "XUV300": ("XUV300", "XUV 300"),
        "XUV700": ("XUV700", "XUV 700"),
        "XUV500": ("XUV500", "XUV 500"),
        "Scorpio N": ("Scorpio N", "Scorpio-N"),
        "Scorpio": ("Scorpio",),
        "Thar": ("Thar",),
        "KUV100": ("KUV100", "KUV 100"),
    },
    "Maruti Suzuki": {
        "Alto 800": ("Alto 800",),
        "Alto K10": ("Alto K10",),
        "Alto": ("Alto",),
        "Baleno": ("Baleno",),
        "Brezza": ("Brezza",),
        "Celerio": ("Celerio",),
        "Ciaz": ("Ciaz",),
        "Eeco": ("Eeco",),
        "Ertiga": ("Ertiga",),
        "Fronx": ("Fronx",),
        "Grand Vitara": ("Grand Vitara",),
        "Ignis": ("Ignis",),
        "Omni": ("Omni",),
        "Ritz": ("Ritz",),
        "S-Cross": ("S-Cross", "S Cross"),
        "Swift Dzire": ("Swift Dzire", "Swift-Dzire", "Dzire"),
        "Swift": ("Swift",),
        "SX4": ("SX4", "Sx4"),
        "Vitara Brezza": ("Vitara Brezza", "Vitara-Brezza"),
        "Wagon R": ("Wagon R", "Wagon-R"),
        "S-Presso": ("S-Presso", "S Presso"),
        "XL6": ("XL6", "Xl6"),
    },
    "Mercedes-Benz": {
        "C-Class": ("C-Class", "C Class"),
        "GLA Class": ("GLA Class", "GLA-Class"),
        "GLA": ("GLA",),
        "GLC": ("GLC",),
    },
    "MG": {
        "Hector Plus": ("Hector Plus",),
        "Hector": ("Hector",),
        "Astor": ("Astor",),
        "ZS EV": ("ZS EV", "ZS-EV"),
    },
    "Nissan": {
        "Magnite": ("Magnite",),
        "Micra Active": ("Micra Active",),
        "Micra": ("Micra",),
    },
    "Renault": {
        "Triber": ("Triber",),
        "Kiger": ("Kiger",),
        "Kwid": ("Kwid",),
    },
    "Skoda": {
        "Kodiaq": ("Kodiaq",),
        "Kushaq": ("Kushaq",),
        "Kylaq": ("Kylaq",),
        "Octavia": ("Octavia",),
        "Rapid": ("Rapid",),
        "Slavia": ("Slavia",),
    },
    "Tata": {
        "Altroz": ("Altroz",),
        "Curvv": ("Curvv",),
        "Harrier": ("Harrier",),
        "Nexon EV": ("Nexon EV", "Nexon-EV"),
        "Nexon": ("Nexon",),
        "Punch": ("Punch",),
        "Nano": ("Nano",),
        "Hexa": ("Hexa",),
        "Tigor EV": ("Tigor EV", "Tigor-EV"),
        "Tigor": ("Tigor",),
        "Tiago EV": ("Tiago EV",),
        "Tiago": ("Tiago",),
    },
    "Toyota": {
        "Fortuner": ("Fortuner",),
        "Innova Crysta": ("Innova Crysta",),
        "Innova Hycross": ("Innova Hycross",),
        "Urban Cruiser Hyryder": ("Urban Cruiser Hyryder",),
        "Urban Cruiser": ("Urban Cruiser",),
        "Corolla": ("Corolla",),
        "Etios": ("Etios",),
        "Glanza": ("Glanza",),
        "Yaris": ("Yaris",),
    },
    "Volkswagen": {
        "Polo": ("Polo",),
        "Taigun": ("Taigun",),
        "T-Roc": ("T-Roc", "T Roc"),
        "Vento": ("Vento",),
        "Virtus": ("Virtus",),
    },
    "Audi": {
        "A4": ("A4",),
        "Q3": ("Q3",),
    },
    "BMW": {
        "X1": ("X1",),
    },
    "BYD": {
        "Seal": ("Seal",),
    },
    "Jaguar": {
        "XE": ("XE",),
    },
    "Lexus": {
        "NX": ("NX",),
    },
    "Mini": {
        "Countryman": ("Countryman",),
    },
    "Jeep": {
        "Compass": ("Compass",),
    },
    "Ford": {
        "EcoSport": ("EcoSport", "Ecosport"),
        "Freestyle": ("Freestyle",),
        "Figo": ("Figo",),
    },
    "Volvo": {
        "S80": ("S80",),
    },
}


@dataclass(frozen=True)
class ParseResult:
    """Result object returned by all shared parsers."""

    raw_value: Any
    normalized_value: Any
    confidence: float
    warnings: list[str] = field(default_factory=list)
    failure_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.failure_reason is None


def normalize_null(value: Any) -> str | None:
    """Return normalized text or None for known null-like tokens."""

    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.lower() in NULL_TOKENS:
        return None
    return text


def _fail(raw_value: Any, warning: str) -> ParseResult:
    return ParseResult(
        raw_value=raw_value,
        normalized_value=None,
        confidence=0.0,
        warnings=[warning],
        failure_reason=warning,
    )


def _normalize_search_text(text: str) -> str:
    lowered = text.lower().replace("\u20b9", " ")
    lowered = lowered.replace(",", "")
    lowered = re.sub(r"[|/+]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _alias_pattern(alias: str) -> str:
    words = [re.escape(word) for word in re.split(r"[\s-]+", alias.strip()) if word]
    return r"[-\s]+".join(words)


def _match_brand(text: str) -> tuple[str | None, str]:
    aliases: list[tuple[str, str]] = []
    for canonical, brand_aliases in KNOWN_BRAND_ALIASES.items():
        aliases.extend((canonical, alias) for alias in brand_aliases)

    for canonical, alias in sorted(aliases, key=lambda item: len(item[1]), reverse=True):
        match = re.search(rf"\b{_alias_pattern(alias)}\b", text, flags=re.IGNORECASE)
        if match:
            remaining = f"{text[: match.start()]} {text[match.end() :]}"
            return canonical, re.sub(r"\s+", " ", remaining).strip()
    return None, text


def _match_model(brand: str | None, text: str) -> tuple[str | None, str | None]:
    if brand is None:
        return None, None

    model_aliases = KNOWN_MODELS_BY_BRAND.get(brand, {})
    candidates: list[tuple[str, str]] = []
    for canonical, aliases in model_aliases.items():
        candidates.extend((canonical, alias) for alias in aliases)

    for canonical, alias in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
        match = re.match(rf"^\s*{_alias_pattern(alias)}\b", text, flags=re.IGNORECASE)
        if match:
            variant = _normalize_variant_text(text[match.end() :])
            return canonical, variant or None
    return None, None


def _normalize_variant_text(text: str) -> str | None:
    variant = re.sub(r"\s+", " ", text).strip(" -|/")
    if not variant:
        return None
    variant = re.sub(r"\b(\d)[-\s]+(\d)\b", r"\1.\2", variant)
    if re.fullmatch(r"\d\.\dL?", variant, flags=re.IGNORECASE):
        return None
    return variant


def is_price_like_text(value: Any) -> bool:
    """Return true when a text field is clearly a price, not a variant."""

    text = normalize_null(value)
    if text is None:
        return False
    normalized = _normalize_search_text(text)
    return (
        re.search(
            r"^(?:rs\.?\s*|inr\s*|\u20b9\s*)?\d+(?:[,.]\d+)?\s*(?:lakhs?|lacs?|lac|cr|crore|crores)\b",
            normalized,
            flags=re.I,
        )
        is not None
        or re.search(r"^(?:rs\.?\s*|inr\s*|\u20b9\s*)\d[\d,]*(?:\.\d+)?\b", normalized, flags=re.I)
        is not None
    )


def parse_spinny_variant_from_listing_url(value: Any) -> str | None:
    """Recover Spinny variant text from listing URL slugs when card text is incomplete."""

    url_text = normalize_null(value)
    if url_text is None:
        return None

    path_parts = [unquote(part) for part in urlparse(url_text).path.split("/") if part]
    try:
        root_index = path_parts.index("buy-used-cars")
    except ValueError:
        return None

    variant_index = root_index + 4
    if len(path_parts) <= variant_index:
        return None

    variant_slug = path_parts[variant_index].strip().lower()
    if not variant_slug or variant_slug.isdigit():
        return None

    variant_slug = re.sub(r"-(?:19|20)\d{2}$", "", variant_slug)
    for suffix in SPINNY_LOCATION_SLUG_SUFFIXES:
        variant_slug = re.sub(rf"-{re.escape(suffix)}$", "", variant_slug)
    variant_slug = variant_slug.strip("-")
    if not variant_slug:
        return None

    words = [_format_spinny_variant_token(token) for token in variant_slug.split("-") if token]
    variant = re.sub(r"\s+", " ", " ".join(words)).strip()
    return variant or None


def _format_spinny_variant_token(token: str) -> str:
    token = token.strip()
    if not token:
        return ""
    displacement = re.fullmatch(r"(\d)(\d)l", token)
    if displacement:
        return f"{displacement.group(1)}.{displacement.group(2)}L"
    if token == "o":
        return "(O)"
    if token in SPINNY_VARIANT_UPPERCASE_TOKENS:
        return token.upper()
    if re.fullmatch(r"[a-z]{1,3}\d+", token):
        return token.upper()
    return token.capitalize()


def parse_price_inr(value: Any) -> ParseResult:
    """Parse Indian used-car price text into integer INR."""

    text = normalize_null(value)
    if text is None:
        return _fail(value, "missing_price")

    normalized = _normalize_search_text(text)
    warnings: list[str] = []

    if "emi" in normalized:
        warnings.append("price_text_contains_emi")
    if "charge" in normalized or "charges" in normalized:
        warnings.append("price_text_contains_extra_charges")

    cleaned = re.sub(r"\b(rs\.?|inr|rupees?|only)\b", " ", normalized)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    pattern = re.compile(
        r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*"
        r"(crores?|cr|lakhs?|lacs?|lac|l|thousand|k)?(?![a-z])"
    )
    candidates: list[int] = []
    for match in pattern.finditer(cleaned):
        number = float(match.group(1))
        unit = match.group(2)
        multiplier = PRICE_UNITS.get(unit or "", 1)
        candidates.append(round(number * multiplier))

    if not candidates:
        return _fail(value, "missing_price")

    if len(candidates) > 1:
        warnings.append("multiple_price_candidates")

    parsed = candidates[0]
    if parsed <= 0:
        return _fail(value, "invalid_price")
    if parsed < 50_000:
        warnings.append("price_below_soft_minimum")
    if parsed > 50_000_000:
        warnings.append("price_above_soft_maximum")

    confidence = 0.98
    if warnings:
        confidence = 0.82 if "price_text_contains_emi" in warnings else 0.9

    return ParseResult(
        raw_value=value,
        normalized_value=parsed,
        confidence=confidence,
        warnings=warnings,
    )


def parse_km_driven(value: Any) -> ParseResult:
    """Parse kilometers driven into an integer kilometer value."""

    text = normalize_null(value)
    if text is None:
        return _fail(value, "missing_km")

    normalized = _normalize_search_text(text)
    cleaned = re.sub(r"\b(kms?|kilometers?|driven)\b", " ", normalized)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    pattern = re.compile(r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*(thousand|k)?(?![a-z])")

    candidates: list[int] = []
    for match in pattern.finditer(cleaned):
        number = float(match.group(1))
        unit = match.group(2)
        multiplier = KM_UNITS.get(unit or "", 1)
        candidates.append(round(number * multiplier))

    if not candidates:
        return _fail(value, "missing_km")

    parsed = max(candidates)
    warnings: list[str] = []
    if parsed < 0:
        return _fail(value, "invalid_km")
    if parsed > 300_000:
        warnings.append("km_above_soft_maximum")
    if parsed > 500_000:
        warnings.append("km_above_hard_maximum")

    return ParseResult(
        raw_value=value,
        normalized_value=parsed,
        confidence=0.96 if not warnings else 0.82,
        warnings=warnings,
        failure_reason="invalid_km" if "km_above_hard_maximum" in warnings else None,
    )


def parse_ownership(value: Any) -> ParseResult:
    """Parse owner count into an integer where possible."""

    text = normalize_null(value)
    if text is None:
        return _fail(value, "missing_ownership")

    normalized = _normalize_search_text(text)
    direct_owner_only = "direct owner" in normalized and not re.search(r"\d|first|second|third", normalized)
    if direct_owner_only:
        return ParseResult(
            raw_value=value,
            normalized_value=None,
            confidence=0.4,
            warnings=["owner_text_is_seller_type_not_owner_count"],
            failure_reason="owner_text_is_seller_type_not_owner_count",
        )

    patterns = [
        (1, r"\b(1|1st|first|single|one)\b"),
        (2, r"\b(2|2nd|second|two)\b"),
        (3, r"\b(3|3rd|third|three)\b"),
        (4, r"\b(4|4th|fourth|four)\b"),
        (5, r"\b(5|5th|fifth|five)\b"),
    ]
    for owner_count, pattern in patterns:
        if re.search(pattern, normalized):
            return ParseResult(
                raw_value=value,
                normalized_value=owner_count,
                confidence=0.94,
            )

    return _fail(value, "ambiguous_ownership_text")


def parse_fuel_type(value: Any) -> ParseResult:
    """Parse fuel text into the canonical fuel vocabulary."""

    text = normalize_null(value)
    if text is None:
        return _fail(value, "missing_fuel_type")

    normalized = _normalize_search_text(text)
    padded = f" {normalized} "
    matches: list[str] = []
    for canonical, synonyms in FUEL_SYNONYMS.items():
        for synonym in synonyms:
            synonym_norm = _normalize_search_text(synonym)
            if f" {synonym_norm} " in padded:
                matches.append(canonical)
                break

    matches = list(dict.fromkeys(matches))
    if "petrol" in matches and "cng" in matches:
        matches = ["petrol_cng"]
    if "petrol" in matches and "lpg" in matches:
        matches = ["petrol_lpg"]

    if not matches:
        return ParseResult(
            raw_value=value,
            normalized_value="unknown",
            confidence=0.2,
            warnings=["unknown_fuel_type"],
            failure_reason="unknown_fuel_type",
        )

    warnings = ["multiple_fuel_candidates"] if len(matches) > 1 else []
    return ParseResult(
        raw_value=value,
        normalized_value=matches[0],
        confidence=0.96 if not warnings else 0.78,
        warnings=warnings,
    )


def parse_transmission(value: Any) -> ParseResult:
    """Parse transmission text into the canonical transmission vocabulary."""

    text = normalize_null(value)
    if text is None:
        return _fail(value, "missing_transmission")

    normalized = _normalize_search_text(text)
    tokens = set(normalized.split())
    matches: list[str] = []

    for canonical, synonyms in TRANSMISSION_SYNONYMS.items():
        for synonym in synonyms:
            synonym_norm = _normalize_search_text(synonym)
            if " " in synonym_norm:
                matched = synonym_norm in normalized
            else:
                matched = synonym_norm in tokens
            if matched:
                matches.append(canonical)
                break

    matches = list(dict.fromkeys(matches))
    if not matches:
        return ParseResult(
            raw_value=value,
            normalized_value="unknown",
            confidence=0.2,
            warnings=["unknown_transmission"],
            failure_reason="unknown_transmission",
        )

    warnings = ["multiple_transmission_candidates"] if len(matches) > 1 else []
    return ParseResult(
        raw_value=value,
        normalized_value=matches[0],
        confidence=0.96 if not warnings else 0.78,
        warnings=warnings,
    )


def parse_registration(value: Any) -> ParseResult:
    """Parse Indian registration code and state from source text."""

    text = normalize_null(value)
    empty_result = {
        "registration_code": None,
        "registration_state": None,
        "registration_type": None,
        "registration_year": None,
    }
    if text is None:
        return ParseResult(
            raw_value=value,
            normalized_value=empty_result,
            confidence=0.0,
            warnings=["missing_registration"],
            failure_reason="missing_registration",
        )

    upper_text = re.sub(r"[^A-Za-z0-9 ]+", " ", str(text).upper())
    upper_text = re.sub(r"\s+", " ", upper_text).strip()

    if upper_text in RTO_LOCATION_ALIASES:
        return ParseResult(
            raw_value=value,
            normalized_value={
                **RTO_LOCATION_ALIASES[upper_text],
                "registration_type": "state_rto",
                "registration_year": None,
            },
            confidence=0.92,
            warnings=["rto_location_alias"],
        )

    bh_match = re.search(r"\b(\d{2})\s*BH\b", upper_text)
    if bh_match:
        return ParseResult(
            raw_value=value,
            normalized_value={
                "registration_code": "BH",
                "registration_state": None,
                "registration_type": "bharat_series",
                "registration_year": 2000 + int(bh_match.group(1)),
            },
            confidence=0.9,
            warnings=["bharat_series_registration"],
        )

    for match in re.finditer(r"\b([A-Z]{2})\s*-?\s*(\d{1,2})?", upper_text):
        prefix = match.group(1)
        district = match.group(2)
        if prefix in LEGACY_STATE_PREFIX_ALIASES:
            alias = LEGACY_STATE_PREFIX_ALIASES[prefix]
            canonical_prefix = alias["canonical_prefix"]
            code = f"{canonical_prefix}{int(district):02d}" if district is not None else None
            warnings = ["legacy_registration_prefix"] if code else [
                "legacy_registration_prefix",
                "registration_state_only",
            ]
            return ParseResult(
                raw_value=value,
                normalized_value={
                    "registration_code": code,
                    "registration_state": alias["registration_state"],
                    "registration_type": "state_rto",
                    "registration_year": None,
                },
                confidence=0.92 if code else 0.72,
                warnings=warnings,
            )
        if prefix not in STATE_PREFIXES:
            continue
        code = f"{prefix}{int(district):02d}" if district is not None else None
        warnings = [] if code else ["registration_state_only"]
        return ParseResult(
            raw_value=value,
            normalized_value={
                "registration_code": code,
                "registration_state": STATE_PREFIXES[prefix],
                "registration_type": "state_rto",
                "registration_year": None,
            },
            confidence=0.95 if code else 0.75,
            warnings=warnings,
        )

    lower_text = str(text).lower()
    for state in sorted(set(STATE_PREFIXES.values()), key=len, reverse=True):
        if state.lower() in lower_text:
            return ParseResult(
                raw_value=value,
                normalized_value={
                    "registration_code": None,
                    "registration_state": state,
                    "registration_type": "state_rto",
                    "registration_year": None,
                },
                confidence=0.7,
                warnings=["registration_state_only"],
            )

    return ParseResult(
        raw_value=value,
        normalized_value=empty_result,
        confidence=0.2,
        warnings=["unknown_registration_prefix"],
        failure_reason="unknown_registration_prefix",
    )


def parse_title(value: Any) -> ParseResult:
    """Parse listing title into model year, brand, model, and variant."""

    text = normalize_null(value)
    if text is None:
        return _fail(value, "missing_title")

    model_year_min = 1990
    model_year_max = date.today().year + 1
    warnings: list[str] = []
    working = re.sub(r"\s+", " ", text).strip()

    year_matches = [
        int(match.group(0))
        for match in re.finditer(r"\b(19\d{2}|20\d{2})\b", working)
        if model_year_min <= int(match.group(0)) <= model_year_max
    ]
    model_year = year_matches[0] if year_matches else None
    if len(year_matches) > 1:
        warnings.append("multiple_year_candidates")
    if model_year is None:
        warnings.append("missing_model_year")
    else:
        working = re.sub(rf"\b{model_year}\b", " ", working, count=1)

    brand, working = _match_brand(working)

    if brand is None:
        warnings.append("unknown_brand")

    remaining = re.sub(r"\s+", " ", working).strip(" -|/")
    model, variant = _match_model(brand, remaining)
    if model is None:
        parts = remaining.split()
        model = parts[0] if parts else None
        variant = _normalize_variant_text(" ".join(parts[1:])) if len(parts) > 1 else None

    if model is None:
        warnings.append("unknown_model")
    elif variant is not None:
        warnings.append("variant_inferred")

    confidence = 0.95
    if model_year is None:
        confidence -= 0.2
    if brand is None:
        confidence -= 0.25
    if model is None:
        confidence -= 0.25
    if "variant_inferred" in warnings:
        confidence -= 0.05
    confidence = max(confidence, 0.0)

    critical = {"missing_title", "missing_model_year", "unknown_brand", "unknown_model"}
    failure_reason = next((warning for warning in warnings if warning in critical), None)

    return ParseResult(
        raw_value=value,
        normalized_value={
            "model_year": model_year,
            "brand": brand,
            "model": model,
            "variant": variant,
        },
        confidence=round(confidence, 2),
        warnings=warnings,
        failure_reason=failure_reason,
    )
