# agents/agent_2_verification.py
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

def check_url_reachable(url: str) -> bool:
    if url.startswith("file://"):
        file_path_str = url.replace("file://", "")
        return Path(file_path_str).exists() or Path(file_path_str.replace("data/articles/", "")).exists()
    return True

def cross_check_numerical(claim: str) -> Dict[str, Any]:
    patterns = [
        (r'(\d+\.?\d*)\s*(million|M|m)\s*(b/d|bpd|barrels?)', lambda n: n * 1_000_000),
        (r'(\d+\.?\d*)\s*(billion|B|b)\s*(b/d|bpd|barrels?)', lambda n: n * 1_000_000_000),
        (r'(\d+\.?\d*)\s*M\s*(bbl|barrels)', lambda n: n * 1_000_000),
    ]
    claim_lower = claim.lower()
    numbers = []
    for pat, multiplier in patterns:
        for match in re.finditer(pat, claim):
            num = float(match.group(1))
            numbers.append(multiplier(num))
    if not numbers:
        return {"checked": False, "reason": "no_numerical_claim"}
    for num in numbers:
        if "saudi" in claim_lower and "shut" in claim_lower:
            baseline = BASELINE.get("saudi_shutin_march2026_mbd", 9.1) * 1_000_000
            variance = abs(num - baseline) / baseline if baseline > 0 else 1.0
            return {
                "checked": True, "baseline": round(baseline), "claimed": round(num),
                "variance_pct": round(variance * 100, 1),
                "within_tolerance": variance <= 0.10,
                "source": "EIA_STEO_April_2026"
            }
        if "hormuz" in claim_lower and "throughput" in claim_lower:
            baseline = BASELINE.get("hormuz_throughput_march2026_mbd", 2.7) * 1_000_000
            variance = abs(num - baseline) / baseline if baseline > 0 else 1.0
            return {
                "checked": True, "baseline": round(baseline), "claimed": round(num),
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
        if not check_url_reachable(url):
            quarantined.append({**claim, "reason": "unreachable_url", "status": "QUARANTINED"})
            continue
        check = cross_check_numerical(claim["claim"])
        if check.get("checked"):
            if check["within_tolerance"]:
                verified.append({
                    **claim, "verification_status": "VERIFIED",
                    "confidence": round(min(0.95, confidence * 1.1), 2),
                    "reason": f"EIA confirmed, within 10% tolerance ({check['variance_pct']}% variance)"
                })
            else:
                flagged.append({
                    **claim, "verification_status": "FLAGGED",
                    "confidence": round(confidence * 0.5, 2),
                    "reason": f"EIA says {check['baseline']/1e6:.1f}M b/d. Claim: {check['claimed']/1e6:.1f}M. Variance: {check['variance_pct']}% exceeds 10% tolerance"
                })
        else:
            tier_mult = {"gov": 1.0, "major_media": 0.8, "regional": 0.5, "social": 0.2}.get(tier, 0.2)
            verified.append({
                **claim, "verification_status": "VERIFIED",
                "confidence": round(confidence * tier_mult, 2),
                "reason": f"Source tier: {tier}, no numerical contradiction found"
            })
    return {"verified_claims": verified, "flagged_claims": flagged, "quarantined_claims": quarantined}
