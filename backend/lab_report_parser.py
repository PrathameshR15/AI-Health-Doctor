import re
from typing import List, Dict, Any, Optional, Tuple


# Comprehensive clinical reference catalog for fallback range/flag evaluation and descriptions
# Tuple: (regex_pattern, canonical_name, default_ref_range, default_unit, low_threshold, high_threshold, clinical_description)
CLINICAL_REFERENCE_CATALOG: List[Tuple[str, str, str, str, Optional[float], Optional[float], str]] = [
    # --- Lipid Profile ---
    (r"\btotal\s*cholesterol\b|\bcholesterol[,\s]*total\b", "Total Cholesterol", "< 200 mg/dL", "mg/dL", None, 200.0, "Total circulating cholesterol; elevated levels increase atherosclerotic cardiovascular risk"),
    (r"\bnon[-\s]*hdl\s*cholesterol\b", "Non-HDL Cholesterol", "< 130 mg/dL", "mg/dL", None, 130.0, "Sum of all atherogenic lipoproteins (LDL, VLDL, IDL)"),
    (r"\bldl\s*cholesterol\b|\bldl[-\s]*c\b|\blow\s*density\s*lipoprotein\b", "LDL Cholesterol", "< 100 mg/dL", "mg/dL", None, 100.0, "Low-density lipoprotein ('bad' cholesterol) contributing to arterial plaque"),
    (r"\bhdl\s*cholesterol\b|\bhdl[-\s]*c\b|\bhigh\s*density\s*lipoprotein\b", "HDL Cholesterol", "> 40 mg/dL", "mg/dL", 40.0, None, "High-density lipoprotein ('good' cholesterol) protective against cardiovascular disease"),
    (r"\bvldl\s*cholesterol\b|\bvldl[-\s]*c\b", "VLDL Cholesterol", "5 - 30 mg/dL", "mg/dL", 5.0, 30.0, "Very-low-density lipoprotein carrying triglycerides"),
    (r"\btriglycerides?\b|\btg\b", "Triglycerides", "< 150 mg/dL", "mg/dL", None, 150.0, "Circulating blood fats; elevated levels increase cardiometabolic and pancreatitis risk"),
    (r"\btotal\s*/?\s*hdl\s*(?:cholesterol\s*)?ratio\b|\bchol\s*/\s*hdl\b", "Total / HDL Cholesterol Ratio", "< 4.5", "ratio", None, 4.5, "Ratio of total cholesterol to protective HDL cholesterol"),
    (r"\bldl\s*/\s*hdl\s*ratio\b", "LDL / HDL Ratio", "< 3.0", "ratio", None, 3.0, "Ratio of atherogenic LDL to protective HDL cholesterol"),

    # --- Cardiac Risk Markers ---
    (r"\bhs[-\s]*crp\b|\bhigh\s*sensitivity\s*c[-\s]*reactive\s*protein\b", "hs-CRP", "< 3.0 mg/L", "mg/L", None, 3.0, "High-sensitivity C-reactive protein assessing vascular inflammation and cardiac risk"),
    (r"\bcrp\b|\bc[-\s]*reactive\s*protein\b", "C-Reactive Protein (CRP)", "< 5.0 mg/L", "mg/L", None, 5.0, "Systemic inflammatory marker"),
    (r"\blipoprotein\s*\(?a\)?\b|\blp\s*\(?a\)?\b", "Lipoprotein (a)", "< 30 mg/dL", "mg/dL", None, 30.0, "Genetically determined atherogenic lipoprotein associated with coronary risk"),
    (r"\bapolipoprotein\s*b\b|\bapo\s*b\b", "Apolipoprotein B (ApoB)", "< 100 mg/dL", "mg/dL", None, 100.0, "Primary protein component of atherogenic lipid particles"),
    (r"\bapolipoprotein\s*a1\b|\bapo\s*a1\b", "Apolipoprotein A1 (ApoA1)", "> 120 mg/dL", "mg/dL", 120.0, None, "Primary protein component of protective HDL particles"),
    (r"\bhomocysteine\b", "Homocysteine", "5 - 15 umol/L", "umol/L", 5.0, 15.0, "Amino acid linked to endothelial dysfunction and cardiovascular risk when elevated"),
    (r"\btroponin\b|\bhs[-\s]*ctn[it]\b", "Cardiac Troponin", "< 0.04 ng/mL", "ng/mL", None, 0.04, "Myocardial injury biomarker"),
    (r"\bnt[-\s]*probnp\b|\bbnp\b", "NT-proBNP / BNP", "< 125 pg/mL", "pg/mL", None, 125.0, "Natriuretic peptide assessing cardiac wall stress and heart failure risk"),
    (r"\bck[-\s]*mb\b", "CK-MB", "< 5.0 ng/mL", "ng/mL", None, 5.0, "Cardiac muscle isoenzyme marker"),

    # --- Iron Studies & Vitamins ---
    (r"\bserum\s*iron\b|\biron[,\s]*serum\b|\biron\b(?!\s*binding)", "Serum Iron", "60 - 170 ug/dL", "ug/dL", 60.0, 170.0, "Circulating iron bound to transferrin for hemoglobin synthesis"),
    (r"\bferritin\b", "Serum Ferritin", "30 - 300 ng/mL", "ng/mL", 30.0, 300.0, "Primary intracellular iron storage protein; low levels indicate iron depletion"),
    (r"\btibc\b|\btotal\s*iron\s*binding\s*capacity\b", "TIBC", "240 - 450 ug/dL", "ug/dL", 240.0, 450.0, "Total iron-binding capacity; typically elevated in iron deficiency"),
    (r"\buibc\b|\bunsaturated\s*iron\s*binding\b", "UIBC", "110 - 370 ug/dL", "ug/dL", 110.0, 370.0, "Unsaturated iron-binding capacity"),
    (r"\btransferrin\s*saturation\b|\btsat\b", "Transferrin Saturation", "20 - 50 %", "%", 20.0, 50.0, "Percentage of transferrin iron-binding sites occupied by iron"),
    (r"\bvitamin\s*d\b|\b25[-\s]*oh\s*vitamin\s*d\b|\b25[-\s]*hydroxy\b", "Vitamin D (25-OH)", "30 - 100 ng/mL", "ng/mL", 30.0, 100.0, "Fat-soluble vitamin essential for bone mineralization, immunity, and muscle health"),
    (r"\bvitamin\s*b12\b|\bcyanocobalamin\b|\bcobalamin\b", "Vitamin B12", "200 - 900 pg/mL", "pg/mL", 200.0, 900.0, "Essential vitamin for red blood cell maturation and neurologic function"),
    (r"\bfolate\b|\bfolic\s*acid\b", "Folate (Vitamin B9)", "> 4.0 ng/mL", "ng/mL", 4.0, None, "B-vitamin essential for DNA synthesis and red blood cell production"),

    # --- Complete Blood Count (CBC) ---
    (r"\bhemoglobin\b|\bhgb\b", "Hemoglobin", "12.0 - 16.0 g/dL", "g/dL", 12.0, 16.0, "Oxygen-carrying protein in red blood cells"),
    (r"\bwbc\b|\bwhite\s*blood\s*cells?\b|\bleukocytes?\b|\btotal\s*leucocyte\b", "WBC Count", "4,000 - 11,000 /mcL", "/mcL", 4000.0, 11000.0, "Infection and immune defense cells"),
    (r"\brbc\b|\bred\s*blood\s*cells?\b", "RBC Count", "4.2 - 5.9 million/mcL", "million/mcL", 4.2, 5.9, "Red blood cell count"),
    (r"\bplatelets?\b|\bplatelet\s*count\b", "Platelet Count", "150,000 - 450,000 /mcL", "/mcL", 150000.0, 450000.0, "Clotting cells critical for hemostasis"),
    (r"\bhematocrit\b|\bhct\b|\bpcv\b", "Hematocrit (PCV)", "36 - 50 %", "%", 36.0, 50.0, "Proportion of red blood cells in blood"),
    (r"\bmcv\b", "MCV", "80 - 100 fL", "fL", 80.0, 100.0, "Mean corpuscular volume (red cell size)"),
    (r"\bmch\b(?!c)", "MCH", "27 - 33 pg", "pg", 27.0, 33.0, "Mean corpuscular hemoglobin"),
    (r"\bmchc\b", "MCHC", "32 - 36 g/dL", "g/dL", 32.0, 36.0, "Mean corpuscular hemoglobin concentration"),
    (r"\besr\b", "ESR", "0 - 20 mm/hr", "mm/hr", 0.0, 20.0, "Non-specific inflammation marker"),

    # --- Glycemic / Metabolic / Renal / Hepatic / Thyroid ---
    (r"\bfasting\s*blood\s*(?:sugar|glucose)\b|\bfbs\b|\bglucose[,\s]*fasting\b", "Blood Glucose (Fasting)", "70 - 99 mg/dL", "mg/dL", 70.0, 99.0, "Fasting blood sugar marker"),
    (r"\bhba1c\b|\bglycated\s*hemoglobin\b", "HbA1c", "< 5.7 %", "%", None, 5.7, "3-month average blood glucose control marker"),
    (r"\bcreatinine\b", "Serum Creatinine", "0.6 - 1.2 mg/dL", "mg/dL", 0.6, 1.2, "Kidney filtration efficiency marker"),
    (r"\begfr\b", "eGFR", "> 90 mL/min", "mL/min", 90.0, None, "Estimated glomerular filtration rate"),
    (r"\bbun\b|\bblood\s*urea\s*nitrogen\b|\burea\b", "BUN / Urea", "7 - 20 mg/dL", "mg/dL", 7.0, 20.0, "Nitrogenous waste cleared by kidneys"),
    (r"\buric\s*acid\b", "Uric Acid", "3.5 - 7.2 mg/dL", "mg/dL", 3.5, 7.2, "Purine metabolism byproduct"),
    (r"\bsgpt\b|\balt\b", "ALT / SGPT", "7 - 56 U/L", "U/L", 7.0, 56.0, "Liver cellular enzyme"),
    (r"\bsgot\b|\bast\b", "AST / SGOT", "10 - 40 U/L", "U/L", 10.0, 40.0, "Hepatic/muscular enzyme"),
    (r"\bbilirubin\b", "Total Bilirubin", "0.1 - 1.2 mg/dL", "mg/dL", 0.1, 1.2, "Bile pigment processed by liver"),
    (r"\btsh\b|\bthyroid\s*stimulating\s*hormone\b", "TSH", "0.4 - 4.0 mIU/L", "mIU/L", 0.4, 4.0, "Pituitary thyroid regulatory hormone"),
    (r"\bfree\s*t4\b|\bft4\b", "Free T4", "0.8 - 1.8 ng/dL", "ng/dL", 0.8, 1.8, "Active circulating thyroxine hormone"),
    (r"\bfree\s*t3\b|\bft3\b", "Free T3", "2.3 - 4.2 pg/mL", "pg/mL", 2.3, 4.2, "Active triiodothyronine hormone"),
]

# Recognized units (order longest first for greedy matching)
UNIT_PATTERN = (
    r"(?:10\^\d+/[a-zA-Z]+|million/[a-zA-Z]+|cells/[a-zA-Z]+|"
    r"mL/min/1\.73m2|mL/min|mg/dL|g/dL|ug/dL|mcg/dL|ng/dL|ng/mL|pg/mL|"
    r"mIU/L|uIU/mL|µIU/mL|U/L|IU/L|mg/L|g/L|umol/L|µmol/L|mmol/L|mEq/L|"
    r"mm/hr|/[a-zA-Z]+|fL|pg|%|ratio|sec|s)"
)

SECTION_KEYWORDS = [
    "lipid profile", "lipid panel", "cardiac risk", "cardiac markers", "cardiovascular",
    "iron studies", "iron profile", "iron & vitamin", "iron and vitamin", "vitamins",
    "vitamin profile", "complete blood count", "cbc", "hemogram", "hematology",
    "liver function", "lft", "kidney function", "kft", "renal panel", "thyroid",
    "diabetes", "glycemic", "metabolic panel", "electrolytes", "biochemistry",
    "inflammatory markers", "urinalysis", "hormone"
]

IGNORE_LINE_PATTERNS = [
    r"^\s*page\s+\d+",
    r"^\s*(?:patient\s*name|name|age|gender|sex|dob|date\s*of\s*birth|patient\s*id|mrn|uhid|lab\s*no|sample\s*id|accession)\s*[:\-]",
    r"^\s*(?:collected|received|reported|printed|registered|referred\s*by|physician|doctor|lab\s*director)\s*[:\-]",
    r"^\s*(?:test\s*name|parameter|investigation|analyte)\s+(?:result|value|observed)",
    r"^\s*(?:specimen|sample\s*type|method|methodology|instrument|note|comment|interpretation|end\s*of\s*report)\s*[:\-]",
    r"^\s*[\*\-=_]{4,}\s*$",
]

FLAG_MAP = {
    "h": "High",
    "high": "High",
    "elevated": "High",
    "above": "High",
    "↑": "High",
    "l": "Low",
    "low": "Low",
    "decreased": "Low",
    "deficient": "Low",
    "deficiency": "Low",
    "insufficient": "Low",
    "below": "Low",
    "↓": "Low",
    "abnormal": "Abnormal",
    "critical": "Abnormal",
    "borderline": "Abnormal",
    "reactive": "Abnormal",
    "positive": "Abnormal",
    "pos": "Abnormal",
    "*": "Abnormal",
    "n": "Normal",
    "normal": "Normal",
    "optimal": "Normal",
    "desirable": "Normal",
    "negative": "Normal",
    "neg": "Normal",
}


def _normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("µ", "u").replace("μ", "u")
    return text


def _parse_numeric(val_str: str) -> Optional[float]:
    if not val_str:
        return None
    cleaned = val_str.strip().lstrip("<>=").replace(",", "").strip()
    m = re.match(r"^[-+]?\d*\.?\d+$", cleaned)
    if m:
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _evaluate_flag_against_range(val_num: Optional[float], ref_str: str) -> Optional[str]:
    if val_num is None or not ref_str:
        return None
    ref_clean = ref_str.replace(",", "").strip()

    # Range: low - high (e.g., "30.0 - 100.0" or "13.5-17.5")
    m_range = re.search(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)", ref_clean, re.IGNORECASE)
    if m_range:
        low = float(m_range.group(1))
        high = float(m_range.group(2))
        if val_num < low:
            return "Low"
        if val_num > high:
            return "High"
        return "Normal"

    # Upper bound: < 200 or <= 150
    m_lt = re.search(r"<=?\s*(\d+(?:\.\d+)?)", ref_clean)
    if m_lt:
        high = float(m_lt.group(1))
        return "High" if val_num >= high and "<=" not in ref_clean else ("High" if val_num > high else "Normal")

    # Lower bound: > 40 or >= 40
    m_gt = re.search(r">=?\s*(\d+(?:\.\d+)?)", ref_clean)
    if m_gt:
        low = float(m_gt.group(1))
        return "Low" if val_num <= low and ">=" not in ref_clean else ("Low" if val_num < low else "Normal")

    return None


def _match_catalog(param_name: str) -> Optional[Tuple[str, str, str, str, Optional[float], Optional[float], str]]:
    name_l = param_name.lower().strip()
    for entry in CLINICAL_REFERENCE_CATALOG:
        if re.search(entry[0], name_l):
            return entry
    return None


def _is_ignored_line(line: str) -> bool:
    l = line.strip()
    if len(l) < 3:
        return True
    for pat in IGNORE_LINE_PATTERNS:
        if re.match(pat, l, re.IGNORECASE):
            return True
    return False


def _detect_section_header(line: str) -> Optional[str]:
    l = line.strip()
    if not l or len(l) > 80:
        return None
    # A section header typically does NOT contain a standalone measurement value + unit
    has_number = bool(re.search(r"\b\d+(?:\.\d+)?\b", l))
    l_lower = l.lower().strip(" :-[]()")
    if not has_number:
        for kw in SECTION_KEYWORDS:
            if kw in l_lower:
                return l.strip(" :-")
        # Also catch ALL CAPS headers like "CARDIAC RISK ASSESSMENT"
        if l.isupper() and len(l.split()) <= 6 and not any(w in l_lower for w in ["normal", "high", "low", "page"]):
            return l.title()
    return None


def _extract_flag_from_tokens(text: str) -> Optional[str]:
    t = text.strip().lower()
    if not t:
        return None
    # Check exact or parenthesized/bracketed flag tokens
    tokens = re.findall(r"[a-zA-Z]+|[↑↓\*]", t)
    for tok in reversed(tokens):
        if tok in FLAG_MAP:
            return FLAG_MAP[tok]
    return None


def _parse_row_text(line: str, current_section: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single lab report row into:
    {section, parameter_name, value, unit, reference_interval, flag, explanation}
    """
    raw = line.strip()
    if not raw or _is_ignored_line(raw):
        return None

    # Strategy 1: Columnar split (2+ spaces, tabs, or pipes) — typical of pypdf layout extraction
    cols = [c.strip() for c in re.split(r"\s{2,}|\t+|\|", raw) if c.strip()]

    param_name = ""
    value_str = ""
    unit_str = ""
    ref_str = ""
    explicit_flag = None

    if len(cols) >= 2:
        # Find the first column that looks like a result value (starts with optional </>/<=/>= and a number)
        val_col_idx = None
        for idx in range(1, len(cols)):
            if re.match(r"^(?:[<>]=?\s*)?[-+]?\d[\d,]*(?:\.\d+)?(?:\s+" + UNIT_PATTERN + r")?(?:\s*\*?[HLhl]\*?)?$", cols[idx], re.IGNORECASE):
                val_col_idx = idx
                break

        if val_col_idx is not None:
            param_name = " ".join(cols[:val_col_idx]).strip(" :-")
            val_col = cols[val_col_idx]

            # Split value, optional attached unit, optional attached flag (e.g. "165 mg/dL H" or "242*")
            m_val = re.match(
                r"^((?:[<>]=?\s*)?[-+]?\d[\d,]*(?:\.\d+)?)\s*(" + UNIT_PATTERN + r")?\s*(\*?([HL]|HIGH|LOW|ABNORMAL|NORMAL|N)\*?)?$",
                val_col,
                re.IGNORECASE
            )
            if m_val:
                value_str = m_val.group(1).strip()
                if m_val.group(2):
                    unit_str = m_val.group(2).strip()
                if m_val.group(3):
                    explicit_flag = _extract_flag_from_tokens(m_val.group(3))

            # Inspect remaining columns for unit, reference interval, and flag
            for extra in cols[val_col_idx + 1:]:
                extra_clean = extra.strip()
                # Is it purely a flag?
                flag_check = _extract_flag_from_tokens(extra_clean)
                if flag_check and re.fullmatch(r"[\(\[\*\s]*(?:H|L|N|HIGH|LOW|NORMAL|ABNORMAL|ELEVATED|DEFICIENT|BORDERLINE|OPTIMAL|DESIRABLE|CRITICAL|POS|NEG|POSITIVE|NEGATIVE|REACTIVE|↑|↓|\*)[\)\]\*\s]*", extra_clean, re.IGNORECASE):
                    explicit_flag = flag_check
                    continue

                # Is it purely a unit?
                if not unit_str and re.fullmatch(UNIT_PATTERN, extra_clean, re.IGNORECASE):
                    unit_str = extra_clean
                    continue

                # Does it look like a reference range (contains numbers with -, <, >, or words like Desirable/Normal)?
                if re.search(r"\d", extra_clean) and (
                    re.search(r"[-–<>]|to\b|desirable|normal|optimal|borderline|ref", extra_clean, re.IGNORECASE)
                ):
                    # Check if a trailing flag is attached to the reference column
                    m_trail_flag = re.search(r"\s+[\(\[]?(HIGH|LOW|ABNORMAL|NORMAL|H|L)[\)\]]?$", extra_clean, re.IGNORECASE)
                    if m_trail_flag and not explicit_flag:
                        explicit_flag = _extract_flag_from_tokens(m_trail_flag.group(1))
                        extra_clean = extra_clean[:m_trail_flag.start()].strip()
                    ref_str = (ref_str + " " + extra_clean).strip() if ref_str else extra_clean
                    continue

                # Otherwise if unit is still empty and it contains slash or %, take first unit match
                if not unit_str:
                    m_u = re.match(r"^(" + UNIT_PATTERN + r")\b", extra_clean, re.IGNORECASE)
                    if m_u:
                        unit_str = m_u.group(1)

    # Strategy 2: Inline single-spaced or colon-separated row
    # Example: "LDL Cholesterol: 165 mg/dL (Normal: < 100 mg/dL) - HIGH"
    # Example: "Serum Ferritin 18 ng/mL 30 - 400 Low"
    if not param_name or not value_str:
        m_inline = re.match(
            r"^([A-Za-z][A-Za-z0-9\s/\-\(\)\.,]+?)\s*[:\-]?\s+"
            r"((?:[<>]=?\s*)?[-+]?\d[\d,]*(?:\.\d+)?)\s*"
            r"(" + UNIT_PATTERN + r")?\s*(.*)$",
            raw,
            re.IGNORECASE
        )
        if m_inline:
            candidate_name = m_inline.group(1).strip(" :-")
            # Avoid matching dates or street addresses or patient IDs
            if len(candidate_name) >= 2 and not re.search(r"^(?:date|page|id|no|ref|age|tel|phone|fax)\b", candidate_name, re.IGNORECASE):
                param_name = candidate_name
                value_str = m_inline.group(2).strip()
                unit_str = (m_inline.group(3) or "").strip()
                rest = (m_inline.group(4) or "").strip()

                if rest:
                    explicit_flag = _extract_flag_from_tokens(rest)
                    # Strip flag words & brackets to isolate reference interval
                    ref_candidate = re.sub(r"[\(\[\-\s]*(?:HIGH|LOW|ABNORMAL|NORMAL|ELEVATED|DEFICIENT|BORDERLINE|CRITICAL|H|L)[\)\]\s]*$", "", rest, flags=re.IGNORECASE).strip()
                    ref_candidate = re.sub(r"^(?:Normal|Ref(?:erence)?(?:\s*Range|\s*Interval)?)\s*[:\-]?\s*", "", ref_candidate.strip("()[] "), flags=re.IGNORECASE).strip()
                    if re.search(r"\d", ref_candidate):
                        ref_str = ref_candidate

    if not param_name or not value_str:
        return None

    # Validate parameter name isn't just a number or noise, or a prescription line (Tab/Cap/Syp/Inj/Rx)
    if len(param_name) < 2 or param_name.replace(".", "").isdigit():
        return None
    if re.match(r"^(?:rx|tab\.?|tablet|cap\.?|capsule|syp\.?|syrup|inj\.?|injection|oint\.?|drop|drops)\b", param_name, re.IGNORECASE):
        return None

    catalog_match = _match_catalog(param_name)
    val_num = _parse_numeric(value_str)

    if not unit_str and catalog_match:
        unit_str = catalog_match[3]
    if not ref_str and catalog_match:
        ref_str = catalog_match[2]

    # Determine final flag
    flag = explicit_flag
    if not flag and ref_str:
        flag = _evaluate_flag_against_range(val_num, ref_str)
    if not flag and catalog_match and val_num is not None:
        _, _, _, _, low_t, high_t, _ = catalog_match
        if low_t is not None and val_num < low_t:
            flag = "Low"
        elif high_t is not None and val_num > high_t:
            flag = "High"
        else:
            flag = "Normal"
    if not flag:
        flag = "Normal"

    # Ensure unit is reflected cleanly in display value if needed, while keeping unit field explicit
    desc = catalog_match[6] if catalog_match else f"{param_name} diagnostic measurement"
    explanation = f"{desc} ({'Within reference interval' if flag == 'Normal' else f'Out of range: {flag}'})."

    return {
        "section": current_section,
        "parameter_name": param_name,
        "value": value_str,
        "unit": unit_str,
        "reference_interval": ref_str or "Standard Reference",
        "flag": flag,
        "explanation": explanation
    }


def parse_lab_report_rows(report_text: str) -> Dict[str, Any]:
    """
    Parses ALL rows and sections across a multi-panel medical/lab report.
    Never stops after the first row or first panel.
    Returns:
      {
        "sections": [str, ...],
        "rows": [{section, parameter_name, value, unit, reference_interval, flag, explanation}, ...]
      }
    """
    if not report_text:
        return {"sections": [], "rows": []}

    normalized = _normalize_text(report_text)
    lines = normalized.splitlines()

    current_section = "General Laboratory Panel"
    sections_seen: List[str] = []
    parsed_rows: List[Dict[str, Any]] = []
    seen_keys = set()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # 1. Check if line is a section/panel header
        sec = _detect_section_header(line)
        if sec:
            current_section = sec
            if sec not in sections_seen:
                sections_seen.append(sec)
            i += 1
            continue

        # 2. Try parsing the current line as a parameter row
        row = _parse_row_text(line, current_section)

        # 3. Handle wrapped multi-line rows:
        # Case A: current line has only a parameter name (no numbers), and next line starts with a number
        if row is None and not re.search(r"\d", line) and not _is_ignored_line(line) and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.match(r"^(?:[<>]=?\s*)?[-+]?\d", next_line):
                combined = f"{line}   {next_line}"
                row = _parse_row_text(combined, current_section)
                if row is not None:
                    i += 1  # consume next line too

        # Case B: row parsed, check if next line is an indented continuation of reference range or flag
        if row is not None and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and not _detect_section_header(next_line) and _parse_row_text(next_line, current_section) is None:
                # If next line looks like a standalone flag or reference interval continuation
                if re.fullmatch(r"[\(\[]?(?:HIGH|LOW|ABNORMAL|NORMAL|H|L)[\)\]]?", next_line, re.IGNORECASE):
                    f = _extract_flag_from_tokens(next_line)
                    if f:
                        row["flag"] = f
                    i += 1
                elif re.match(r"^(?:ref|normal|desirable|optimal|borderline)\s*[:\-]?\s*[<>\d\.\-\s]+$", next_line, re.IGNORECASE):
                    if row["reference_interval"] == "Standard Reference":
                        row["reference_interval"] = next_line
                        val_num = _parse_numeric(row["value"])
                        re_flag = _evaluate_flag_against_range(val_num, next_line)
                        if re_flag:
                            row["flag"] = re_flag
                    i += 1

        if row is not None:
            dedup_key = (row["parameter_name"].lower(), row["value"].lower())
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                if current_section not in sections_seen:
                    sections_seen.append(current_section)
                parsed_rows.append(row)

        i += 1

    return {
        "sections": sections_seen,
        "rows": parsed_rows
    }


# Common prescription medication knowledge base for deterministic fallback & enrichment
# Tuple: (regex_pattern, display_name, what_it_is, what_it_is_for, why_prescribed, precautions)
MEDICATION_KNOWLEDGE_CATALOG: List[Tuple[str, str, str, str, str, str]] = [
    (r"\bparacetamol\b|\bacetaminophen\b|\bdolo\b|\bcrocin\b|\btylenol\b", "Paracetamol (Acetaminophen)", "Analgesic & Antipyretic (Pain reliever & fever reducer)", "Fever, headache, body aches, and mild-to-moderate pain", "Reduces fever and relieves pain signals in the central nervous system without irritating the stomach.", "Avoid exceeding daily limits or combining with other acetaminophen-containing medicines; use caution in liver disease."),
    (r"\bibuprofen\b|\bbrufen\b|\badvil\b|\bmotrin\b", "Ibuprofen", "NSAID (Non-Steroidal Anti-Inflammatory Drug)", "Inflammation, joint/muscle pain, fever, and headache", "Blocks prostaglandin production to reduce swelling, pain, and fever.", "Take with food to protect the stomach; avoid in dengue/bleeding risk, kidney disease, or stomach ulcers."),
    (r"\bdiclofenac\b|\bvoveran\b", "Diclofenac", "NSAID (Anti-inflammatory painkiller)", "Joint pain, muscle sprains, arthritis, and acute inflammation", "Reduces inflammatory chemicals at the site of pain and swelling.", "Take after meals; avoid prolonged use without physician monitoring due to stomach/kidney risks."),
    (r"\bazithromycin\b|\bazithral\b|\bazee\b", "Azithromycin", "Macrolide Antibiotic", "Bacterial respiratory infections (throat, sinus, bronchitis), ear, or skin infections", "Stops bacteria from producing proteins needed to grow and multiply.", "Complete the full prescribed course even if you feel better early; only works against bacteria, not viruses."),
    (r"\bamoxicillin\b|\baugmentin\b|\bmoxikind\b|\bclavulanate\b", "Amoxicillin / Co-Amoxiclav", "Penicillin-class Antibiotic", "Bacterial sinusitis, throat/ear infections, chest infections, and urinary infections", "Kills susceptible bacteria by disrupting their cell wall formation.", "Check for penicillin allergy before use; complete the full prescribed course."),
    (r"\bcefixime\b|\bceftriaxone\b|\bcephalexin\b", "Cephalosporin Antibiotic (Cefixime/Cephalexin)", "Broad-spectrum Beta-lactam Antibiotic", "Bacterial respiratory, urinary tract, or typhoid/enteric infections", "Destroys bacterial cell walls to clear bacterial infection.", "Report any rash or allergic reaction; finish the prescribed duration."),
    (r"\bciprofloxacin\b|\blevofloxacin\b|\bofloxacin\b", "Fluoroquinolone Antibiotic", "Broad-spectrum Antibiotic", "Bacterial urinary tract, gastrointestinal, or respiratory infections", "Inhibits bacterial DNA replication to eliminate infection.", "Stay well hydrated; avoid taking simultaneously with calcium/iron supplements or antacids."),
    (r"\bcetirizine\b|\blevocetirizine\b|\bzyrtec\b|\bxyzal\b", "Cetirizine / Levocetirizine", "Second-generation Antihistamine", "Allergic rhinitis, sneezing, runny nose, itchy eyes, and skin hives", "Blocks histamine (H1) receptors to calm allergy symptoms.", "May cause mild drowsiness in some people; use caution when driving."),
    (r"\bfexofenadine\b|\ballegra\b|\bloratadine\b", "Fexofenadine / Loratadine", "Non-drowsy Antihistamine", "Seasonal allergies, nasal congestion/sneezing, and urticaria", "Blocks allergic histamine response with minimal sedation.", "Avoid taking fexofenadine with fruit juices (orange/apple/grapefruit) as they reduce absorption."),
    (r"\bmontelukast\b|\bmontair\b", "Montelukast", "Leukotriene Receptor Antagonist", "Asthma prevention, allergic rhinitis, and airway inflammation", "Blocks leukotrienes that narrow airways and trigger nasal/bronchial inflammation.", "Usually taken in the evening; report any mood or sleep changes to your doctor."),
    (r"\bomeprazole\b|\bpantoprazole\b|\brabeprazole\b|\besomeprazole\b|\bpan\s*40\b|\bpantocid\b", "Proton Pump Inhibitor (Pantoprazole / Omeprazole)", "Gastric Acid Suppressant (PPI)", "Acid reflux (GERD), heartburn, gastritis, and stomach ulcers", "Reduces stomach acid production by blocking proton pumps in the stomach lining, allowing irritation/ulcers to heal.", "Best taken 30–60 minutes before breakfast on an empty stomach."),
    (r"\bdomperidone\b|\bondansetron\b|\bemeset\b|\bvomikind\b", "Ondansetron / Domperidone", "Antiemetic / Prokinetic", "Nausea, vomiting, and gastric fullness", "Blocks nausea signaling in the gut and brain to prevent vomiting.", "Stay hydrated with small sips of fluids; follow physician timing instructions."),
    (r"\bmetformin\b|\bglucophage\b|\bglycomet\b", "Metformin", "Biguanide Antidiabetic Medication", "Type 2 Diabetes / elevated blood glucose", "Lowers liver glucose production and improves the body's insulin sensitivity.", "Take with meals to minimize stomach upset; monitor kidney function periodically."),
    (r"\batorvastatin\b|\brosuvastatin\b|\bstatin\b|\batorva\b|\brosuvas\b", "Statin (Atorvastatin / Rosuvastatin)", "Lipid-Lowering Statin", "High LDL cholesterol, high total cholesterol, and cardiovascular risk reduction", "Inhibits liver cholesterol production (HMG-CoA reductase) and clears LDL ('bad') cholesterol from the blood.", "Report unexplained muscle pain/weakness; avoid excessive grapefruit juice with atorvastatin."),
    (r"\baspirin\b|\becosprin\b|\bclopidogrel\b|\bplavix\b", "Aspirin / Clopidogrel", "Antiplatelet Medication", "Cardiovascular protection and prevention of blood clots", "Prevents platelets from clumping together inside blood vessels.", "Watch for unusual bruising or bleeding; never stop prescribed antiplatelets without talking to your cardiologist."),
    (r"\bamlodipine\b|\btelmisartan\b|\blosartan\b|\bmetoprolol\b|\batenolol\b", "Antihypertensive (Amlodipine / Telmisartan / Beta-blocker)", "Blood Pressure & Cardiac Medication", "Hypertension (high blood pressure) and heart strain protection", "Relaxes blood vessels or reduces heart workload to keep blood pressure in a safe range.", "Do not skip doses abruptly; monitor blood pressure regularly and rise slowly if dizzy."),
    (r"\bsalbutamol\b|\balbuterol\b|\basthalin\b|\bbudesonide\b", "Bronchodilator / Inhaled Corticosteroid", "Respiratory Inhaler / Airway Medication", "Asthma, wheezing, bronchospasm, and shortness of breath", "Relaxes airway muscles (salbutamol) or calms airway inflammation (budesonide) to make breathing easier.", "Rinse mouth after steroid inhalers; seek urgent care if rescue inhaler is needed frequently."),
    (r"\bprednisolone\b|\bprednisone\b|\bmethylprednisolone\b|\bdeflazacort\b", "Corticosteroid (Prednisolone / Methylprednisolone)", "Systemic Anti-inflammatory Steroid", "Severe inflammation, allergic flare-ups, asthma exacerbations, or autoimmune conditions", "Suppresses overactive immune and inflammatory pathways quickly.", "Take with food; do not stop suddenly after multi-day use without physician tapering instructions."),
    (r"\bvitamin\s*d3?\b|\bcholecalciferol\b|\bd[\-\s]*rise\b", "Vitamin D3 (Cholecalciferol)", "Fat-Soluble Vitamin Supplement", "Vitamin D deficiency, bone health, and immune support", "Restores Vitamin D levels to support calcium absorption and bone/muscle strength.", "Take with a meal containing healthy fats for best absorption."),
    (r"\bvitamin\s*b12\b|\bmethylcobalamin\b|\bcyanocobalamin\b|\bneurobion\b", "Vitamin B12 (Methylcobalamin)", "Water-Soluble Vitamin Supplement", "Vitamin B12 deficiency, nerve tingling, fatigue, and megaloblastic anemia", "Supports red blood cell formation and healthy nerve myelin function.", "Follow prescribed duration and recheck B12 levels as advised."),
    (r"\bferrous\b|\biron\b|\bferritin\b|\borofer\b|\bautrin\b|\bfolic\s*acid\b", "Iron / Folic Acid Supplement", "Hematinic (Blood-building Supplement)", "Iron deficiency anemia, low ferritin, and low hemoglobin", "Replenishes body iron stores required to produce healthy oxygen-carrying hemoglobin.", "Vitamin C helps absorption; avoid taking at the exact same time as tea, coffee, calcium, or antacids."),
    (r"\bambroxol\b|\bdextromethorphan\b|\bguaifenesin\b|\bascoryl\b|\bbenadryl\b", "Cough / Mucolytic Syrup", "Antitussive / Expectorant / Mucolytic", "Dry cough, productive phlegm cough, and chest congestion", "Either calms the cough reflex (dry cough) or thins mucus so it clears more easily (wet cough).", "Check whether it is sedating before driving; stay well hydrated."),
]


def extract_prescription_medications(report_text: str) -> List[Dict[str, str]]:
    """
    Extracts prescribed medicines from text/PDF prescription reports and returns
    structured explanations: what it is, what it is for, why prescribed, and precautions.
    """
    if not report_text:
        return []

    found: List[Dict[str, str]] = []
    seen = set()
    lines = _normalize_text(report_text).splitlines()

    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        line_l = line_s.lower()
        for pat, name, what_it_is, what_for, why_rx, prec in MEDICATION_KNOWLEDGE_CATALOG:
            if re.search(pat, line_l) and name not in seen:
                seen.add(name)
                # Preserve exact line snippet (e.g. "Tab. Azithromycin 500mg OD") if concise
                med_label = line_s if len(line_s) <= 75 else name
                if name.lower() not in med_label.lower():
                    med_label = f"{name} ({med_label})"
                found.append({
                    "medicine_name": med_label,
                    "what_it_is": what_it_is,
                    "what_it_is_for": what_for,
                    "why_prescribed": why_rx,
                    "precautions": prec
                })
    return found

