import re
from typing import Dict, Any, List, Set, Tuple, Optional

# Try importing spacy, or fallback to regex-based parser
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# Comprehensive mapping of colloquial patient terms to normalized clinical concepts
COLLOQUIAL_TO_CLINICAL = [
    # Sinusitis & Rhinology specific clinical presentations (All 7 cardinal manifestations)
    (r"\b(?:facial|face|cheek|forehead|sinus)\s*(?:pain|pressure|fullness|tightness|heaviness|tenderness|ache)\b|\bpressure\s*(?:in|around|over)\s*(?:face|sinuses|forehead|cheeks|eyes)\b", "facial pain / pressure / fullness"),
    (r"\b(?:stuffy|blocked|congested|plugged)\s*nose\b|\bnasal\s*(?:congestion|blockage|obstruction|stuffiness)\b|\bcongestion\b", "nasal congestion"),
    (r"\b(?:thick|discolored|yellow|green|cloudy|purulent)\s*(?:nasal\s*)?(?:discharge|drainage|mucus|snot|phlegm)\b|\bdiscolored\s*(?:nasal\s*)?(?:discharge|drainage)\b", "thick discolored nasal discharge"),
    (r"\bpost[- ]nasal\s*drip\b|\bmucus\s*(?:dripping|running|draining)\s*(?:in|down)\s*(?:the\s*)?(?:back\s*of\s*)?throat\b", "post-nasal drip"),
    (r"\bsinus\s*headaches?\b|\bfrontal\s*headaches?\b|\bheadache\s*(?:over|behind)\s*(?:eyes|forehead|cheeks)\b|\bforehead\s*headaches?\b", "sinus headache"),
    (r"\b(?:loss\s*of|cannot|can't|reduced|decreased|impaired|diminished)\s*(?:sense\s*of\s*)?(?:smell|taste)\b|\banosmia\b|\bhyposmia\b|\bloss\s*of\s*smell\b", "loss of smell (hyposmia/anosmia)"),
    (r"\b(?:ear|ears)\s*(?:fullness|pressure|plugged|clogged|blocked)\b|\bear\s*fullness\b", "ear fullness and pressure"),
    (r"\bhalitosis\b|\bbad\s*breath\b", "halitosis"),
    (r"\b(?:tooth|teeth|dental|maxillary)\s*(?:pain|ache)\s*(?:from\s*sinus|under\s*eyes)?\b", "dental / maxillary facial pain"),

    # Neurological / Headache & Sensory Sensitivities
    (r"\b(?:sensitive|sensitivity)\s*to\s*sound\b|\bphonophobia\b|\bloud\s*noises?\s*(?:hurt|bother|irritate)\b", "phonophobia (sensitivity to sound)"),
    (r"\bblurred\s*vision\b|\bblurry\s*vision\b|\bvisual\s*aura\b|\baura\s*(?:before|with)?\s*headache\b|\bflashing\s*lights?\s*in\s*vision\b", "blurred vision / visual aura"),
    (r"\b(?:pain\s*)?worsens?\s*with\s*(?:physical\s*)?activity\b|\b(?:worse|aggravated)\s*with\s*(?:movement|walking|exercise|physical\s*activity)\b", "aggravation with physical activity"),
    (r"\b(throbbing (headaches?|head pain)|one[- ]sided headaches?|migraines?|unilateral headache)\b", "hemicranial throbbing headache"),
    (r"\b(stiff neck|cannot bend neck|rigid neck|nuchal rigidity)\b", "nuchal rigidity (neck stiffness)"),
    (r"\b(light hurts eyes|sensitive to light|photophobia|sensitivity to light)\b", "photophobia"),
    (r"\b(room spinning|vertigo|loss of balance)\b", "vertigo"),
    (r"\b(lightheaded|woozy|fainting feeling|presyncope|dizziness)\b", "dizziness"),

    # Vector / Arbovirus specific expressions
    (r"\b(pain|ache|hurts?) behind (the )?eyes?\b|\bretro[- ]orbital (pain|ache)\b", "retro-orbital pain"),
    (r"\b(breakbone|breaking pain|bone[- ]breaking|severe bone pain)\b", "severe arthralgia (breakbone pain)"),
    (r"\b(red spots|tiny red dots|pinpoint red rash|petechiae|purpura)\b", "petechial rash"),
    (r"\b(mosquito bites?|mosquito exposure|stagnant water)\b", "vector exposure history"),

    # Chikungunya specific clinical presentations
    (r"\b(swollen joints?|joint swelling|puffy joints?|swelling in (wrists?|ankles?|knees?|fingers?|hands?|feet))\b", "joint swelling and periarticular edema"),
    (r"\b(wrist pain|ankle pain|pain in small joints|symmetrical joint pain|crippling joint pain|cannot walk|limping from joint pain|severe joint stiffness)\b", "severe symmetrical polyarthralgia (wrists/ankles/small joints)"),
    (r"\b(morning stiffness|stiff joints in the morning)\b", "morning joint stiffness"),

    # Critical Clinical Warning Signs (Dengue, Sepsis & Severe Infection)
    (r"\b(bleeding gums?|gum bleeding|blood from gums?|bleeding from gums?|spontaneous gum bleeding)\b", "mucosal bleeding (gum bleeding)"),
    (r"\b(nosebleed|nose bleed|epistaxis|bleeding from nose)\b", "mucosal bleeding (epistaxis)"),
    (r"\b(severe abdominal pain|severe stomach pain|intense belly pain|abdominal tenderness|stomach cramps severe)\b", "severe abdominal pain / tenderness"),
    (r"\b(persistent vomiting|vomiting frequently|cannot keep fluids? down|vomiting everything|incessant vomiting)\b", "persistent vomiting (inability to tolerate oral fluids)"),
    (r"\b(black stools?|tarry stools?|melena|blood in poop)\b", "melena (gastrointestinal hemorrhage)"),
    (r"\b(blood in vomit|vomiting blood|coffee ground emesis|hematemesis)\b", "hematemesis (blood in vomit)"),
    (r"\b(extreme lethargy|very drowsy|restlessness|feeling faint|collapse|cold clammy skin)\b", "lethargy, restlessness, and postural collapse"),
    (r"\b(puffy face|swollen abdomen|ascites|fluid in chest|pleural effusion)\b", "clinical fluid accumulation (plasma leakage)"),

    # Respiratory & Airway
    (r"\b(cannot catch breath|winded|out of breath|hard to breathe|gasping|trouble breathing)\b", "dyspnea (shortness of breath)"),
    (r"\b(coughing (up )?blood|blood in phlegm|blood in sputum|hemoptysis)\b", "hemoptysis"),
    (r"\b(scratchy throat|raw throat|throat tickle|throat pain|sore throat)\b", "pharyngitis (sore throat)"),
    (r"\b(phlegm|mucus|sputum|cough with gunk)\b", "productive cough"),
    (r"\b(dry cough|hacking cough|barking cough)\b", "dry cough"),
    (r"\b(runny nose|dripping nose|rhinorrhea)\b", "rhinorrhea (runny nose)"),
    (r"\b(wheezing|whistling breath|whistle in chest)\b", "wheezing"),
    (r"\b(cannot lie flat|need pillows to breathe|orthopnea)\b", "orthopnea / exertional dyspnea"),

    # Gastrointestinal
    (r"\b(throwing up|puking|vomiting|emesis)\b", "vomiting"),
    (r"\b(feeling sick to stomach|queasy|nauseated|nausea)\b", "nausea"),
    (r"\b(loose motions?|watery stools?|the runs|diarrhea)\b", "diarrhea"),
    (r"\b(burning in (chest|stomach|throat)|heartburn|acid reflux|sour water|acid burps?|waterbrash)\b", "pyrosis (acid reflux/heartburn)"),
    (r"\b(stomach aches?|belly pain|tummy pain|cramps in stomach|abdominal pain)\b", "abdominal pain"),

    # Cardiopulmonary / Thoracic
    (r"\b(crushing chest pain|chest tightness|pressure on chest|chest heaviness)\b", "chest pain / tightness"),
    (r"\bradiating\s*(?:chest\s*)?pain\s*(?:to\s*)?(?:left\s*arm|jaw|neck|back)\b", "chest pain radiating to arm/jaw"),
    (r"\b(cold sweats?|profuse sweating|diaphoresis|drenching sweat)\b", "diaphoresis (profuse sweating)"),

    # Systemic / Metabolic / Infection
    (r"\b(burning (when|while) peeing|painful urination|dysuria)\b", "dysuria"),
    (r"\b(peeing (all the time|constantly|frequently)|frequent urination|polyuria)\b", "polyuria"),
    (r"\b(thirsty all the time|excessive thirst|drinking gallons|polydipsia)\b", "polydipsia"),
    (r"\b(yellowing of (eyes|skin)|yellow eyes|dark urine with yellow skin|jaundice)\b", "jaundice (icterus)"),
    (r"\b(shivering|teeth chattering|shaking chills|rigors)\b", "rigors and chills"),
    (r"\b(burning hot fever|high fever|102|103|104|pyrexia)\b", "high-grade fever"),
    (r"\b(body aches?|muscle aches?|myalgia|aching all over)\b", "generalized myalgia")
]

WHO_DENGUE_WARNING_PATTERNS = [
    (r"\b(bleeding gums?|gum bleeding|blood from gums?|bleeding from gums?|spontaneous gum bleeding)\b", "mucosal bleeding (gum bleeding)"),
    (r"\b(nosebleed|nose bleed|epistaxis|bleeding from nose)\b", "mucosal bleeding (epistaxis)"),
    (r"\b(severe abdominal pain|severe stomach pain|intense belly pain|abdominal tenderness|stomach cramps severe)\b", "severe abdominal pain / tenderness"),
    (r"\b(persistent vomiting|vomiting frequently|cannot keep fluids? down|vomiting everything|incessant vomiting)\b", "persistent vomiting (inability to tolerate oral fluids)"),
    (r"\b(black stools?|tarry stools?|melena|blood in poop)\b", "melena (gastrointestinal hemorrhage)"),
    (r"\b(blood in vomit|vomiting blood|coffee ground emesis|hematemesis)\b", "hematemesis (blood in vomit)"),
    (r"\b(extreme lethargy|very drowsy|restlessness|feeling faint|collapse|cold clammy skin)\b", "lethargy, restlessness, and postural collapse"),
    (r"\b(puffy face|swollen abdomen|ascites|fluid in chest|pleural effusion)\b", "clinical fluid accumulation (plasma leakage)")
]

# Standard Medical Entity Lexicon
CLINICAL_SYMPTOMS = [
    # Sinus & Rhinology (All 7 cardinal sinusitis symptoms + ENT)
    "facial pain / pressure / fullness", "facial pressure", "facial pain", "facial fullness", "facial tenderness",
    "nasal congestion", "thick discolored nasal discharge", "nasal discharge", "post-nasal drip",
    "sinus headache", "frontal headache", "loss of smell (hyposmia/anosmia)", "loss of smell", "anosmia", "hyposmia",
    "ear fullness and pressure", "ear fullness", "halitosis", "dental / maxillary facial pain",

    # Neurological & Sensory
    "hemicranial throbbing headache", "headache", "photophobia", "phonophobia (sensitivity to sound)",
    "phonophobia", "blurred vision / visual aura", "blurred vision", "visual aura", "aggravation with physical activity",
    "nuchal rigidity (neck stiffness)", "dizziness", "vertigo",

    # Systemic, Arboviral & Infectious
    "fever", "high-grade fever", "chills", "rigors and chills", "retro-orbital pain",
    "severe arthralgia (breakbone pain)", "joint swelling and periarticular edema",
    "severe symmetrical polyarthralgia (wrists/ankles/small joints)", "morning joint stiffness",
    "joint pain", "generalized myalgia", "fatigue", "lethargy", "weakness",
    "rash", "petechial rash", "hives", "pruritus", "itching", "swelling", "edema", "back pain",

    # Respiratory & Airway
    "dry cough", "productive cough", "cough", "shortness of breath", "dyspnea (shortness of breath)",
    "wheezing", "orthopnea / exertional dyspnea", "pharyngitis (sore throat)", "rhinorrhea (runny nose)",
    "sneezing", "hemoptysis",

    # Thoracic & Cardiac
    "chest pain / tightness", "chest pain", "chest tightness", "chest pain radiating to arm/jaw",
    "palpitations", "diaphoresis (profuse sweating)",

    # Gastrointestinal
    "nausea", "vomiting", "diarrhea", "abdominal pain", "severe abdominal pain / tenderness",
    "pyrosis (acid reflux/heartburn)", "loss of appetite", "weight loss", "persistent vomiting",
    "melena (gastrointestinal hemorrhage)", "hematemesis (blood in vomit)",

    # Metabolic & Renal
    "dysuria", "polyuria", "polydipsia", "jaundice (icterus)", "mucosal bleeding",
    "insomnia", "numbness", "tingling"
]

TEST_PATTERNS = [
    (r"\bdengue ns1\b|\bns1 antigen\b", "Dengue NS1 Antigen"),
    (r"\bdengue (igm|igg)\b|\bdengue serology\b", "Dengue Serology (IgM/IgG)"),
    (r"\bplatelet count\b|\bthrombocytes\b", "Platelet Count"),
    (r"\bhematocrit\b|\bhct\b|\bpcv\b", "Hematocrit (PCV)"),
    (r"\bmalaria (smear|antigen|rdt|card)\b", "Malaria Smear & Rapid Antigen Test"),
    (r"\btyphidot\b|\bwidal\b|\bblood culture\b", "Blood Culture / Typhidot"),
    (r"\bcbc\b|\bcomplete blood count\b|\bhemogram\b", "Complete Blood Count (CBC)"),
    (r"\bchest x-ray\b|\bcxr\b", "Chest X-Ray (PA View)"),
    (r"\becg\b|\bekg\b|\belectrocardiogram\b", "12-Lead Electrocardiogram (ECG)"),
    (r"\btroponin\b|\bhs-c?tn[it]\b", "Cardiac Troponin (hs-cTnI/T)"),
    (r"\bhba1c\b|\bglycated hemoglobin\b", "HbA1c"),
    (r"\bfasting blood (sugar|glucose)\b|\bfbs\b", "Fasting Blood Glucose"),
    (r"\blipid profile\b|\bcholesterol\b", "Lipid Profile"),
    (r"\blft\b|\bliver function\b|\balt\b|\bast\b|\bbilirubin\b", "Liver Function Panel (LFT)"),
    (r"\bkft\b|\bkidney function\b|\brenal panel\b|\bcreatinine\b", "Kidney Function Panel (KFT/eGFR)"),
    (r"\burinalysis\b|\burine routine\b|\burine r/m\b", "Urinalysis (Urine R/M)"),
    (r"\bcrp\b|\bc-reactive protein\b", "C-Reactive Protein (CRP)"),
    (r"\besr\b|\berythrocyte sedimentation\b", "Erythrocyte Sedimentation Rate (ESR)"),
    (r"\bultrasound\b|\busg\b|\bultra[- ]sound abdomen\b", "Abdominal Ultrasonography (USG)"),
    (r"\bpulse oximetry\b|\bspo2\b", "Pulse Oximetry (SpO2)")
]

# ConText-style Negation Triggers (MedSpaCy rule semantics)
NEGATION_PRE = [
    r"\bno\b", r"\bnot\b", r"\bdenies\b", r"\bdenied\b", r"\bwithout\b",
    r"\bnegative for\b", r"\bruled out\b", r"\bnever had\b", r"\brules out\b",
    r"\bfree of\b", r"\bneither\b", r"\bnor\b", r"\bzero\b"
]

HISTORICAL_TRIGGERS = [
    r"\bpast medical history\b", r"\bhistory of\b", r"\bprior\b", r"\bpreviously\b",
    r"\byears ago\b", r"\bdiagnosed in\b", r"\bformer\b", r"\bresolved\b", r"\blast year\b"
]

FAMILY_TRIGGERS = [
    r"\bfamily history\b", r"\bmother has\b", r"\bmother had\b", r"\bfather has\b",
    r"\bfather had\b", r"\bsister\b", r"\bbrother\b", r"\bparents\b"
]

WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1, "couple": 2, "few": 3, "several": 4
}

class ClinicalTextExtractor:
    """
    Enhanced MedSpaCy-compatible Clinical Text Extractor.
    Extracts medical entities, maps colloquial vernacular to standardized medical terms,
    applies ConText modifiers (Negation, Temporality, Experiencer), and detects clinical syndromes.
    """

    def __init__(self):
        self.use_spacy = nlp is not None

    def _split_into_sentences(self, text: str) -> List[str]:
        if self.use_spacy:
            doc = nlp(text)
            return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        return [s.strip() for s in re.split(r"[.\n;]+", text) if s.strip()]

    def _is_span_negated(self, text: str, start: int, end: int) -> bool:
        """
        Determines if a symptom span is negated using strict syntactic scope.
        A symptom is negated if preceded by a negation trigger in the same clause,
        or followed by a post-negation trigger, WITHOUT crossing resetting conjunctions
        (e.g., 'but', 'however', 'although', 'except', '.', ';').
        """
        pre_text = text[:start]
        clauses = re.split(r"[.;]|\b(?:but|however|although|except|yet|nevertheless)\b", pre_text, flags=re.IGNORECASE)
        immediate_clause = clauses[-1] if clauses else pre_text

        for trig in NEGATION_PRE:
            # Matches negation trigger followed by up to 6 words/commas before symptom
            if re.search(rf"{trig}(?:\s+[\w\-]+|\s*,|\s+or|\s+and){{0,6}}\s*$", immediate_clause, re.IGNORECASE):
                return True

        # Check post-negation trigger (e.g. 'cough: absent', 'fever was ruled out')
        post_text = text[end:end+40]
        post_clauses = re.split(r"[.;]|\b(?:but|however|although|except|yet|nevertheless)\b", post_text, flags=re.IGNORECASE)
        immediate_post = post_clauses[0] if post_clauses else post_text
        if re.search(r"^(?:\s+is|\s+was|:)?\s*(?:absent|none|ruled out|negative|not present|denied)\b", immediate_post, re.IGNORECASE):
            return True

        return False

    def _is_span_historical(self, text: str, start: int, end: int) -> bool:
        pre_text = text[:start]
        clauses = re.split(r"[.;]|\b(?:but|however|although|except|yet|now|currently)\b", pre_text, flags=re.IGNORECASE)
        immediate_clause = clauses[-1] if clauses else pre_text
        for trig in HISTORICAL_TRIGGERS:
            if re.search(rf"{trig}(?:\s+[\w\-]+|\s*,){{0,6}}\s*$", immediate_clause, re.IGNORECASE):
                return True
        return False

    def _is_span_family(self, text: str, start: int, end: int) -> bool:
        pre_text = text[:start]
        clauses = re.split(r"[.;]|\b(?:but|however|although|except|yet|i have|patient has)\b", pre_text, flags=re.IGNORECASE)
        immediate_clause = clauses[-1] if clauses else pre_text
        for trig in FAMILY_TRIGGERS:
            if re.search(rf"{trig}(?:\s+[\w\-]+|\s*,){{0,6}}\s*$", immediate_clause, re.IGNORECASE):
                return True
        return False

    def _extract_symptom_attributes(self, sentence: str, start: int, end: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts duration and severity specific to an individual symptom's clause or sentence.
        Preserves individual symptom timelines and avoids overwriting with the general duration.
        """
        pre_text = sentence[:start]
        post_text = sentence[end:]
        
        # Split on clause delimiters (commas, semicolons, conjunctions)
        pre_clauses = re.split(r"[,;]|\b(?:and|with|but|however|except)\b", pre_text, flags=re.IGNORECASE)
        clause_pre = pre_clauses[-1] if pre_clauses else pre_text
        
        post_clauses = re.split(r"[,;]|\b(?:and|with|but|however|except)\b", post_text, flags=re.IGNORECASE)
        clause_post = post_clauses[0] if post_clauses else post_text
        
        clause = f"{clause_pre} {sentence[start:end]} {clause_post}".strip()
        
        # 1. Search duration in the immediate clause
        dur = None
        dur_match = re.search(
            r"\b(?:for|lasting|over|since|duration:?)\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten|couple|few|several)\s*(hours?|hrs?|days?|weeks?|months?|minutes?|mins?)\b",
            clause,
            re.IGNORECASE
        )
        if dur_match:
            val_str = dur_match.group(1).lower()
            val = int(val_str) if val_str.isdigit() else WORD_NUMS.get(val_str, 1)
            unit = dur_match.group(2).lower()
            dur = f"{val} {unit}"
        else:
            dur_match2 = re.search(
                r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(hours?|hrs?|days?|weeks?|months?|minutes?|mins?)\b",
                clause,
                re.IGNORECASE
            )
            if dur_match2:
                val_str = dur_match2.group(1).lower()
                val = int(val_str) if val_str.isdigit() else WORD_NUMS.get(val_str, 1)
                unit = dur_match2.group(2).lower()
                dur = f"{val} {unit}"

        # 2. Search severity in the immediate clause
        sev = None
        for word in ["mild", "moderate", "severe", "excruciating", "unbearable", "high-grade", "low-grade", "critical", "intense"]:
            if re.search(r"\b" + re.escape(word) + r"\b", clause, re.IGNORECASE):
                sev = word.capitalize()
                break

        return dur, sev

    def extract_severity(self, text: str, explicit_severity: Optional[int] = None) -> Dict[str, Any]:
        """Extracts quantitative and qualitative severity indicators."""
        score = explicit_severity
        if score is None:
            num_match = re.search(r"\b(\d{1,2})\s*/\s*10\b|\bseverity\s*:\s*(\d{1,2})\b", text, re.IGNORECASE)
            if num_match:
                score = int(num_match.group(1) or num_match.group(2))

        qual = []
        for word in ["mild", "moderate", "severe", "excruciating", "unbearable", "high-grade", "low-grade", "critical", "intense"]:
            if re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE):
                qual.append(word)

        level = "Moderate"
        if score is not None:
            level = "Mild" if score <= 3 else "Moderate" if score <= 6 else "Severe"
        elif any(w in qual for w in ["severe", "excruciating", "unbearable", "high-grade", "critical", "intense"]):
            level = "Severe"
        elif any(w in qual for w in ["mild", "low-grade"]):
            level = "Mild"

        return {
            "score_1_10": score,
            "qualitative": list(set(qual)),
            "overall_level": level
        }

    def extract_duration(self, text: str, explicit_duration: Optional[str] = None) -> Dict[str, Any]:
        """Extracts duration and categorizes acute early (<=5 days) vs late/convalescent (>5 days)."""
        dur_target = explicit_duration if explicit_duration and explicit_duration.strip().lower() not in ["not specified", "none", ""] else text
        
        m = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|couple|few|several|a|an)(?:\s*(?:to|-)\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten))?\s*(day|days|week|weeks|month|months|hour|hours)\b", dur_target, re.IGNORECASE)
        duration_str = None
        days = None
        if m:
            val_str = m.group(1).lower()
            val = int(val_str) if val_str.isdigit() else WORD_NUMS.get(val_str, 1)
            unit = m.group(3).lower()
            duration_str = f"{val} {unit}"
            if "day" in unit:
                days = val
            elif "week" in unit:
                days = val * 7
            elif "month" in unit:
                days = val * 30
            elif "hour" in unit:
                days = max(1, val // 24)
        elif re.search(r"\b(started today|today|sudden onset today)\b", dur_target, re.IGNORECASE):
            duration_str = "started today"
            days = 1
        elif re.search(r"\b(yesterday|started yesterday)\b", dur_target, re.IGNORECASE):
            duration_str = "yesterday"
            days = 2
        elif explicit_duration and explicit_duration.strip() and explicit_duration.strip().lower() not in ["not specified", "none"]:
            duration_str = explicit_duration.strip()
            digits = re.findall(r"\d+", duration_str)
            if digits:
                days = int(digits[0])

        return {
            "raw_duration": duration_str or "Not specified",
            "estimated_days": days,
            "is_acute_early": days is not None and days <= 5,
            "is_convalescent_late": days is not None and days > 5
        }

    def extract_warning_signs(self, text: str) -> List[str]:
        """Extracts WHO and clinical emergency warning signs."""
        detected = []
        for pat, term in WHO_DENGUE_WARNING_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                if term not in detected:
                    detected.append(term)
        return detected

    def extract_entities(
        self,
        text: str,
        accompanying_symptoms: Optional[List[str]] = None,
        explicit_duration: Optional[str] = None,
        explicit_severity: Optional[int] = None
    ) -> Dict[str, Any]:
        sentences = self._split_into_sentences(text)
        
        extracted_symptoms = []
        extracted_tests = []
        negated_findings = []
        historical_findings = []
        family_findings = []
        seen_entities = set()

        for sentence in sentences:
            sent_lower = sentence.lower()

            # 1. Colloquial / Multi-word medical equivalents with span-level context
            for pattern, normalized_term in COLLOQUIAL_TO_CLINICAL:
                for match in re.finditer(pattern, sent_lower):
                    start, end = match.span()
                    raw_span = sentence[start:end].strip()
                    is_neg = self._is_span_negated(sent_lower, start, end)
                    is_hist = self._is_span_historical(sent_lower, start, end)
                    is_fam = self._is_span_family(sent_lower, start, end)

                    # Preserve the patient's actual distinct symptom term (do not merge distinct symptoms)
                    symptom_display = raw_span if len(raw_span) >= 3 else normalized_term
                    key = f"symptom:{raw_span.lower()}"
                    if key not in seen_entities:
                        seen_entities.add(key)
                        if is_neg:
                            negated_findings.append(symptom_display)
                        elif is_hist:
                            historical_findings.append(symptom_display)
                        elif is_fam:
                            family_findings.append(symptom_display)
                        else:
                            dur, sev = self._extract_symptom_attributes(sentence, start, end)
                            extracted_symptoms.append({
                                "text": symptom_display,
                                "raw_text": raw_span,
                                "normalized": normalized_term,
                                "category": "PROBLEM",
                                "sentence": sentence,
                                "duration": dur,
                                "severity": sev,
                                "is_negated": False
                            })

            # 2. Standard symptom vocabulary with span-level context
            for term in CLINICAL_SYMPTOMS:
                escaped = re.escape(term.split(" (")[0])
                for match in re.finditer(r"\b" + escaped + r"\b", sent_lower):
                    start, end = match.span()
                    raw_span = sentence[start:end].strip()
                    is_neg = self._is_span_negated(sent_lower, start, end)
                    is_hist = self._is_span_historical(sent_lower, start, end)
                    is_fam = self._is_span_family(sent_lower, start, end)

                    symptom_display = raw_span if len(raw_span) >= 3 else term
                    key = f"symptom:{raw_span.lower()}"
                    if key not in seen_entities:
                        seen_entities.add(key)
                        if is_neg:
                            negated_findings.append(symptom_display)
                        elif is_hist:
                            historical_findings.append(symptom_display)
                        elif is_fam:
                            family_findings.append(symptom_display)
                        else:
                            dur, sev = self._extract_symptom_attributes(sentence, start, end)
                            extracted_symptoms.append({
                                "text": symptom_display,
                                "raw_text": raw_span,
                                "normalized": term,
                                "category": "PROBLEM",
                                "sentence": sentence,
                                "duration": dur,
                                "severity": sev,
                                "is_negated": False
                            })

            # 3. Medical Tests
            for pat, std_name in TEST_PATTERNS:
                for match in re.finditer(pat, sent_lower):
                    start, end = match.span()
                    is_neg = self._is_span_negated(sent_lower, start, end)
                    key = f"test:{std_name}"
                    if key not in seen_entities:
                        seen_entities.add(key)
                        extracted_tests.append({
                            "text": std_name,
                            "category": "TEST",
                            "sentence": sentence,
                            "is_negated": is_neg
                        })

        active_symptom_names = [e["text"] for e in extracted_symptoms]

        # 4. Integrate frontend accompanying symptoms directly: NEVER merge or drop distinct selections
        if accompanying_symptoms:
            for acc in accompanying_symptoms:
                if not acc or not isinstance(acc, str):
                    continue
                acc_clean = acc.strip()
                if not acc_clean:
                    continue
                # Do NOT merge different symptoms: keep every distinct reported symptom
                if not any(acc_clean.lower() == s.lower() for s in active_symptom_names):
                    active_symptom_names.append(acc_clean)
                    extracted_symptoms.append({
                        "text": acc_clean,
                        "raw_text": acc_clean,
                        "normalized": acc_clean,
                        "category": "PROBLEM",
                        "sentence": f"Accompanying symptom: {acc_clean}",
                        "duration": None,
                        "severity": None,
                        "is_negated": False
                    })

        # 5. Fallback list/bullet extractor: captures any symptoms from numbered or comma-separated lists strictly in chief complaint
        complaint_part = re.split(r"\b(?:Duration|Severity|Accompanying symptoms|Known chronic conditions|Known allergies)\s*:", text, flags=re.IGNORECASE)[0]
        list_items = re.split(r"(?:\r?\n|\b\d+[\.\)\-]\s*|\s*,\s*)", complaint_part)
        for item in list_items:
            item_clean = re.sub(r"^(?:and\s+|with\s+|also\s+)", "", item.strip(), flags=re.IGNORECASE).strip()
            item_clean = item_clean.strip(".,;:").strip()
            if 3 <= len(item_clean) <= 50:
                if not re.search(r"^(?:duration|severity|days?|hours?|weeks?|months?|age|gender|patient|male|female|none|yes|no)\b", item_clean, re.IGNORECASE):
                    if not any(item_clean.lower() == s.lower() for s in active_symptom_names):
                        if not self._is_span_negated(item_clean.lower(), 0, len(item_clean)):
                            active_symptom_names.append(item_clean)
                            extracted_symptoms.append({
                                "text": item_clean,
                                "raw_text": item_clean,
                                "normalized": item_clean,
                                "category": "PROBLEM",
                                "sentence": item_clean,
                                "duration": None,
                                "severity": None,
                                "is_negated": False
                            })

        severity_info = self.extract_severity(text, explicit_severity=explicit_severity)
        duration_info = self.extract_duration(text, explicit_duration=explicit_duration)
        warning_signs = self.extract_warning_signs(text)
        syndromes = self.detect_clinical_syndromes(
            symptoms=active_symptom_names,
            full_text=text.lower(),
            warning_signs=warning_signs,
            negated_symptoms=negated_findings
        )

        return {
            "active_symptoms": active_symptom_names,
            "active_symptoms_detailed": extracted_symptoms,
            "negated_symptoms": negated_findings,
            "historical_conditions": historical_findings,
            "family_history": family_findings,
            "tests_mentioned": [t["text"] for t in extracted_tests],
            "severity_info": severity_info,
            "duration_info": duration_info,
            "warning_signs": warning_signs,
            "has_warning_signs": len(warning_signs) > 0,
            "detected_syndromes": syndromes,
            "details": {
                "symptoms": extracted_symptoms,
                "tests": extracted_tests
            }
        }

    # pyrefly: ignore[unknown-name]
    def detect_clinical_syndromes(self, symptoms: List[str], full_text: str = "", 
                                  warning_signs: Optional[List[str]] = None,
                                  negated_symptoms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Combinatorial syndrome analyzer. Evaluates constellation of symptoms,
        severity, duration, and warning signs rather than isolated individual keywords.
        Accurately differentiates Dengue vs Chikungunya vs Malaria vs Respiratory.
        """
        syndromes = []
        active_sym_str = " ".join(symptoms).lower()
        negated_list = [n.lower() for n in (negated_symptoms or [])]
        active_warnings = warning_signs or self.extract_warning_signs(full_text)
        sym_str = active_sym_str + " " + full_text.lower()

        # Check symptom components from ACTIVE symptoms to avoid negated false positives
        has_fever = any(w in active_sym_str or (w in full_text.lower() and not any(w in n for n in negated_list)) for w in ["fever", "pyrexia", "temperature", "chills", "rigors", "burning hot", "high-grade"])
        has_retro_orbital = any(w in active_sym_str or (w in full_text.lower() and not any(w in n for n in negated_list)) for w in ["retro-orbital", "behind eyes", "eye pain", "eye ache", "behind the eye"])
        has_bone_joint = any(w in active_sym_str for w in ["breakbone", "bone pain", "joint pain", "myalgia", "body ache", "arthralgia", "aching all over"])
        has_rash_or_bleed = any(w in active_sym_str for w in ["petechiae", "red spots", "rash", "bleeding", "nosebleed", "gums", "epistaxis"]) or bool(active_warnings)
        
        # Respiratory & Airway components (strictly active and not negated)
        has_true_cough = any(w in active_sym_str for w in ["cough", "phlegm", "sputum", "sore throat", "wheez", "productive cough", "dry cough", "bronchial"])
        has_chest_pain = any(w in active_sym_str for w in ["chest pain", "crushing pain", "pressure in chest", "chest tightness", "angina"])

        # Chikungunya-specific markers: prominent joint swelling, wrists/ankles/small joints, morning stiffness
        has_chikungunya_markers = any(w in active_sym_str or (w in full_text.lower() and not any(w in n for n in negated_list)) for w in [
            "chikungunya", "swollen joint", "joint swelling", "wrist", "ankle",
            "small joints", "symmetrical joint", "morning stiffness", "cannot walk", "limping from joint"
        ])

        # Malaria-specific markers: cyclical rigors, shaking chills, profuse diaphoresis paroxysms
        has_malaria_markers = any(w in sym_str for w in [
            "malaria", "cyclical fever", "shivering chills", "teeth chattering", "rigors and chills", "paroxysm"
        ])

        # Sinonasal / Rhinosinusitis markers
        sinonasal_keys = [
            "facial pain", "facial pressure", "facial fullness", "facial tenderness",
            "nasal congestion", "thick discolored nasal discharge", "nasal discharge",
            "post-nasal drip", "sinus headache", "loss of smell", "hyposmia", "anosmia", "sinus"
        ]
        matched_sinonasal = [k for k in sinonasal_keys if any(k in s for s in symptoms) or k in full_text.lower()]
        has_sinonasal = len(matched_sinonasal) >= 2 or any(k in active_sym_str for k in ["facial pressure", "sinus headache", "thick discolored nasal discharge", "post-nasal drip"])

        # Migraine / Neurovascular markers
        migraine_keys = [
            "hemicranial throbbing headache", "throbbing headache", "one-sided headache", "migraine",
            "photophobia", "phonophobia", "blurred vision", "visual aura", "aggravation with physical activity"
        ]
        matched_migraine = [k for k in migraine_keys if any(k in s for s in symptoms) or k in full_text.lower()]
        has_migraine = len(matched_migraine) >= 2 or "hemicranial" in active_sym_str or "migraine" in sym_str

        # 1. Neurological / Meningeal Syndrome (Highest Urgency)
        has_stiff_neck = any(w in sym_str for w in ["stiff neck", "neck stiffness", "nuchal rigidity"])
        if has_fever and has_stiff_neck:
            syndromes.append({
                "syndrome": "Suspected Acute Meningeal Syndrome",
                "confidence": "Critical",
                "constellation": ["High Fever", "Nuchal Rigidity (Neck Stiffness)", "Headache / Photophobia"],
                "warning": "EMERGENCY: Immediate emergency hospital evaluation required for possible acute meningitis / meningoencephalitis."
            })

        # 2. Acute Coronary / Cardiac Syndrome
        if has_chest_pain:
            syndromes.append({
                "syndrome": "Acute Thoracic / Cardiac Syndrome",
                "confidence": "High" if any(w in sym_str for w in ["radiating", "arm", "jaw", "sweating", "diaphoresis"]) else "Moderate",
                "constellation": ["Chest Pain / Pressure", "Thoracic Discomfort"],
                "warning": "URGENT: Rule out Acute Coronary Syndrome (ACS) with immediate 12-lead ECG and Cardiac Troponins."
            })

        # 3. Acute Rhinosinusitis / Sinonasal Complex
        if has_sinonasal:
            syndromes.append({
                "syndrome": "Acute Rhinosinusitis / Sinonasal Complex",
                "confidence": "High" if len(matched_sinonasal) >= 3 else "Moderate",
                "constellation": [
                    "Facial Pain / Pressure / Fullness",
                    "Nasal Obstruction / Congestion",
                    "Thick Discolored Nasal Discharge",
                    "Sinus Headache / Post-Nasal Drip",
                    "Hyposmia / Loss of Smell"
                ],
                "warning": "Watch for red flags: periorbital edema, erythema, visual changes, or persistent severe frontal pain with high fever."
            })

        # 4. Neurovascular Cephalea / Migraine Complex
        if has_migraine:
            syndromes.append({
                "syndrome": "Neurovascular Cephalea / Migraine Complex",
                "confidence": "High" if len(matched_migraine) >= 3 else "Moderate",
                "constellation": [
                    "Hemicranial Pulsatile Headache",
                    "Sensory Sensitivity (Photophobia / Phonophobia)",
                    "Nausea / Vegetative Symptoms",
                    "Visual Aura / Aggravation with Physical Activity"
                ]
            })

        # 5. Chikungunya Arboviral Polyarthritic Complex
        if has_fever and has_chikungunya_markers and not has_true_cough:
            syndromes.append({
                "syndrome": "Chikungunya Arboviral Polyarthritic Complex",
                "confidence": "High",
                "constellation": [
                    "High Fever",
                    "Severe Symmetrical Polyarthralgia (Wrists/Ankles/Hands)",
                    "Joint Swelling / Periarticular Edema",
                    "Morning Joint Stiffness"
                ],
                "warning": "High clinical suspicion for Chikungunya virus. Symmetrical peripheral joint swelling and disabling polyarthralgia distinguish this from uncomplicated dengue. Complete bed rest, supportive analgesia (avoid NSAIDs until dengue is serologically excluded), and serology advised."
            })

        # 6. Dengue Arboviral Febrile Complex
        is_dengue_match = has_fever and (
            has_retro_orbital or 
            has_rash_or_bleed or 
            len(active_warnings) > 0 or
            "dengue" in sym_str or 
            "mosquito" in sym_str or 
            (has_bone_joint and not has_true_cough and not has_chikungunya_markers and not has_sinonasal)
        )
        if is_dengue_match:
            dengue_warning = "CRITICAL CONTRAINDICATION: Strictly avoid NSAIDs (aspirin, ibuprofen, diclofenac, naproxen) due to severe thrombocytopenia and hemorrhage risk. Use Paracetamol only. Monitor platelet count and hematocrit daily."
            if active_warnings:
                dengue_warning = f"EMERGENCY WARNING: Active WHO Warning Signs Detected ({', '.join(active_warnings)}). Immediate hospital admission required for IV hydration and plasma leakage management! " + dengue_warning

            syndromes.append({
                "syndrome": "Dengue Arboviral Febrile Complex",
                "confidence": "High" if (has_retro_orbital or len(active_warnings) > 0 or "dengue" in sym_str) else "Moderate",
                "constellation": [
                    "Acute High-Grade Fever",
                    "Retro-Orbital Pain / Severe Headache",
                    "Diffuse Myalgias / 'Breakbone' Arthralgia",
                    "Petechiae / Warning Signs (Bleeding, Abdominal Pain, Vomiting)"
                ],
                "warning_signs_present": active_warnings,
                "warning": dengue_warning
            })

        # 7. Malarial Paroxysmal Syndrome
        if has_fever and has_malaria_markers and not has_true_cough:
            syndromes.append({
                "syndrome": "Malarial Paroxysmal Febrile Syndrome",
                "confidence": "High" if "malaria" in sym_str else "Moderate",
                "constellation": ["Cyclical Fever Paroxysms", "Rigors / Shaking Chills", "Diaphoresis (Profuse Sweating)", "Headache / Body Ache"],
                "warning": "Urgent peripheral blood smear (thick and thin films) and Rapid Diagnostic Test (RDT) required for Plasmodium detection."
            })

        # 8. Acute Respiratory Tract Syndrome (ONLY for true respiratory presentations not better accounted for by primary Sinonasal Complex)
        if has_true_cough and not (has_sinonasal and len(matched_sinonasal) >= 3 and not any(w in active_sym_str for w in ["wheez", "shortness of breath", "dyspnea", "chest tightness"])):
            syndromes.append({
                "syndrome": "Acute Respiratory Infection Syndrome",
                "confidence": "High" if ("cough" in sym_str and ("fever" in sym_str or "sore throat" in sym_str or "phlegm" in sym_str)) else "Moderate",
                "constellation": ["Cough / Airway Irritation", "Phlegm / Sputum", "Fever / Upper Airway Symptoms"]
            })

        # 9. Gastrointestinal Syndrome
        has_gi = any(w in sym_str for w in ["vomit", "nausea", "diarrhea", "loose stool", "acid reflux", "stomach pain", "pyrosis", "belly pain"])
        if has_gi:
            syndromes.append({
                "syndrome": "Acute Gastrointestinal / Dyspeptic Syndrome",
                "confidence": "High" if (("diarrhea" in sym_str or "vomit" in sym_str) and ("abdominal pain" in sym_str or "stomach" in sym_str)) else "Moderate",
                "constellation": ["Abdominal Symptoms", "Altered Motility / Emesis"]
            })

        # 10. Metabolic / Endocrine Syndrome
        has_poly = any(w in sym_str for w in ["polyuria", "polydipsia", "frequent urination", "excessive thirst", "high blood sugar", "sugar high"])
        if has_poly:
            syndromes.append({
                "syndrome": "Metabolic / Hyperglycemic Syndrome",
                "confidence": "Moderate",
                "constellation": ["Polyuria (Frequent Urination)", "Polydipsia (Excessive Thirst)"],
                "warning": "Evaluate blood glucose and HbA1c to screen for diabetes mellitus or diabetic ketoacidosis."
            })

        return syndromes

clinical_extractor = ClinicalTextExtractor()
