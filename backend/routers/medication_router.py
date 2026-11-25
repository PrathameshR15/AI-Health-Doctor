from fastapi import APIRouter, Depends
from typing import List, Dict, Any, Optional

from backend.schemas import MedicationInfoRequest
from backend.auth import get_current_user
from backend.models import User
from backend.medical_knowledge import search_medical_knowledge, get_sources_citation_list

router = APIRouter(prefix="/api/medication", tags=["Medication Information"])

# Comprehensive Educational Medication Knowledge Catalog (NO DOSAGES / NO PRESCRIPTIONS)
MEDICATION_EDUCATIONAL_DATABASE = [
    {
        "drug_class": "Analgesics & Antipyretics",
        "common_agents": ["Paracetamol (Acetaminophen)"],
        "clinical_purpose": "Relieves mild to moderate pain (headache, body aches) and reduces fever.",
        "mechanism": "Centrally acting inhibitor of prostaglandin synthesis with antipyretic and analgesic effects.",
        "precautions": [
            "Strictly avoid combining with other medications containing acetaminophen to prevent accidental overdose.",
            "Avoid alcohol consumption as it elevates risk of acute liver toxicity.",
            "Patients with pre-existing hepatic impairment must consult their doctor prior to use."
        ],
        "common_side_effects": ["Rare at therapeutic levels; mild nausea, rash; overdose causes severe hepatotoxicity."],
        "key_interactions": ["Alcohol (increased hepatotoxicity)", "Warfarin (possible increased INR with prolonged high doses)"],
        "tags": ["fever", "pain", "headache", "body ache", "flu", "cold"]
    },
    {
        "drug_class": "Non-Steroidal Anti-Inflammatory Drugs (NSAIDs)",
        "common_agents": ["Ibuprofen", "Naproxen"],
        "clinical_purpose": "Reduces inflammatory pain, joint swelling, musculoskeletal discomfort, and fever.",
        "mechanism": "Inhibits cyclooxygenase (COX-1 and COX-2) enzymes, decreasing inflammatory prostaglandin synthesis.",
        "precautions": [
            "Take with food or milk to minimize gastric mucosal irritation.",
            "Contraindicated in active peptic ulcer disease, severe renal insufficiency, or gastrointestinal bleeding.",
            "WARNING: Do NOT take in suspected Dengue fever or other bleeding disorders due to platelet inhibition and hemorrhagic risk."
        ],
        "common_side_effects": ["Dyspepsia, epigastric pain, nausea, fluid retention, elevated blood pressure."],
        "key_interactions": ["Aspirin/Anticoagulants (bleeding risk)", "ACE inhibitors (reduced antihypertensive efficacy, renal risk)", "Lithium"],
        "tags": ["joint pain", "swelling", "inflammation", "muscle pain", "headache", "arthritis"]
    },
    {
        "drug_class": "Proton Pump Inhibitors (PPIs)",
        "common_agents": ["Pantoprazole", "Omeprazole", "Esomeprazole"],
        "clinical_purpose": "Used in gastroesophageal reflux (GERD), gastritis, and prevention/healing of gastric and duodenal ulcers.",
        "mechanism": "Irreversibly blocks the H+/K+ ATPase pump in gastric parietal cells, significantly decreasing stomach acid secretion.",
        "precautions": [
            "Usually taken 30-60 minutes before the first meal of the day as directed by a healthcare provider.",
            "Long-term unmonitored use may impair absorption of vitamin B12, magnesium, and calcium.",
            "Consult physician if symptoms fail to improve after 14 days."
        ],
        "common_side_effects": ["Headache, mild diarrhea or constipation, abdominal flatulence."],
        "key_interactions": ["Clopidogrel (variable interaction depending on agent)", "Iron supplements (reduced iron absorption due to reduced acidity)"],
        "tags": ["acidity", "gerd", "heartburn", "acid reflux", "stomach pain", "ulcer"]
    },
    {
        "drug_class": "Second-Generation Non-Sedating Antihistamines",
        "common_agents": ["Cetirizine", "Loratadine", "Fexofenadine"],
        "clinical_purpose": "Alleviates allergic rhinitis, sneezing, runny nose, itchy watery eyes, and urticaria (hives).",
        "mechanism": "Selective peripheral H1-receptor antagonist that blocks histamine-mediated allergic cascades.",
        "precautions": [
            "While largely non-sedating, Cetirizine can still cause mild drowsiness in certain sensitive individuals.",
            "Exercise caution when operating machinery or driving until personal tolerance is established.",
            "Avoid concomitant alcohol consumption."
        ],
        "common_side_effects": ["Mild drowsiness, dry mouth, headache, fatigue."],
        "key_interactions": ["CNS depressants and sedatives (additive somnolence)"],
        "tags": ["allergy", "sneezing", "runny nose", "itching", "rash", "hives", "cold"]
    },
    {
        "drug_class": "Expectorants & Mucolytics",
        "common_agents": ["Guaifenesin", "Ambroxol"],
        "clinical_purpose": "Assists in loosening and thinning mucus and phlegm in the respiratory tract to ease coughing it up.",
        "mechanism": "Increases bronchial secretion volume and decreases mucus viscosity.",
        "precautions": [
            "Must be accompanied by high daily water and warm fluid intake to facilitate mucus clearance.",
            "If cough persists for more than 2-3 weeks or is accompanied by blood, evaluate with a physician immediately."
        ],
        "common_side_effects": ["Mild nausea, stomach upset, dizziness."],
        "key_interactions": ["Generally minimal; avoid combination cough syrups with duplicate ingredients."],
        "tags": ["cough", "phlegm", "mucus", "chest congestion", "bronchitis"]
    },
    {
        "drug_class": "Oral Rehydration Therapy",
        "common_agents": ["Oral Rehydration Salts (WHO Formulation)"],
        "clinical_purpose": "Prevents and treats dehydration resulting from diarrhea, vomiting, or excessive perspiration.",
        "mechanism": "Utilizes sodium-glucose coupled transport across the intestinal brush border to maximize water and electrolyte absorption.",
        "precautions": [
            "Dissolve in the exact specified volume of clean drinking water; never boil or concentrate the prepared solution.",
            "Discard prepared solution after 24 hours."
        ],
        "common_side_effects": ["None when reconstituted accurately."],
        "key_interactions": ["None significant."],
        "tags": ["diarrhea", "vomiting", "dehydration", "gastroenteritis", "stomach bug"]
    }
]

@router.post("/info")
def get_medication_information(req: MedicationInfoRequest, current_user: User = Depends(get_current_user)):
    """
    Feature 8: Symptom-Based Medication Educational Information.
    Explains relevant drug classes, purposes, precautions, side effects, and interactions.
    Strictly educational: NEVER prescribes medications or dosages.
    """
    query = (req.symptoms_or_condition + " " + (req.medication_name or "")).lower()
    sources = search_medical_knowledge(query, max_results=3)
    citations = get_sources_citation_list(sources)

    matched_classes = []
    for item in MEDICATION_EDUCATIONAL_DATABASE:
        score = 0
        for tag in item["tags"]:
            if tag in query:
                score += 2
        for agent in item["common_agents"]:
            if agent.lower() in query:
                score += 5
        if score > 0:
            matched_classes.append(item)

    if not matched_classes:
        # Provide general baseline educational classes
        matched_classes = [MEDICATION_EDUCATIONAL_DATABASE[0], MEDICATION_EDUCATIONAL_DATABASE[3]]

    return {
        "query": req.symptoms_or_condition,
        "educational_medication_info": matched_classes,
        "critical_safety_rules": [
            "NEVER take prescription medications without a verified prescription from a licensed doctor.",
            "DO NOT alter or stop existing prescribed treatments without consulting your physician.",
            "Dosages depend strictly on age, weight, kidney/liver function, and pregnancy status and must be calculated by a doctor.",
            "Always disclose all vitamins, herbs, and over-the-counter supplements to your doctor to prevent adverse interactions."
        ],
        "medical_sources": citations,
        "mandatory_disclaimer": "⚠️ STRICT DISCLAIMER: This information is for general educational purposes only. Smart Health AI does NOT prescribe medications, dosages, or regimens. Consult your licensed physician or pharmacist for clinical treatment."
    }
