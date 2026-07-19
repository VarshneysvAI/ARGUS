import math
from typing import List, Dict, Any

class ArgusEngine:
    @staticmethod
    def calculate_cost_delta(v_lost: float, p_spot: float, p_contract: float, 
                           m_freight: float, delta_grade: float, d_congestion: float, 
                           fx: float = 86.0) -> Dict[str, float]:
        """
        C_Δ = V_lost × (P_spot − P_contract + M_freight + δ_grade) + D_congestion
        """
        c_delta_usd_day = v_lost * 1_000_000 * (p_spot - p_contract + m_freight + delta_grade) + d_congestion
        c_delta_inr_crore_day = c_delta_usd_day * fx / 10_000_000
        
        return {
            "c_delta_usd_day": round(c_delta_usd_day, 2),
            "c_delta_inr_crore_day": round(c_delta_inr_crore_day, 2)
        }

    @staticmethod
    def apply_sanctions_filter(candidates: List[Dict], sanctions_data: Dict) -> List[Dict]:
        """
        Marks candidates as 'COMPLIANCE-BLOCKED' if they match sanctions list.
        """
        sanctioned_suppliers = set(sanctions_data.get("sanctioned_suppliers", []))
        sanctioned_flags = set(sanctions_data.get("sanctioned_flag_states", []))
        
        for candidate in candidates:
            candidate['compliance_status'] = "CLEAR"
            if candidate['supplier'] in sanctioned_suppliers or candidate['flag_state'] in sanctioned_flags:
                candidate['compliance_status'] = "COMPLIANCE-BLOCKED"
        return candidates

    @staticmethod
    def heuristic_ranking(candidates: List[Dict]) -> List[Dict]:
        """
        TOPSIS MCDA Ranking. Candidates should already be filtered/marked.
        Only ranks 'CLEAR' candidates.
        Criteria: landed_cost, lead_time (both lower is better for this basic implementation).
        We'll use a simplified ranking for the demo.
        """
        valid = [c for c in candidates if c.get('compliance_status') == "CLEAR"]
        if not valid:
            return []
            
        # Simplified: just sort by a proxy score (e.g. landed cost + lead time penalty)
        for v in valid:
            # A heuristic score for demonstration 
            # In a real scenario, this would apply the full MCDA math.
            score = 1.0 / (v['landed_cost_usd_bbl'] * 0.7 + v['lead_time_days'] * 0.3)
            v['heuristic_score'] = round(score * 100, 2)
            
        valid.sort(key=lambda x: x['heuristic_score'], reverse=True)
        
        for i, v in enumerate(valid):
            v['rank'] = i + 1
            v['action_window'] = "executable within 6h"
            
        # Return all (including blocked, so UI can show them)
        blocked = [c for c in candidates if c.get('compliance_status') == "COMPLIANCE-BLOCKED"]
        for b in blocked:
            b['rank'] = 999
            
        return valid + blocked

    @staticmethod
    def optimize_spr(volume_lost_mbd: float, duration_days: int) -> Dict[str, Any]:
        """
        SPR Drawdown Optimizer.
        Anchor: 9.5 days of national consumption. (India total consumption approx 5 mbd -> S_0 = 47.5 mb)
        S_min = 20% of S_0 = 9.5 mb
        """
        daily_consumption = 5.0 # mbd, assumed
        s_0 = 9.5 * daily_consumption
        s_min = 0.20 * s_0
        
        # S1: Max immediate (draw at full gap until floor)
        s1_days_full_coverage = int((s_0 - s_min) / volume_lost_mbd) if volume_lost_mbd > 0 else duration_days
        s1_days_full_coverage = min(duration_days, s1_days_full_coverage)
        
        # S2: Phased (draw at 0.5g)
        s2_days_partial_coverage = int((s_0 - s_min) / (0.5 * volume_lost_mbd)) if volume_lost_mbd > 0 else duration_days
        s2_days_partial_coverage = min(duration_days, s2_days_partial_coverage)
        
        # Generate curve arrays (x=day, y=remaining_volume)
        s1_curve = []
        s2_curve = []
        for day in range(duration_days + 1):
            # S1 logic
            if day <= s1_days_full_coverage:
                y1 = s_0 - (volume_lost_mbd * day)
            else:
                y1 = s_min
            s1_curve.append({"day": day, "stock": max(s_min, round(y1, 2))})
            
            # S2 logic
            if day <= s2_days_partial_coverage:
                y2 = s_0 - (0.5 * volume_lost_mbd * day)
            else:
                y2 = s_min
            s2_curve.append({"day": day, "stock": max(s_min, round(y2, 2))})
            
        return {
            "recommended_strategy": "S2" if s2_days_partial_coverage > s1_days_full_coverage else "S1",
            "coverage_days": round(s2_days_partial_coverage if s2_days_partial_coverage > s1_days_full_coverage else s1_days_full_coverage),
            "s_0": s_0,
            "s_min": s_min,
            "s1_curve": s1_curve,
            "s2_curve": s2_curve
        }

    @staticmethod
    def economic_cascade(pump_delta: float, duration_days: int) -> Dict[str, Any]:
        """
        Pump price: Delta P * 0.55/litre
        Power sector: ELEVATED if premium > 15% (mocked based on pump_delta)
        GDP: Delta P * 1.2 bps * (duration/90)
        """
        pump_price_impact = pump_delta * 0.55
        power_stress = "ELEVATED" if pump_delta > 10 else "NORMAL"
        gdp_impact = pump_delta * 1.2 * (duration_days / 90.0)
        
        return {
            "pump_price_impact_inr": round(pump_price_impact, 2),
            "power_sector_stress": power_stress,
            "gdp_impact_bps": round(-gdp_impact, 2) # negative impact
        }
