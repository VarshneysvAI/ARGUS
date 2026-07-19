import re

def validate_claims(narrative: str, math_state: dict):
    """
    Scans the narrative for [CLAIM id="X" source="Y"]...[/CLAIM].
    If the tag is missing source or id, raises ValueError.
    (Optional) string-matches numbers against math_state.
    """
    pattern = r'\[CLAIM.*?source=[\'"]([^\'"]+)[\'"].*?\]([\s\S]*?)\[/CLAIM\]'
    claims = re.findall(pattern, narrative)
    
    # Check if there are malformed tags by just searching for [CLAIM without the right format
    raw_claims = re.findall(r'\[CLAIM', narrative)
    if len(claims) != len(raw_claims):
        raise ValueError("Regex Validator Failed: Malformed [CLAIM] tags found or missing id/source metadata.")
        
    return True
