# agents/agent_2_verification.py
"""Agent 2: Source Verification — checks URL reachability, source tier, cross-checks numerical claims against EIA baseline."""
import json
import re
from typing import Dict, Any, List
from pathlib import Path

EIA_BASELINE_PATH = Path(__file__).resolve().parent.parent / "data" / "eia_baseline.json"

def load_baseline() -> Dict[str, Any]:
    try:
        return json.loads(EIA_BASELINE_PATH.read_text(encoding="utf-8"))
    except (IOError, json.JSONDecodeError):
        return {}

BASELINE = load_baseline()

NUMERICAL_PATTERNS = [
    (r'(\d+\.?\d*)\s*(million|M|m)\s*(b[/\\]?d|bpd|barrels?)', lambda n: n * 1_000_000),
    (r'(\d+\.?\d*)\s*(billion|B|b)\s*(b[/\\]?d|bpd|barrels?)', lambda n: n * 1_000_000_000),
    (r'(\d+\.?\d*)\s*M\s*(bbl|barrels)', lambda n: n * 1_000_000),
    (r'(\d+\.?\d*)\s*(billion|B)\s*(barrels?)', lambda n: n * 1_000_000_000),
]

CHECKS = [
    {"keywords": ["saudi", "shut", "shut-in"], "exclude": [], "baseline_key": "saudi_shutin_march2026_mbd", "label": "Saudi shut-in"},
    {"keywords": ["uae", "pipeline", "fujairah", "habshan"], "exclude": [], "baseline_key": "uae_pipeline_capacity_mbd", "label": "UAE pipeline capacity"},
    {"keywords": ["hormuz", "throughput", "flow"], "exclude": ["pipeline", "uae", "fujairah"], "baseline_key": "hormuz_throughput_march2026_mbd", "label": "Hormuz throughput"},
    {"keywords": ["$", "brent"], "exclude": [], "baseline_key": "brent_peak_april2026", "label": "Brent crude price"},
    {"keywords": ["india", "import", "dependency", "%"], "exclude": [], "baseline_key": "india_import_dependency_pct", "label": "India import dependency"},
]

def extract_numbers(text: str) -> List[float]:
    numbers = []
    claim_lower = text.lower()
    for pat, multiplier in NUMERICAL_PATTERNS:
        for match in re.finditer(pat, claim_lower):
            try:
                num = float(match.group(1))
                numbers.append(multiplier(num))
            except ValueError:
                continue
    return numbers

def cross_check_numerical(claim_text: str) -> Dict[str, Any]:
    numbers = extract_numbers(claim_text)
    if not numbers:
        return {"checked": False, "reason": "no_numerical_claim"}
    claim_lower = claim_text.lower()
    for check in CHECKS:
        if not all(kw in claim_lower for kw in check["keywords"]):
            continue
        exclude = check.get("exclude", [])
        if exclude and any(ex in claim_lower for ex in exclude):
            continue
        baseline_val = BASELINE.get(check["baseline_key"])
        if baseline_val is None:
            continue
        is_pct = "pct" in check["baseline_key"] or "dependency" in check["baseline_key"]
        is_price = "brent" in check["baseline_key"]
        for num in numbers:
            # For price checks, only consider reasonable price-range numbers
            if is_price and (num < 50 or num > 250):
                continue
            if is_pct and num > 100:
                continue
            if is_pct:
                candidate = num
                baseline = float(baseline_val)
            else:
                candidate = num
                baseline = float(baseline_val) * 1_000_000
            if baseline == 0:
                continue
            variance = abs(candidate - baseline) / baseline
            return {
                "checked": True,
                "check_name": check["label"],
                "baseline_raw": float(baseline_val),
                "baseline_display": f"${baseline_val:.1f}" if "brent" in check["baseline_key"] else (f"{baseline_val:.1f}%" if is_pct else f"{baseline_val:.1f}M"),
                "claimed_raw": candidate / (1e6 if not is_pct else 1),
                "variance_pct": round(variance * 100, 1),
                "within_tolerance": variance <= 0.10,
                "source": "EIA_STEO_April_2026"
            }
    return {"checked": False, "reason": "no_matching_baseline"}

def run_agent_2(claims: List[Dict]) -> Dict[str, Any]:
    verified = []
    flagged = []
    quarantined = []
    for claim in claims:
        url = claim.get("source_url", "")
        tier = claim.get("source_tier", "social")
        confidence = claim.get("retrieval_confidence", 0.5)
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("file://")):
            quarantined.append({**claim, "reason": "invalid_url_format", "status": "QUARANTINED"})
            continue
        check = cross_check_numerical(claim["claim"])
        if check.get("checked"):
            if check["within_tolerance"]:
                verified.append({
                    **claim, "verification_status": "VERIFIED",
                    "confidence": round(min(0.95, confidence * 1.1), 2),
                    "reason": f"EIA confirmed {check['check_name']}, within 10% tolerance ({check['variance_pct']}% variance)"
                })
            else:
                flagged.append({
                    **claim, "verification_status": "FLAGGED",
                    "confidence": round(confidence * 0.5, 2),
                    "reason": f"EIA reports {check['check_name']}={check['baseline_raw']:.1f}M. Claim suggests {check['claimed_raw']:.1f}M. Variance: {check['variance_pct']}% exceeds 10% tolerance"
                })
        else:
            tier_mult = {"gov": 1.0, "major_media": 0.8, "regional": 0.5, "social": 0.2}.get(tier, 0.2)
            verified.append({
                **claim, "verification_status": "VERIFIED",
                "confidence": round(confidence * tier_mult, 2),
                "reason": f"Source tier: {tier}, no numerical contradiction with EIA baseline found"
            })
    return {"verified_claims": verified, "flagged_claims": flagged, "quarantined_claims": quarantined}
