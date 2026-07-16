"""Source adapters for turning extracted source records into canonical listings."""

from used_car_price_intelligence.adapters.common import (
    AdapterRunContext,
    PayloadContractFailure,
    PayloadContractResult,
)
from used_car_price_intelligence.adapters.mahindra_first_choice import (
    MahindraFirstChoiceExtractedPayloadAdapter,
    MahindraFirstChoiceFixtureAdapter,
    parse_mfc_variant_details,
    validate_mahindra_first_choice_extracted_payload,
)
from used_car_price_intelligence.adapters.spinny import (
    SpinnyExtractedPayloadAdapter,
    SpinnyFixtureAdapter,
    validate_spinny_extracted_payload,
)
from used_car_price_intelligence.adapters.true_value import (
    TrueValueExtractedPayloadAdapter,
    TrueValueFixtureAdapter,
    validate_true_value_extracted_payload,
)

__all__ = [
    "AdapterRunContext",
    "MahindraFirstChoiceExtractedPayloadAdapter",
    "MahindraFirstChoiceFixtureAdapter",
    "PayloadContractFailure",
    "PayloadContractResult",
    "parse_mfc_variant_details",
    "SpinnyExtractedPayloadAdapter",
    "SpinnyFixtureAdapter",
    "TrueValueExtractedPayloadAdapter",
    "TrueValueFixtureAdapter",
    "validate_mahindra_first_choice_extracted_payload",
    "validate_spinny_extracted_payload",
    "validate_true_value_extracted_payload",
]
