import re
from typing import Dict, Any, List

# Emergency Red-Flag Keyword Patterns and Clinical Rules
RED_FLAG_RULES = [
    {
        "id": "cardiac_emergency",
        "keywords": [
            r"chest pain", r"crushing pain", r"pressure in chest", r"pain radiating to (left arm|jaw|neck|back)",
            r"heart attack", r"chest tightness with sweating"
        ],
        "warning": "CRITICAL: Symptoms suggest possible acute cardiac event (such as Acute Coronary Syndrome / Heart Attack).",
        "action": "Call emergency services (911 / 112) or go to the nearest emergency department immediately.",
        "level": "EMERGENCY"
    },
    {
        "id": "stroke_fast",
        "keywords": [
            r"facial droop", r"face drooping", r"slurred speech", r"cannot speak", r"weakness on one side",
            r"arm numbness", r"sudden loss of balance", r"sudden vision loss", r"confusion"
        ],
        "warning": "CRITICAL: Symptoms match FAST criteria for suspected acute ischemic or hemorrhagic stroke.",
        "action": "Immediate medical emergency! Every minute counts. Call 911 / 112 immediately.",
        "level": "EMERGENCY"
    },
    {
        "id": "respiratory_distress",
        "keywords": [
            r"cannot breathe", r"severe shortness of breath", r"gasping for air", r"lips turning blue",
            r"stridor", r"cyanosis", r"suffocating"
        ],
        "warning": "CRITICAL: Severe respiratory failure or airway compromise detected.",
        "action": "Call emergency services immediately. Keep upright and do not leave patient alone.",
        "level": "EMERGENCY"
    },
    {
        "id": "anaphylaxis",
        "keywords": [
            r"throat swelling", r"tongue swelling", r"swollen airway", r"anaphylaxis", r"severe allergic reaction",
            r"wheezing after eating (peanuts|shellfish|eggs)"
        ],
        "warning": "CRITICAL: Signs of severe systemic allergic reaction (Anaphylaxis).",
        "action": "Administer intramuscular Epinephrine (EpiPen) if prescribed, and call emergency services immediately.",
        "level": "EMERGENCY"
    },
    {
        "id": "severe_hemorrhage",
        "keywords": [
            r"coughing (up )?blood", r"hemoptysis", r"vomiting blood", r"black tarry stools",
            r"uncontrolled bleeding", r"spurting blood"
        ],
        "warning": "CRITICAL: Internal or severe active hemorrhage suspected.",
        "action": "Seek immediate emergency trauma / critical care evaluation.",
        "level": "EMERGENCY"
    },
    {
        "id": "meningitis_sepsis",
        "keywords": [
            r"stiff neck with high fever", r"fever and neck stiffness", r"petechial rash with fever",
            r"unresponsive with fever"
        ],
        "warning": "CRITICAL: Severe neurological infection (e.g. Meningitis) or systemic sepsis suspected.",
        "action": "Immediate emergency room hospital evaluation required.",
        "level": "EMERGENCY"
    }
]

URGENT_RULES = [
    {
        "id": "high_fever",
        "keywords": [r"fever (above|over|>) 103", r"fever for (more than|over) 3 days", r"persistent fever"],
        "warning": "High or prolonged fever requiring prompt medical assessment within 12-24 hours.",
        "level": "URGENT"
    },
    {
        "id": "severe_dehydration",
        "keywords": [r"cannot keep fluids down", r"no urine for 12 hours", r"severe vomiting"],
        "warning": "Risk of acute dehydration and electrolyte disturbance.",
        "level": "URGENT"
    },
    {
        "id": "acute_localized_pain",
        "keywords": [r"severe right lower quadrant abdominal pain", r"appendix pain", r"severe testicular pain"],
        "warning": "Acute abdominal or surgical abdomen signs requiring urgent evaluation.",
        "level": "URGENT"
    }
]

def evaluate_emergency_triage(text: str) -> Dict[str, Any]:
    """
    Independent Rule-Based Emergency Triage Evaluator.
    Runs deterministically on patient text before and alongside LLM output.
    """
    clean_text = text.lower()
    triggered_warnings = []
    highest_level = "ROUTINE"
    recommended_action = "Schedule an evaluation with your physician or healthcare provider."

    # Check emergency red flags
    for rule in RED_FLAG_RULES:
        for kw in rule["keywords"]:
            if re.search(r"\b" + kw + r"\b", clean_text, re.IGNORECASE):
                triggered_warnings.append({
                    "id": rule["id"],
                    "level": rule["level"],
                    "warning": rule["warning"],
                    "action": rule["action"]
                })
                highest_level = "EMERGENCY"
                recommended_action = rule["action"]
                break

    # If no emergency, check urgent rules
    if highest_level != "EMERGENCY":
        for rule in URGENT_RULES:
            for kw in rule["keywords"]:
                if re.search(r"\b" + kw + r"\b", clean_text, re.IGNORECASE):
                    triggered_warnings.append({
                        "id": rule["id"],
                        "level": rule["level"],
                        "warning": rule["warning"],
                        "action": "Visit an urgent care center or consult a physician within 12-24 hours."
                    })
                    highest_level = "URGENT"
                    recommended_action = "Seek medical assessment within 12-24 hours."
                    break

    is_emergency = highest_level == "EMERGENCY"
    is_urgent = highest_level == "URGENT"

    return {
        "is_emergency": is_emergency,
        "is_urgent": is_urgent,
        "triage_level": highest_level,
        "warnings": triggered_warnings,
        "recommended_action": recommended_action,
        "emergency_contacts": {
            "US": "911",
            "UK": "999 / 111",
            "India": "112 / 108",
            "Europe": "112"
        }
    }
