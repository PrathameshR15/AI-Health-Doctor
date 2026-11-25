from typing import List, Dict, Any
import re

# Curated Medical Knowledge Database with Verified Official Sources
OFFICIAL_MEDICAL_SOURCES = [
    # --- Respiratory & Infectious Diseases ---
    {
        "id": "ref_resp_who_ari",
        "title": "WHO Guidelines on Acute Respiratory Infections & Influenza",
        "organization": "WHO",
        "keywords": ["cough", "fever", "cold", "flu", "influenza", "bronchitis", "pneumonia", "shortness of breath", "sore throat"],
        "url": "https://www.who.int/health-topics/influenza-seasonal",
        "summary": "WHO clinical management guidelines emphasize hydration, antipyretics for high fever, rest, and monitoring for danger signs like cyanosis or rapid breathing.",
        "precautions": ["Adequate fluid intake", "Rest", "Steam inhalation", "Hand hygiene", "Mask wearing if around vulnerable individuals"],
        "recommended_tests": ["Complete Blood Count (CBC)", "Chest X-Ray (if fever persists or dyspnea presents)", "Influenza/COVID-19 rapid antigen test"]
    },
    {
        "id": "ref_resp_nhs_cough",
        "title": "NHS Overview: Coughs, Colds and Chest Infections",
        "organization": "NHS",
        "keywords": ["cough", "phlegm", "chest infection", "mucus", "runny nose", "sore throat"],
        "url": "https://www.nhs.uk/conditions/cough/",
        "summary": "NHS advises most coughs resolve within 3-4 weeks. Non-drug remedies like warm honey and lemon help soothe irritation. Antibiotics are not recommended for viral coughs.",
        "precautions": ["Warm fluids with honey and lemon", "Avoid tobacco smoke", "Rest and elevate head while sleeping"],
        "recommended_tests": ["Peak Flow measurement", "Sputum culture (if persistent green/yellow phlegm >3 weeks)"]
    },
    {
        "id": "ref_icmr_covid_ari",
        "title": "ICMR Clinical Guidance for Management of Adult Patients with Respiratory Infections",
        "organization": "ICMR",
        "keywords": ["fever", "cough", "breathlessness", "spO2", "oxygen", "viral infection", "icmr"],
        "url": "https://main.icmr.nic.in/content/guidelines-advisories",
        "summary": "ICMR clinical management protocol highlights frequent monitoring of oxygen saturation (SpO2 > 94%), symptomatic antipyretics, and early escalation for respiratory distress.",
        "precautions": ["SpO2 monitoring using pulse oximeter twice daily", "Hydration", "Isolation if contagious symptoms present"],
        "recommended_tests": ["CBC with differential", "CRP (C-Reactive Protein)", "Pulse Oximetry"]
    },
    {
        "id": "ref_ncdc_dengue_vector",
        "title": "NCDC India Guidelines for Management of Dengue and Vector-Borne Fevers",
        "organization": "NCDC India",
        "keywords": ["dengue", "high fever", "joint pain", "bone pain", "body ache", "headache", "platelet", "ncdc", "retro-orbital pain"],
        "url": "https://ncdc.mohfw.gov.in/index1.php?lang=1&level=1&sublinkid=703&lid=550",
        "summary": "National Centre for Disease Control (NCDC) protocol for vector fevers stresses close hematocrit and platelet monitoring, oral rehydration therapy, and avoidance of NSAIDs like aspirin/ibuprofen due to bleeding risk.",
        "precautions": ["Aggressive oral fluid therapy (ORS, coconut water)", "Bed rest", "Mosquito net protection", "Strictly avoid NSAIDs like aspirin/ibuprofen; use paracetamol only under guidance"],
        "recommended_tests": ["Dengue NS1 Antigen (Day 1-5)", "Dengue IgM/IgG ELISA", "Complete Blood Count (Platelet count, Hematocrit)"]
    },
    {
        "id": "ref_medline_hypertension",
        "title": "MedlinePlus: High Blood Pressure (Hypertension) Management",
        "organization": "MedlinePlus",
        "keywords": ["hypertension", "high blood pressure", "bp", "headache", "dizziness", "chest pressure"],
        "url": "https://medlineplus.gov/highbloodpressure.html",
        "summary": "MedlinePlus (National Library of Medicine) outlines lifestyle modifications: DASH diet, sodium restriction below 2300 mg/day, regular aerobic activity, and routine home blood pressure logs.",
        "precautions": ["Low-sodium dietary pattern (<2g sodium/day)", "Regular aerobic exercise (30 min/day)", "Stress reduction", "Limiting alcohol and caffeine"],
        "recommended_tests": ["Serial Blood Pressure monitoring", "Lipid Panel", "Serum Creatinine and eGFR", "Electrocardiogram (ECG)"]
    },
    {
        "id": "ref_who_diabetes",
        "title": "WHO Fact Sheet: Diabetes Mellitus Diagnosis & Dietary Care",
        "organization": "WHO",
        "keywords": ["diabetes", "high sugar", "frequent urination", "excessive thirst", "weight loss", "polyuria", "polydipsia", "glucose"],
        "url": "https://www.who.int/news-room/fact-sheets/detail/diabetes",
        "summary": "WHO guidelines emphasize glycemic control through balanced low-glycemic index diets, routine foot examinations, physical activity, and targeted microvascular screening.",
        "precautions": ["Low glycemic index meal planning", "Foot inspection daily", "Consistent carbohydrate distribution", "Routine self-monitoring of blood glucose"],
        "recommended_tests": ["Fasting Blood Glucose", "HbA1c (Glycated Hemoglobin)", "Urine Albumin-to-Creatinine Ratio (UACR)"]
    },
    {
        "id": "ref_nhs_migraine",
        "title": "NHS Health Guidance: Migraine and Tension Headache",
        "organization": "NHS",
        "keywords": ["headache", "migraine", "throbbing", "photophobia", "sensitivity to light", "nausea", "head pain"],
        "url": "https://www.nhs.uk/conditions/migraine/",
        "summary": "NHS recommends resting in a dark, quiet room during acute episodes. Maintaining a headache trigger diary (sleep, hydration, screen time, certain foods) helps identify aggravating factors.",
        "precautions": ["Rest in dark, quiet room", "Stay well-hydrated", "Cold or warm compresses on forehead/neck", "Maintain regular sleep schedule"],
        "recommended_tests": ["Clinical Neurological Examination", "Fundoscopy", "Brain MRI/CT if red flags present (sudden thunderclap onset)"]
    },
    {
        "id": "ref_medline_gerd",
        "title": "MedlinePlus: Gastroesophageal Reflux Disease (GERD) & Acidity",
        "organization": "MedlinePlus",
        "keywords": ["gerd", "acid reflux", "heartburn", "indigestion", "burning stomach", "stomach pain", "belching"],
        "url": "https://medlineplus.gov/gerd.html",
        "summary": "MedlinePlus outlines non-pharmacological reflux control: avoiding trigger foods (spicy, fatty, chocolate, citrus), eating smaller meals, and not lying down within 3 hours of eating.",
        "precautions": ["Avoid lying down for 3 hours after meals", "Elevate head of bed by 6 inches", "Avoid spicy, oily, acidic, and caffeinated items", "Eat smaller, more frequent meals"],
        "recommended_tests": ["Upper GI Endoscopy (if dysphagia, unexplained weight loss, or persistent symptoms)", "H. pylori stool antigen test"]
    },
    {
        "id": "ref_who_healthy_diet",
        "title": "WHO Healthy Diet Principles and Nutritional Recommendations",
        "organization": "WHO",
        "keywords": ["diet", "nutrition", "allergy", "food", "healthy eating", "cholesterol", "fiber"],
        "url": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        "summary": "WHO healthy diet framework advises at least 400g of fruit and vegetables daily, less than 10% total energy intake from free sugars, less than 30% from fats (favoring unsaturated fats), and less than 5g salt daily.",
        "precautions": ["Include diverse legumes, whole grains, and seasonal vegetables", "Eliminate trans-fats", "Hydrate with plain water"],
        "recommended_tests": ["Lipid Profile", "Nutritional Vitamin D and B12 assessment"]
    },
    {
        "id": "ref_icmr_dietary_guidelines",
        "title": "ICMR-NIN Dietary Guidelines for Indians (Latest Edition)",
        "organization": "ICMR",
        "keywords": ["icmr diet", "indian diet", "nin guidelines", "balanced plate", "protein", "micronutrients"],
        "url": "https://main.icmr.nic.in/content/guidelines-advisories",
        "summary": "National Institute of Nutrition (ICMR-NIN) recommends a diverse plate: 50% fresh vegetables, fruits, and greens; balanced pulses and cereals; limiting ultra-processed foods, high sodium, and refined oils.",
        "precautions": ["Incorporate millets and whole pulses", "Limit oil consumption to <20-25g/day per person", "Prioritize home-cooked fresh meals"],
        "recommended_tests": ["Comprehensive Metabolic Profile", "Complete Blood Count (CBC)"]
    }
]

def search_medical_knowledge(query_text: str, max_results: int = 4) -> List[Dict[str, Any]]:
    """
    Search and retrieve validated clinical guidelines and references
    from WHO, NHS, MedlinePlus, ICMR, and NCDC India.
    Matches queries against keywords, title, and clinical topics.
    """
    q_words = re.findall(r"\w+", query_text.lower())
    if not q_words:
        return OFFICIAL_MEDICAL_SOURCES[:max_results]

    scored = []
    for doc in OFFICIAL_MEDICAL_SOURCES:
        score = 0
        doc_kw = [k.lower() for k in doc["keywords"]]
        doc_text = (doc["title"] + " " + doc["summary"]).lower()

        for w in q_words:
            if len(w) < 3:
                continue
            if any(w in kw for kw in doc_kw):
                score += 3
            if w in doc_text:
                score += 1

        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item[1] for item in scored[:max_results]]
    
    # Fallback to general guidance if nothing matched
    if not results:
        results = [
            doc for doc in OFFICIAL_MEDICAL_SOURCES 
            if doc["organization"] in ["WHO", "NHS", "ICMR"]
        ][:max_results]
        
    return results

def get_sources_citation_list(docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate clean, authentic citation objects with actual external links.
    """
    citations = []
    seen = set()
    for d in docs:
        if d["url"] not in seen:
            seen.add(d["url"])
            citations.append({
                "title": d["title"],
                "organization": d["organization"],
                "url": d["url"],
                "key_takeaway": d["summary"][:160] + "..."
            })
    return citations
