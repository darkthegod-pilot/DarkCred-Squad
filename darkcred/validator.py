import re

from darkcred.config import FORBIDDEN_EXACT, FORBIDDEN_PATTERNS

MAX_COPY_LENGTH = 500


class ComplianceViolation:
    def __init__(self, variation_index: int, reasons: list[str]):
        self.variation_index = variation_index
        self.reasons = reasons

    def __str__(self) -> str:
        reasons_str = "; ".join(self.reasons)
        return f"Variação {self.variation_index + 1}: {reasons_str}"


def validate_variation(variation: dict) -> list[str]:
    full_text = variation.get("full_copy", "").lower()
    violations = []

    for term in FORBIDDEN_EXACT:
        if term.lower() in full_text:
            violations.append(f"Termo proibido: '{term}'")

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE):
            violations.append(f"Padrão proibido detectado: {pattern}")

    copy_len = len(variation.get("full_copy", ""))
    if copy_len > MAX_COPY_LENGTH:
        violations.append(f"Copy muito longa: {copy_len} caracteres (máx {MAX_COPY_LENGTH})")

    return violations


def validate_all(
    variations: list[dict],
) -> tuple[list[dict], list[ComplianceViolation]]:
    compliant = []
    violations = []

    for i, var in enumerate(variations):
        reasons = validate_variation(var)
        if reasons:
            violations.append(ComplianceViolation(i, reasons))
        else:
            compliant.append(var)

    return compliant, violations
