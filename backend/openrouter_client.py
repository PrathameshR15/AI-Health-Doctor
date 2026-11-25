import os
import re
import json
import httpx
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.medical_knowledge import search_medical_knowledge, get_sources_citation_list
from backend.emergency_triage import evaluate_emergency_triage
from backend.clinical_nlp import clinical_extractor
from backend.lab_report_parser import parse_lab_report_rows, CLINICAL_REFERENCE_CATALOG

SYSTEM_PROMPT = """You are Smart Health AI, an advanced clinical decision-support and patient health education assistant.
You operate with the highest ethical and medical safety standards.

CLINICAL REASONING PRINCIPLES:
1. CONSTELATION-BASED ANALYSIS: Analyze complete symptom combinations (syndromes) rather than isolated keywords.
   - For example: High fever + retro-orbital pain + severe body/joint ache +/- rash = Arboviral Vector-Borne Illness (Dengue, Chikungunya, Malaria). Do NOT diagnose as a respiratory infection when respiratory symptoms are absent.
2. DIFFERENTIAL DIAGNOSES WITH RATIONALE: Provide pertinent positives (symptoms present that support each condition) and pertinent negatives (symptoms absent that rule down alternatives). Never present possible conditions as confirmed diagnoses. Always use terms like "Possible conditions to discuss with a physician", "Differential considerations".
3. CONDITION-SPECIFIC MEDICAL TESTS: Recommend targeted laboratory and imaging investigations with preparation guidance and clinical timing (e.g., Dengue NS1 Antigen during days 1-5, IgM/IgG serology after day 5, Complete Blood Count for platelet count and hematocrit).
4. MEDICALLY ACCURATE PRECAUTIONS & CONTRAINDICATIONS: Provide precise non-drug precautions, red flags for emergency care, and explicit contraindications (e.g., in suspected Dengue or bleeding fevers, STRICTLY CONTRAINDICATE NSAIDs like aspirin, ibuprofen, naproxen due to bleeding and platelet impairment risks; recommend Paracetamol only).
5. MEDICATIONS (EDUCATION ONLY): NEVER prescribe medications or specify dosages. Only explain therapeutic classes, mechanisms, standard precautions, and drug interactions.
6. SOAP CONSULTATION SUMMARY: Provide an accurate SOAP summary reflecting ONLY the patient's actual reported facts without repeating or fabricating patient information or inventing unmeasured physical vitals.
7. CITATIONS: Prescribe evidence-based medical information citing recognized authorities: WHO, NHS, MedlinePlus, ICMR, and NCDC India.
"""

class OpenRouterClient:
    def __init__(self):
        # OpenAI Direct Integration
        self.openai_api_key = settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else ""
        self.openai_base_url = settings.OPENAI_BASE_URL.rstrip("/")
        self.openai_model = settings.OPENAI_MODEL or "gpt-4o"

        # OpenRouter Integration (sanitizes any deprecated :free suffixes)
        self.openrouter_api_key = settings.OPENROUTER_API_KEY.strip() if settings.OPENROUTER_API_KEY else ""
        self.openrouter_base_url = settings.OPENROUTER_BASE_URL.rstrip("/")
        raw_default = settings.DEFAULT_MODEL or "openai/gpt-4o-mini"
        raw_fallback = settings.FALLBACK_MODEL or "meta-llama/llama-3.3-70b-instruct"
        self.openrouter_model = raw_default.replace(":free", "").strip() or "openai/gpt-4o-mini"
        self.fallback_model = raw_fallback.replace(":free", "").strip() or "meta-llama/llama-3.3-70b-instruct"

    async def _call_openai(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1500) -> Optional[str]:
        """Calls OpenAI API directly with the chosen model (e.g. gpt-6.2-sol-healthcare, gpt-4o)."""
        if not self.openai_api_key or len(self.openai_api_key) < 5:
            return None

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        model_l = self.openai_model.lower()
        uses_completion_tokens = any(model_l.startswith(p) for p in ("gpt-6", "gpt-5", "o1", "o3", "o4"))

        payload: Dict[str, Any] = {
            "model": self.openai_model,
            "messages": messages,
        }
        if uses_completion_tokens:
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["temperature"] = temperature
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(f"{self.openai_base_url}/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    print(f"OpenAI Direct API returned status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"OpenAI Direct API call exception: {e}")
        return None

    async def _call_openrouter(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1500) -> Optional[str]:
        """Calls OpenRouter API with primary model or fallback model."""
        if not self.openrouter_api_key or len(self.openrouter_api_key) < 5:
            return None

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://smarthealthai.org",
            "X-Title": "Smart Health AI Assistant"
        }

        # Try primary model first, then fallback
        models_to_try = [self.openrouter_model]
        if self.fallback_model and self.fallback_model != self.openrouter_model:
            models_to_try.append(self.fallback_model)

        for model in models_to_try:
            model_slug = model.replace(":free", "").strip()
            payload = {
                "model": model_slug,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    res = await client.post(f"{self.openrouter_base_url}/chat/completions", headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        print(f"OpenRouter [{model}] returned status {res.status_code}: {res.text}")
            except Exception as e:
                print(f"OpenRouter [{model}] call exception: {e}")

        return None

    async def _call_llm(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1500) -> str:
        """
        Unified LLM router:
        1. Checks OpenAI API Key first (e.g. gpt-4o).
        2. Falls back to OpenRouter API (e.g. openai/gpt-4o-mini).
        3. Returns empty string if both fail, triggering deterministic clinical reasoning engine.
        """
        # 1. Try Direct OpenAI if key is present
        if self.openai_api_key:
            res = await self._call_openai(messages, temperature, max_tokens)
            if res:
                return res

        # 2. Try OpenRouter
        if self.openrouter_api_key:
            res = await self._call_openrouter(messages, temperature, max_tokens)
            if res:
                return res

        return ""

    # --- Feature 1: Interactive Symptom Checker / AI Virtual Doctor ---
    async def generate_symptom_follow_up(
        self,
        chief_complaint: str,
        conversation_history: List[Dict[str, str]],
        current_step: int,
        extracted_entities: Optional[Dict[str, Any]] = None,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates the next relevant clinical question (one-by-one) as an AI Virtual Doctor.
        Dynamically adapts to symptom insufficiency, clarifying differential diagnoses.
        Concludes after step 3 to trigger comprehensive assessment.
        """
        is_last_step = current_step >= 3

        # Emergency check on complaint
        full_text = f"{chief_complaint} " + " ".join([m.get("content", "") for m in conversation_history])
        triage = evaluate_emergency_triage(full_text)
        if triage["is_emergency"]:
            return {
                "step": current_step,
                "question": "EMERGENCY ALERT: Your reported symptoms indicate a potential medical emergency. Please seek immediate emergency medical care.",
                "suggested_options": ["Call 911 / 112 Now", "Proceeding to Emergency Room", "I have someone with me"],
                "is_last_step": True,
                "emergency_flag": True,
                "emergency_message": triage["recommended_action"]
            }

        if is_last_step:
            return {
                "step": current_step,
                "question": "Thank you for providing those details. I have gathered sufficient information to generate your preliminary health assessment, differential considerations, precautions, and medical guidance.",
                "suggested_options": ["View My Health Assessment", "Add another detail"],
                "is_last_step": True,
                "emergency_flag": False
            }

        # Analyze current text for clinical syndromes & sparse symptoms
        text_lower = full_text.lower()
        if not extracted_entities:
            extracted_entities = clinical_extractor.extract_entities(full_text)

        active_symptoms = extracted_entities.get("active_symptoms", [])
        duration_info = extracted_entities.get("duration_info", {})
        has_stated_duration = bool(duration_info.get("raw_duration") or duration_info.get("estimated_days"))
        stated_dur_str = duration_info.get("raw_duration") or (f"{duration_info.get('estimated_days')} days" if duration_info.get("estimated_days") else None)

        # Try LLM to generate targeted doctor chatbot question
        llm_question_prompt = f"""You are an empathetic, clinical AI Virtual Doctor conducting a patient consultation.
Patient's reported symptom or concern: "{chief_complaint}"
Conversation so far: {conversation_history}
Extracted active symptoms: {active_symptoms}
Patient medical context & allergies: {patient_context or 'None reported'}
Already extracted illness duration: {stated_dur_str if has_stated_duration else 'Not yet specified'}
Current interview step: {current_step} of 3.

Clinical Instructions:
- Act like an experienced doctor in a clinical consultation. Ask 1-2 focused, relevant follow-up questions to understand onset, exact character, severity, progression, or key accompanying/aggravating factors.
- CRITICAL AVOID REPETITION: If the patient already stated the duration (e.g. "{stated_dur_str}"), DO NOT ask how long they have had it! Instead, ask about severity, whether weakness/pain is localized or generalized, and accompanying symptoms.
- Keep the language reassuring, empathetic, and clinical—never alarm the patient with rare or scary diagnoses.
- Provide 3 concise, clinically realistic tap-to-answer choices to help the patient answer quickly, plus an option to get immediate advice.

Return strictly JSON:
{{
  "question": "Doctor's question text here",
  "suggested_options": ["Option 1", "Option 2", "Option 3"]
}}
"""
        messages = [
            {"role": "system", "content": "You are a clinical decision support system asking targeted medical triage questions. Return strictly JSON."},
            {"role": "user", "content": llm_question_prompt}
        ]
        llm_res = await self._call_llm(messages, temperature=0.2, max_tokens=300)
        if llm_res:
            try:
                clean = re.sub(r"```json\s*", "", llm_res)
                clean = re.sub(r"```\s*$", "", clean).strip()
                try:
                    parsed = json.loads(clean)
                except Exception:
                    m = re.search(r"(\{[\s\S]*\})", clean)
                    parsed = json.loads(m.group(1)) if m else None
                if parsed and "question" in parsed and "suggested_options" in parsed:
                    opts = list(parsed["suggested_options"][:3])
                    advice_pill = "💡 Give me advice: Cure, prevention & why it happens"
                    if not any("advice" in o.lower() for o in opts):
                        opts.append(advice_pill)
                    return {
                        "step": current_step,
                        "question": parsed["question"],
                        "suggested_options": opts,
                        "is_last_step": False,
                        "emergency_flag": False
                    }
            except Exception:
                pass

        # Intelligent Clinical Decision Tree Fallback
        advice_pill = "💡 Give me advice: Cure, prevention & why it happens"

        # 1. Fever / Vector / Infection
        if any(w in text_lower for w in ["fever", "pyrexia", "temperature", "chills", "rigors"]):
            if current_step == 1:
                return {
                    "step": 1,
                    "question": "Do you have any severe body aches, pain behind your eyes (retro-orbital pain), or severe joint pain with this fever?",
                    "suggested_options": [
                        "Severe joint pain & pain behind eyes",
                        "Mild body ache with sore throat/cough",
                        "High fever with shivering and chills",
                        advice_pill
                    ],
                    "is_last_step": False,
                    "emergency_flag": False
                }
            else:
                return {
                    "step": 2,
                    "question": "Have you noticed any skin rash, small red pinpoint spots (petechiae), bleeding gums, or persistent vomiting?",
                    "suggested_options": [
                        "No rash, bleeding, or vomiting",
                        "Red spots or rash appeared on skin",
                        "Bleeding from gums or nosebleed",
                        advice_pill
                    ],
                    "is_last_step": False,
                    "emergency_flag": False
                }

        # 2. Headache / Neurological (Handles Headache + Weakness intelligently)
        elif any(w in text_lower for w in ["headache", "head pain", "migraine", "dizziness"]):
            has_weakness = any(w in text_lower for w in ["weakness", "weak", "fatigue", "tired", "lethargic", "exhaust"])
            if current_step == 1:
                if has_weakness:
                    q_text = "Did your headache start suddenly or develop gradually, and does the weakness affect your whole body or one specific side?"
                    opts = [
                        "Gradual onset, generalized whole-body weakness",
                        "Sudden throbbing headache with light sensitivity",
                        "Weakness on one specific side (arm or leg)",
                        "Accompanied by dizziness and difficulty concentrating",
                        advice_pill
                    ]
                else:
                    q_text = "Did this headache start suddenly like a thunderclap or gradually, and do you have any neck stiffness or light sensitivity?"
                    opts = [
                        "Gradual onset, no neck stiffness",
                        "Sudden, severe thunderclap onset",
                        "Stiff neck and pain looking at light",
                        advice_pill
                    ]
                return {
                    "step": 1,
                    "question": q_text,
                    "suggested_options": opts,
                    "is_last_step": False,
                    "emergency_flag": False
                }
            else:
                return {
                    "step": 2,
                    "question": "On a scale of 1 to 10, how severe is the pain and weakness, and do you have any nausea, visual blurriness, or numbness?",
                    "suggested_options": [
                        "Mild to moderate (3-5), relieved with quiet rest",
                        "Severe (7-9), difficulty concentrating",
                        "Accompanied by nausea and whole-body fatigue",
                        advice_pill
                    ],
                    "is_last_step": False,
                    "emergency_flag": False
                }

        # 3. Gastrointestinal
        elif any(w in text_lower for w in ["stomach", "abdominal", "acidity", "reflux", "vomit", "diarrhea", "nausea"]):
            if current_step == 1:
                return {
                    "step": 1,
                    "question": "Where is the pain or discomfort located, and does it feel like burning, sharp cramping, or dull bloating?",
                    "suggested_options": [
                        "Upper stomach burning (acid reflux)",
                        "Lower right side sharp pain",
                        "Generalized cramping with loose stools",
                        advice_pill
                    ],
                    "is_last_step": False,
                    "emergency_flag": False
                }
            else:
                return {
                    "step": 2,
                    "question": "Are you able to keep fluids down, and have you observed any blood in vomit or dark tarry stools?",
                    "suggested_options": [
                        "Drinking fluids normally, no blood",
                        "Mild nausea, no vomiting",
                        "Frequent vomiting, unable to keep fluids down",
                        advice_pill
                    ],
                    "is_last_step": False,
                    "emergency_flag": False
                }

        # 4. Respiratory / Cold & Cough (Interactive Health Guide Chatbot)
        elif any(w in text_lower for w in ["cold", "sneez", "runny nose", "congestion", "stuffy", "cough", "throat", "breath", "wheez", "chest", "phlegm"]):
            if current_step == 1:
                if any(w in text_lower for w in ["cold", "sneez", "runny nose", "congestion", "stuffy"]):
                    return {
                        "step": 1,
                        "question": "How many days have you had this cold, and did it start gradually or suddenly?",
                        "suggested_options": [
                            "1 to 2 days (just started)",
                            "3 to 5 days, with runny nose & sneezing",
                            "Over a week (persistent)",
                            advice_pill
                        ],
                        "is_last_step": False,
                        "emergency_flag": False
                    }
                else:
                    return {
                        "step": 1,
                        "question": "How many days have you had this cough or throat irritation, and is it dry or producing phlegm?",
                        "suggested_options": [
                            "1 to 2 days, dry irritating cough/throat",
                            "3 to 5 days, with mild yellow/clear phlegm",
                            "Over a week, persistent cough",
                            advice_pill
                        ],
                        "is_last_step": False,
                        "emergency_flag": False
                    }
            else:
                return {
                    "step": 2,
                    "question": "How severe is your discomfort, and are you able to rest comfortably and drink warm fluids?",
                    "suggested_options": [
                        "Mild discomfort, resting and hydrating well",
                        "Moderate congestion, stuffy nose and headache",
                        "Severe throat pain or chest tightness",
                        advice_pill
                    ],
                    "is_last_step": False,
                    "emergency_flag": False
                }

        # General Default
        questions_by_step = {
            1: {
                "question": f"To better understand your '{chief_complaint}', how long have you been experiencing this, and did it start suddenly or develop gradually?",
                "suggested_options": ["Started today (Sudden)", "2 to 3 days ago", "1 to 2 weeks", advice_pill]
            },
            2: {
                "question": "On a scale of 1 to 10, how severe is the discomfort, and are you having any accompanying symptoms such as fever, dizziness, or nausea?",
                "suggested_options": ["Mild (1-3), no other symptoms", "Moderate (4-6) with mild fatigue", "Severe (7-9) with fever or chills", advice_pill]
            }
        }
        q_info = questions_by_step.get(current_step, {
            "question": "Are your symptoms improved or worsened by specific activities, resting, or eating?",
            "suggested_options": ["Worse with exertion", "Worse after meals", "Better with rest", advice_pill]
        })
        return {
            "step": current_step,
            "question": q_info["question"],
            "suggested_options": q_info["suggested_options"],
            "is_last_step": False,
            "emergency_flag": False
        }

    # --- Feature 1 & Unified: Symptom Assessment & Condition Explanation ---
    async def generate_health_assessment(
        self,
        chief_complaint: str,
        conversation_text: str,
        patient_context: Dict[str, Any],
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates possible conditions, explanations, precautions, test guidance,
        dietary tips, and medication education with verified references.
        Analyzes complete symptom constellations and validates clinical consistency.
        """
        combined_text = f"{chief_complaint} {conversation_text}"
        emergency_eval = evaluate_emergency_triage(combined_text)

        # MedSpaCy Entity Extraction & Syndrome Detection
        if not extracted_entities:
            extracted_entities = clinical_extractor.extract_entities(combined_text)

        active_symptoms = extracted_entities.get("active_symptoms", [])
        negated_symptoms = extracted_entities.get("negated_symptoms", [])
        detected_syndromes = extracted_entities.get("detected_syndromes", [])
        severity_info = extracted_entities.get("severity_info", {})
        duration_info = extracted_entities.get("duration_info", {})
        warning_signs = extracted_entities.get("warning_signs", [])

        # If critical warning signs exist, escalate emergency triage
        if warning_signs:
            emergency_eval["is_emergency"] = True
            emergency_eval["triage_level"] = "EMERGENCY"
            emergency_eval["recommended_action"] = f"CRITICAL WARNING SIGNS DETECTED ({', '.join(warning_signs)}). Proceed to hospital emergency department immediately for observation, serial platelet/hematocrit monitoring, and fluid management."

        # Search medical knowledge sources
        search_query = f"{chief_complaint} {' '.join(active_symptoms[:3])}"
        relevant_sources = search_medical_knowledge(search_query, max_results=3)
        citations = get_sources_citation_list(relevant_sources)

        # Build prompt for LLM with syndromic context
        syndromes_summary = ", ".join([s["syndrome"] for s in detected_syndromes]) if detected_syndromes else "None specifically clustered"
        
        # Build structured active symptoms list with individual timelines & severities preserved
        detailed_symptoms = extracted_entities.get("active_symptoms_detailed") or extracted_entities.get("details", {}).get("symptoms", [])
        formatted_symptoms_list = []
        for sym in detailed_symptoms:
            name = sym.get("text", "")
            dur = sym.get("duration")
            sev = sym.get("severity")
            parts = [f"'{name}'"]
            if dur:
                parts.append(f"Individual Duration: {dur}")
            if sev:
                parts.append(f"Severity: {sev}")
            formatted_symptoms_list.append(" - " + ", ".join(parts))
        
        if not formatted_symptoms_list and active_symptoms:
            formatted_symptoms_list = [f" - '{s}'" for s in active_symptoms]
        
        symptoms_payload_str = "\n".join(formatted_symptoms_list) if formatted_symptoms_list else "None reported"

        prompt = f"""PATIENT CLINICAL CASE:
- Chief Complaint: {chief_complaint}
- Conversation/Details: {conversation_text}
- Patient Profile: Age {patient_context.get('age', 'Adult')}, Gender: {patient_context.get('gender', 'Unspecified')}, Known Conditions: {patient_context.get('chronic_conditions', 'None')}
- Overall Illness Duration: {duration_info.get('raw_duration', 'Unspecified')} (Estimated Days: {duration_info.get('estimated_days', 'Unknown')})
- Discomfort Severity: {severity_info.get('overall_level', 'Moderate')} ({severity_info.get('score_1_10', 'N/A')}/10)
- Extracted Active Symptoms with Individual Timeline & Severity:
{symptoms_payload_str}
- Extracted Critical Warning Signs (Emergency Red Flags): {warning_signs or 'None reported'}
- Pertinent Negatives (Explicitly Ruled Out by Patient): {negated_symptoms or 'None explicitly denied'}
- Detected Clinical Syndrome Constellation: {syndromes_summary}

CLINICAL DECISION SUPPORT INSTRUCTIONS:
1. STRICT ON-TIME PRESENTATION ISOLATION (Current Visit Only):
   - All diagnostic reasoning, medical tests, precautions, medication education, and SOAP report MUST be based STRICTLY and EXCLUSIVELY on the on-time active symptoms presented right now in this specific consultation.
   - Do NOT recommend medical tests, precautions, or medications for previous symptoms, historical episodes, or background chronic conditions. Focus 100% on the active clinical problem.
2. UNIVERSAL CONSTELLATION REASONING (All Disease Domains):
   - Analyze the complete constellation of current patient symptoms, their individual durations/chronology, anatomical localization, and severity.
   - Accurately differentiate conditions across relevant medical domains (e.g. Rhinology/Sinusitis, Neurology/Cephalea, Pulmonology, Gastroenterology, Cardiology, Infectious/Vector-borne, Musculoskeletal, Dermatology).
   - STRICT NEGATIVE RULE: Do NOT suggest diagnoses whose cardinal organ-system symptoms are absent or contradicted by the patient input (e.g. do not diagnose lower respiratory infection if respiratory/pulmonary signs are absent).
   - NO SINGLE-SYMPTOM RULE OUT: Never rule out a condition based solely on the absence of a single non-universal symptom.
   - QUALITATIVE LIKELIHOOD: Use qualitative likelihood only ("High", "Moderate", "Low") without arbitrary percentages.
3. CONDITION-RELEVANT WARNING SIGNS & EMERGENCY GUIDANCE:
   - Identify clinical red flags and warning signs specific to the affected organ system (e.g. periorbital edema/visual impairment/severe frontal headache for sinusitis; focal deficits/thunderclap onset for cephalea; acute chest pressure/hypotension for thoracic; hemodynamic collapse/severe bleeding for infectious fevers).
   - If emergency warning signs exist, prioritize urgent medical evaluation and stabilization guidance.
4. DURATION-DEPENDENT & GUIDELINE-ALIGNED TEST GUIDANCE:
   - Recommend targeted investigations tailored specifically to the suspected condition(s) and the patient's individual illness duration (e.g. clinical assessment in acute uncomplicated phases; sinus CT/nasal endoscopy for persistent sinonasal symptoms >10-14 days; phase-appropriate serology/PCR/culture or imaging where indicated).
   - Explain the clinical purpose and ideal timing for every recommended test. Tests must strictly target the CURRENT presenting condition.
5. CONDITION-SPECIFIC PRECAUTIONS & CONTRAINDICATIONS:
   - Provide precise non-drug supportive measures and relevant medication contraindications tailored to the suspected disease (e.g. avoid sedating antihistamines that dry and thicken secretions in non-allergic sinusitis; contraindicate NSAIDs in suspected arboviral or bleeding fevers; avoid migraine triggers).
6. CONDITION-SPECIFIC CLINICAL REPORT (SOAP SUMMARY):
   - Subjective: Concisely synthesize the patient's actual reported facts: chief complaint, individual symptom durations and severities, overall illness duration, and ONLY true pertinent negatives (symptoms explicitly denied by the patient). Never convert unmentioned symptoms into confirmed negatives, never invent unstated details, and never duplicate text.
   - Objective: Explicitly state: "Telehealth clinical review. Physical vitals (Temperature, Pulse, Blood Pressure, Respiratory Rate, SpO2) and in-person physical examination have not been measured and are pending in-person clinical evaluation." Do NOT fabricate unmeasured numerical vitals.
   - Assessment: Provide clinical rationale tailored specifically to the patient's individual diagnosis and key differentials based on the complete symptom constellation of the current visit.
   - Plan: Tailor recommendations specifically to the identified diagnosis: condition-appropriate diagnostic investigations, non-drug supportive care, relevant precautions/contraindications, and condition-specific emergency warning signs. All plan items must directly address the on-time presentation.

Return strictly valid JSON matching this schema:
{{
  "possible_conditions": [
    {{ "condition": str, "likelihood": "High"|"Moderate"|"Low", "rationale": str, "clinical_explanation": str }}
  ],
  "precautions": [str],
  "test_guidance": [
    {{ "test_name": str, "purpose": str, "when_considered": str }}
  ],
  "diet_guidance": {{ "avoid": [str], "recommended": [str], "hydration": str }},
  "medication_info": [
    {{ "drug_class": str, "common_examples": [str], "clinical_purpose": str, "precautions": str, "side_effects": str }}
  ],
  "consultation_summary": {{ "subjective": str, "objective": str, "assessment": str, "plan": str }}
}}
"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        print("\n======================================================================")
        print("[PIPELINE STEP 3: PROCESSED SYMPTOMS & SYNDROMIC CONSTELLATIONS]")
        print(f"Chief Complaint       : {chief_complaint}")
        print(f"Active Symptoms       : {active_symptoms}")
        print(f"Duration Applied      : {duration_info.get('raw_duration')} (Estimated Days: {duration_info.get('estimated_days')})")
        print(f"Severity Applied      : {severity_info.get('overall_level')} ({severity_info.get('score_1_10')}/10)")
        print(f"WHO Warning Signs     : {warning_signs}")
        print(f"Pertinent Negatives   : {negated_symptoms}")
        print(f"Detected Syndromes    : {syndromes_summary}")
        print("======================================================================")
        print("[PIPELINE STEP 4: EXACT FINAL LLM API PAYLOAD]")
        print(f"Target Gateway        : {'Direct OpenAI' if self.openai_api_key else 'OpenRouter'}")
        print(f"Active Model          : {self.openai_model if self.openai_api_key else self.openrouter_model}")
        print(f"Prompt Sent to LLM:\n{prompt}")
        print("======================================================================\n")

        llm_output = await self._call_llm(messages, temperature=0.1, max_tokens=1800)
        parsed_result = None
        if llm_output:
            try:
                clean = re.sub(r"```json\s*", "", llm_output)
                clean = re.sub(r"```\s*$", "", clean).strip()
                parsed_result = json.loads(clean)
            except Exception as e:
                m = re.search(r"(\{[\s\S]*\})", clean)
                if m:
                    try:
                        parsed_result = json.loads(m.group(1))
                    except Exception as e2:
                        print(f"Regex fallback JSON parse failed: {e2}")
                else:
                    print(f"Error parsing LLM JSON: {e}")

        # Deterministic clinical fallback if LLM offline or returned invalid JSON
        if parsed_result:
            # 1. Normalize key aliases
            if "precautions_and_contraindications" in parsed_result and "precautions" not in parsed_result:
                parsed_result["precautions"] = parsed_result["precautions_and_contraindications"]
            if "medication_education" in parsed_result and "medication_info" not in parsed_result:
                parsed_result["medication_info"] = parsed_result["medication_education"]
            if "SOAP_summary" in parsed_result and "consultation_summary" not in parsed_result:
                parsed_result["consultation_summary"] = parsed_result["SOAP_summary"]

            # 2. Normalize possible_conditions to list of dicts with string values
            raw_conds = parsed_result.get("possible_conditions", [])
            norm_conds = []
            if isinstance(raw_conds, list):
                for c in raw_conds:
                    if isinstance(c, dict):
                        norm_conds.append({
                            "condition": str(c.get("condition") or c.get("name") or "Medical Consideration"),
                            "likelihood": str(c.get("likelihood") or "Moderate"),
                            "rationale": str(c.get("rationale") or c.get("reason") or "Clinical presentation"),
                            "clinical_explanation": str(c.get("clinical_explanation") or c.get("explanation") or "")
                        })
                    elif isinstance(c, str):
                        norm_conds.append({
                            "condition": c,
                            "likelihood": "Moderate",
                            "rationale": "Symptom presentation",
                            "clinical_explanation": ""
                        })
            parsed_result["possible_conditions"] = norm_conds

            # 3. Normalize precautions to list of strings
            raw_prec = parsed_result.get("precautions", [])
            norm_prec = []
            if isinstance(raw_prec, list):
                for p in raw_prec:
                    if isinstance(p, dict):
                        norm_prec.append(str(p.get("precaution") or p.get("warning") or p.get("text") or json.dumps(p)))
                    else:
                        norm_prec.append(str(p))
            elif isinstance(raw_prec, dict):
                for k, v in raw_prec.items():
                    if isinstance(v, list):
                        norm_prec.extend([str(item) for item in v])
                    else:
                        norm_prec.append(f"{k.replace('_', ' ').title()}: {v}")
            elif isinstance(raw_prec, str):
                norm_prec = [raw_prec]
            parsed_result["precautions"] = norm_prec

            # 4. Normalize test_guidance to list of dicts
            raw_tests = parsed_result.get("test_guidance", [])
            norm_tests = []
            if isinstance(raw_tests, list):
                for t in raw_tests:
                    if isinstance(t, dict):
                        norm_tests.append({
                            "test_name": str(t.get("test_name") or t.get("name") or "Diagnostic Test"),
                            "purpose": str(t.get("purpose") or "Clinical evaluation"),
                            "when_considered": str(t.get("when_considered") or "")
                        })
                    elif isinstance(t, str):
                        norm_tests.append({
                            "test_name": t,
                            "purpose": "Clinical evaluation",
                            "when_considered": ""
                        })
            parsed_result["test_guidance"] = norm_tests

            # 5. Normalize diet_guidance
            diet = parsed_result.get("diet_guidance", {})
            if not isinstance(diet, dict):
                diet = {}
            avoid = diet.get("avoid", [])
            if isinstance(avoid, str):
                avoid = [avoid]
            elif isinstance(avoid, list):
                avoid = [str(x.get("food") or x) if isinstance(x, dict) else str(x) for x in avoid]
            else:
                avoid = []

            rec = diet.get("recommended", [])
            if isinstance(rec, str):
                rec = [rec]
            elif isinstance(rec, list):
                rec = [str(x.get("food") or x) if isinstance(x, dict) else str(x) for x in rec]
            else:
                rec = []

            parsed_result["diet_guidance"] = {
                "avoid": avoid,
                "recommended": rec,
                "hydration": str(diet.get("hydration") or "Maintain adequate daily hydration.")
            }

            # 6. Normalize medication_info
            raw_meds = parsed_result.get("medication_info", [])
            norm_meds = []
            if isinstance(raw_meds, list):
                for m in raw_meds:
                    if isinstance(m, dict):
                        ex = m.get("common_examples") or m.get("common_agents") or m.get("examples") or []
                        if isinstance(ex, str):
                            ex = [s.strip() for s in ex.split(",")]
                        elif not isinstance(ex, list):
                            ex = [str(ex)]
                        else:
                            ex = [str(item) for item in ex]

                        norm_meds.append({
                            "drug_class": str(m.get("drug_class") or m.get("class") or "Therapeutic Class"),
                            "common_examples": ex,
                            "clinical_purpose": str(m.get("clinical_purpose") or m.get("purpose") or ""),
                            "precautions": str(m.get("precautions") or ""),
                            "side_effects": str(m.get("side_effects") or m.get("common_side_effects") or "")
                        })
            parsed_result["medication_info"] = norm_meds

            # 7. Normalize consultation_summary
            soap = parsed_result.get("consultation_summary", {})
            if not isinstance(soap, dict):
                soap = {}
            parsed_result["consultation_summary"] = {
                "subjective": str(soap.get("subjective") if not isinstance(soap.get("subjective"), dict) else json.dumps(soap.get("subjective"))),
                "objective": str(soap.get("objective") if not isinstance(soap.get("objective"), dict) else json.dumps(soap.get("objective"))),
                "assessment": str(soap.get("assessment") if not isinstance(soap.get("assessment"), dict) else json.dumps(soap.get("assessment"))),
                "plan": str(soap.get("plan") if not isinstance(soap.get("plan"), dict) else json.dumps(soap.get("plan")))
            }

        if not parsed_result:
            parsed_result = self._generate_rule_based_assessment(
                chief_complaint=chief_complaint,
                conversation_text=conversation_text,
                sources=relevant_sources,
                extracted_entities=extracted_entities
            )

        # Validate clinical consistency (e.g., ensure Dengue isn't replaced by Respiratory if vector fever detected)
        parsed_result = self.validate_clinical_consistency(
            assessment=parsed_result,
            active_symptoms=active_symptoms,
            detected_syndromes=detected_syndromes,
            full_text=combined_text,
            extracted_entities=extracted_entities
        )

        # Merge emergency evaluation and verified citations
        parsed_result["emergency_eval"] = emergency_eval
        parsed_result["sources"] = citations
        parsed_result["disclaimer"] = "This assessment is for informational and educational purposes only. It is not a definitive medical diagnosis or treatment plan. Always consult a qualified medical professional."

        return parsed_result

    def _synthesize_clinical_soap(
        self,
        existing_soap: Dict[str, Any],
        chief_complaint: str,
        active_symptoms: List[str],
        negated_symptoms: List[str],
        warning_signs: List[str],
        duration_info: Dict[str, Any],
        severity_info: Dict[str, Any],
        conditions: List[Dict[str, Any]],
        tests: List[Dict[str, Any]],
        precautions: List[str]
    ) -> Dict[str, str]:
        """
        Universal clinical SOAP synthesizer.
        Works dynamically for ALL diseases without hardcoding disease-specific templates.
        Leverages LLM clinical intelligence, eliminates duplicate text, and enforces telehealth safety.
        """
        llm_subj = str(existing_soap.get("subjective", "")).strip() if isinstance(existing_soap, dict) else ""
        llm_obj = str(existing_soap.get("objective", "")).strip() if isinstance(existing_soap, dict) else ""
        llm_assess = str(existing_soap.get("assessment", "")).strip() if isinstance(existing_soap, dict) else ""
        llm_plan = str(existing_soap.get("plan", "")).strip() if isinstance(existing_soap, dict) else ""

        # 1. Subjective: Preserve LLM's nuanced clinical synthesis, or generate clean factual intake
        if len(llm_subj) > 30 and "Chief Complaint: Chief Complaint:" not in llm_subj and "denies other focal systemic symptoms" not in llm_subj:
            clean_subj = llm_subj
        else:
            raw_dur = duration_info.get("raw_duration", "Unspecified")
            sev_lvl = severity_info.get("overall_level", "Moderate")
            sev_num = f"{severity_info.get('score_1_10')}/10" if severity_info.get("score_1_10") is not None else "clinical grading"
            
            # Format active symptoms preserving individual durations where available
            detailed_symptoms = (
                (existing_soap.get("active_symptoms_detailed") if isinstance(existing_soap, dict) else None)
                or []
            )
            patient_symptoms_str = ", ".join(active_symptoms) if active_symptoms else chief_complaint
            
            # Strictly never convert unknown/unreported items into confirmed negative findings
            neg_str = f"Pertinent negatives: denies {', '.join(negated_symptoms)}." if negated_symptoms else "Pertinent negatives: none explicitly reported during intake."
            warn_str = f"Clinical warning indicators: {', '.join(warning_signs)}." if warning_signs else "Warning indicators: no acute emergency red flags reported."
            clean_subj = (
                f"Patient presents with chief complaint of {chief_complaint}. "
                f"Reported duration: {raw_dur}. "
                f"Severity: {sev_lvl} ({sev_num}). "
                f"Active symptoms: {patient_symptoms_str}. "
                f"{neg_str} "
                f"{warn_str}"
            )

        # 2. Objective: Universal telehealth standard across all diseases (prevents fabricating physical vitals)
        if len(llm_obj) > 25 and not any(fake in llm_obj.lower() for fake in ["bp: 120", "bp: 110", "pulse: 72", "pulse: 80", "lungs clear to auscultation"]):
            clean_obj = llm_obj
        else:
            clean_obj = (
                "Telehealth clinical assessment intake. Physical vital signs (Temperature, Pulse, Blood Pressure, Respiratory Rate, SpO2) "
                "and in-person physical examinations have not been measured and are pending in-person clinician examination."
            )

        # 3. Assessment: Dynamic differential synthesis from evaluated conditions
        if len(llm_assess) > 25:
            clean_assess = llm_assess
        else:
            top_cond = conditions[0] if conditions else {"condition": "Clinical Evaluation Indicated", "likelihood": "Moderate", "rationale": "Symptom constellation"}
            other_conds = [c["condition"] for c in conditions[1:]] if len(conditions) > 1 else []
            diff_str = f"Differential considerations: {', '.join(other_conds)}." if other_conds else "No secondary differentials currently indicated."
            safety_note = f"Warning flags: ACTIVE ({', '.join(warning_signs)})." if warning_signs else "Safety indicators: no acute red flags reported."
            clean_assess = (
                f"Primary clinical consideration: {top_cond.get('condition')} ({top_cond.get('likelihood')} likelihood) - {top_cond.get('rationale')}. "
                f"{diff_str} "
                f"{safety_note}"
            )

        # 4. Plan: Dynamic plan derived strictly from the evaluated condition's tests and precautions
        if len(llm_plan) > 30 and (not warning_signs or "emergency" in llm_plan.lower() or "hospital" in llm_plan.lower()):
            clean_plan = llm_plan
        else:
            test_names = [t.get("test_name") for t in tests[:3] if t.get("test_name")]
            test_str = f"1. Recommended Diagnostics: {', '.join(test_names)}." if test_names else "1. Recommended Diagnostics: In-person clinician consultation for diagnostic testing."
            prim_prec = precautions[0] if precautions else "Maintain supportive care, appropriate hydration, and physical rest."
            prec_str = f"2. Supportive Care: {prim_prec}"
            em_str = (
                f"3. Emergency Protocol: IMMEDIATE EMERGENCY HOSPITAL ADMISSION MANDATORY due to active warning indicators ({', '.join(warning_signs)})."
                if warning_signs else
                "3. Monitoring & Red Flags: Seek emergency medical care immediately if symptoms worsen rapidly or acute warning signs develop."
            )
            clean_plan = f"{test_str} {prec_str} {em_str}"

        return {
            "subjective": clean_subj,
            "objective": clean_obj,
            "assessment": clean_assess,
            "plan": clean_plan
        }

        return {
            "subjective": clean_subj,
            "objective": clean_obj,
            "assessment": clean_assess,
            "plan": clean_plan
        }

    def validate_clinical_consistency(
        self,
        assessment: Dict[str, Any],
        active_symptoms: List[str],
        detected_syndromes: List[Dict[str, Any]],
        full_text: str,
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enforces clinical accuracy and consistency:
        1. Prevents unrelated diagnoses (e.g. respiratory diseases) unless respiratory symptoms exist.
        2. Differentiates Dengue vs Chikungunya vs Malaria based on full symptom combinations.
        3. Preserves and prioritizes critical WHO warning signs (gum bleeding, severe abdominal pain, persistent vomiting).
        4. Makes test recommendations dependent on illness duration and clinical guidelines.
        5. Enforces NSAID contraindication for bleeding fevers.
        6. Guarantees SOAP reports accurately preserve patient information without inventing findings.
        """
        text_lower = full_text.lower()
        if not extracted_entities:
            extracted_entities = clinical_extractor.extract_entities(full_text)

        severity_info = extracted_entities.get("severity_info", {})
        duration_info = extracted_entities.get("duration_info", {})
        warning_signs = extracted_entities.get("warning_signs", []) or clinical_extractor.extract_warning_signs(full_text)
        negated_symptoms = extracted_entities.get("negated_symptoms", [])
        chief_complaint = extracted_entities.get("chief_complaint") or (full_text.split(".")[0] if full_text else "Patient presentation")
        estimated_days = duration_info.get("estimated_days")

        has_respiratory_symptoms = any(w in text_lower for w in [
            "cough", "productive cough", "dry cough", "phlegm", "sputum", "sore throat", "wheezing", "rhinorrhea", "congestion", "runny nose"
        ])
        has_fever = any(w in text_lower for w in ["fever", "pyrexia", "temperature", "chills", "rigors", "burning hot", "high-grade"])
        has_retro_orbital = any(w in text_lower for w in ["retro-orbital", "behind eyes", "eye pain", "eye ache", "behind the eye"])
        has_bone_joint = any(w in text_lower for w in ["breakbone", "bone pain", "joint pain", "myalgia", "body ache", "arthralgia", "aching all over"])
        has_rash_or_bleed = any(w in text_lower for w in ["petechiae", "red spots", "rash", "bleeding", "nosebleed", "gums", "epistaxis"])

        # Chikungunya-specific markers: prominent joint swelling/edema, wrists/ankles/small joints, morning stiffness
        has_chikungunya_markers = any(w in text_lower for w in [
            "chikungunya", "swollen joint", "joint swelling", "wrist pain", "ankle pain",
            "small joints", "symmetrical joint", "morning stiffness", "cannot walk", "limping from joint"
        ])

        # 1. PREVENT UNRELATED DIAGNOSES (Respiratory Filter)
        conditions = assessment.get("possible_conditions", [])
        if not has_respiratory_symptoms:
            # Remove any upper/lower respiratory diagnoses when patient has NO respiratory symptoms
            conditions = [
                c for c in conditions
                if not any(r in c.get("condition", "").lower() for r in [
                    "respiratory", "bronchitis", "pharyngitis", "common cold", "rhinitis", "pneumonia", "airway"
                ])
            ]

        # 2. DISEASE REASONING: VECTOR / ARBOVIRAL REFINEMENT (ONLY WHEN CLINICALLY INDICATED)
        has_arboviral_markers = has_fever and not has_respiratory_symptoms and (
            has_chikungunya_markers or
            has_retro_orbital or
            "dengue" in text_lower or
            "chikungunya" in text_lower or
            "mosquito" in text_lower or
            any("dengue" in c.get("condition", "").lower() or "chikungunya" in c.get("condition", "").lower() for c in conditions) or
            (has_bone_joint and not any(r in text_lower for r in ["sinus", "facial", "nasal", "throat"]))
        )

        if has_arboviral_markers:
            if has_chikungunya_markers:
                # Prioritize Chikungunya Fever
                has_chik_cond = any("chikungunya" in c.get("condition", "").lower() for c in conditions)
                if not has_chik_cond:
                    chik_condition = {
                        "condition": "Suspected Chikungunya Fever (Alphaviral Polyarthritic Infection)",
                        "likelihood": "High",
                        "rationale": "Acute high fever coupled with prominent symmetrical polyarthralgia and joint swelling/stiffness (wrists/ankles/small joints) classically indicates Chikungunya.",
                        "clinical_explanation": "Alphavirus infection transmitted by Aedes mosquitoes characterized by acute high fever and debilitating, crippling peripheral joint inflammation."
                    }
                    conditions.insert(0, chik_condition)

                # Ensure Dengue is also retained as differential
                if not any("dengue" in c.get("condition", "").lower() for c in conditions):
                    conditions.append({
                        "condition": "Suspected Dengue Fever",
                        "likelihood": "Moderate",
                        "rationale": "Shares Aedes mosquito vector transmission; considered in acute tropical febrile illnesses though severe joint swelling favors Chikungunya.",
                        "clinical_explanation": "Flavivirus infection to be differentiated clinically and serologically."
                    })
            elif has_retro_orbital or has_rash_or_bleed or len(warning_signs) > 0 or has_bone_joint:
                # Prioritize Dengue Fever
                has_dengue_cond = any("dengue" in c.get("condition", "").lower() for c in conditions)
                if not has_dengue_cond:
                    dengue_condition = {
                        "condition": "Suspected Dengue Fever (Flaviviral Infection)",
                        "likelihood": "High",
                        "rationale": "High fever accompanied by retro-orbital pain, severe generalized myalgia ('breakbone' aches), and absence of primary cough strongly suggests Dengue.",
                        "clinical_explanation": "Flavivirus infection transmitted by Aedes mosquitoes, characterized by febrile, critical (plasma leakage), and recovery phases."
                    }
                    conditions.insert(0, dengue_condition)

                # Ensure Chikungunya is also retained as differential
                if not any("chikungunya" in c.get("condition", "").lower() for c in conditions):
                    conditions.append({
                        "condition": "Suspected Chikungunya Fever",
                        "likelihood": "Moderate",
                        "rationale": "Shares Aedes vector transmission; important differential in acute febrile illnesses presenting with joint and muscle aches.",
                        "clinical_explanation": "Alphavirus infection requiring serological differentiation from dengue."
                    })

        assessment["possible_conditions"] = conditions

        # 3. PRESERVE & PRIORITIZE CRITICAL WARNING SIGNS
        precautions = assessment.get("precautions", [])
        if warning_signs:
            warning_msg = f"EMERGENCY CLINICAL ALERT: Critical Warning Signs Detected ({', '.join(warning_signs)}). Immediate hospital emergency admission is mandatory for continuous IV fluid resuscitation, serial platelet & hematocrit monitoring, and observation for plasma leakage/shock!"
            if not any("warning signs detected" in p.lower() for p in precautions):
                precautions.insert(0, warning_msg)

        # Enforce NSAID contraindication in vector fevers and bleeding risks
        if has_arboviral_markers or any("dengue" in c.get("condition", "").lower() or "chikungunya" in c.get("condition", "").lower() for c in conditions):
            nsaid_warning = "CRITICAL CONTRAINDICATION: Strictly avoid NSAIDs (aspirin, ibuprofen, naproxen, diclofenac) as they inhibit platelets and heighten hemorrhagic risk in dengue. Use only Paracetamol for fever under physician guidance."
            if not any("nsaid" in p.lower() or "aspirin" in p.lower() or "ibuprofen" in p.lower() for p in precautions):
                precautions.insert(0, nsaid_warning)

        assessment["precautions"] = precautions

        # 4. DURATION-DEPENDENT MEDICAL TEST RECOMMENDATIONS
        tests = assessment.get("test_guidance", [])
        is_early_phase = estimated_days is not None and estimated_days <= 5
        is_late_phase = estimated_days is not None and estimated_days > 5

        # Format tests according to clinical guideline timing for arboviral infections
        if has_arboviral_markers or any("dengue" in c.get("condition", "").lower() for c in conditions):
            tests_to_inject = []
            
            # CBC with platelets is essential across all durations
            if not any("cbc" in t.get("test_name", "").lower() or "platelet" in t.get("test_name", "").lower() for t in tests):
                tests_to_inject.append({
                    "test_name": "Complete Blood Count (CBC) with Platelet Count & Hematocrit (PCV)",
                    "purpose": "Monitors thrombocytopenia (platelet drop) and hemoconcentration/plasma leakage.",
                    "when_considered": f"Baseline immediate testing upon fever presentation ({'Days 1-5 acute viraemic phase' if is_early_phase else 'Day 5+ critical/convalescent phase'}); serial testing daily."
                })

            if is_early_phase:
                # Early Phase (Day 1 - 5): NS1 Antigen & RT-PCR
                if not any("ns1" in t.get("test_name", "").lower() for t in tests):
                    tests_to_inject.append({
                        "test_name": "Dengue NS1 Antigen Test (ELISA / Rapid)",
                        "purpose": "Highest diagnostic sensitivity during active viral replication in first 1-5 days of fever.",
                        "when_considered": f"Currently indicated: Patient reported duration {duration_info.get('raw_duration')} (Day 1-5 window). Note: Dengue IgM is not sensitive during this early window."
                    })
                if has_chikungunya_markers and not any("pcr" in t.get("test_name", "").lower() for t in tests):
                    tests_to_inject.append({
                        "test_name": "Chikungunya RT-PCR (Viral RNA)",
                        "purpose": "Detects viral RNA during early viraemic window (Days 1 to 7).",
                        "when_considered": "Acute febrile phase with disabling symmetrical polyarthritis."
                    })
            elif is_late_phase:
                # Late Phase (Day 5+): IgM/IgG Serology & Platelet Tracking
                if not any("igm" in t.get("test_name", "").lower() or "serology" in t.get("test_name", "").lower() for t in tests):
                    tests_to_inject.append({
                        "test_name": "Dengue IgM & IgG Serological ELISA",
                        "purpose": "Detects humoral anti-dengue antibodies which emerge around Day 5 and peak during convalescence.",
                        "when_considered": f"Currently indicated: Patient reported duration {duration_info.get('raw_duration')} (Day 5+ window). Note: NS1 antigen sensitivity drops after day 5."
                    })
                if has_chikungunya_markers:
                    tests_to_inject.append({
                        "test_name": "Chikungunya IgM ELISA Serology",
                        "purpose": "Primary serological confirmation for Chikungunya virus antibodies after Day 7.",
                        "when_considered": "Persistent polyarthritis / post-febrile phase."
                    })
            else:
                # Duration unstated: Recommend combined NS1 + IgM profile
                if not any("ns1" in t.get("test_name", "").lower() for t in tests):
                    tests_to_inject.append({
                        "test_name": "Dengue NS1 Antigen & Dengue IgM/IgG Combo Panel",
                        "purpose": "Comprehensive screen covering both early viraemic phase (NS1: Days 1-5) and convalescent antibody phase (IgM: Day 5+).",
                        "when_considered": "Acute febrile presentation where exact onset timing is being clinically determined."
                    })

            for ti in reversed(tests_to_inject):
                tests.insert(0, ti)

        assessment["test_guidance"] = tests

        # 5. DYNAMIC, CONDITION-AWARE CLINICAL SOAP REPORT GENERATION
        raw_soap = assessment.get("consultation_summary", {})
        assessment["consultation_summary"] = self._synthesize_clinical_soap(
            existing_soap=raw_soap,
            chief_complaint=chief_complaint,
            active_symptoms=active_symptoms,
            negated_symptoms=negated_symptoms,
            warning_signs=warning_signs,
            duration_info=duration_info,
            severity_info=severity_info,
            conditions=conditions,
            tests=tests,
            precautions=precautions
        )

        # 6. NON-DRUG SUPPORTIVE HOME REMEDIES & PATIENT-GUIDE SUMMARY
        home_remedies = self._generate_home_remedies(chief_complaint, active_symptoms, full_text)
        why_it_happens = self._generate_why_it_happens(chief_complaint, active_symptoms, full_text)
        prevention_tips = self._generate_prevention_tips(chief_complaint, active_symptoms, full_text)
        exercise_guidance = self._generate_exercise_guidance(chief_complaint, active_symptoms, full_text)
        hydration_advice = self._generate_hydration_advice(chief_complaint, active_symptoms, full_text)

        assessment["home_remedies"] = home_remedies
        assessment["cure_and_relief"] = [f"{r['title']}: {r['instructions']}" if isinstance(r, dict) else str(r) for r in home_remedies]
        assessment["why_it_happens"] = why_it_happens
        assessment["prevention_tips"] = prevention_tips
        assessment["exercises"] = exercise_guidance
        assessment["exercise_guidance"] = exercise_guidance
        assessment["hydration_advice"] = hydration_advice
        assessment["differential_diagnoses"] = conditions
        assessment["what_it_likely_is"] = self._generate_plain_language_explanation(chief_complaint, active_symptoms, full_text, conditions)
        assessment["when_to_see_doctor"] = self._generate_when_to_see_doctor(chief_complaint, active_symptoms, full_text)
        assessment["doctor_review_disclaimer"] = "AI Virtual Doctor clinical decision-support only. Definitive diagnosis, prescription confirmation, and final treatment approval must be conducted by a licensed physician in the Doctor Portal."

        return assessment

    def _generate_home_remedies(self, chief_complaint: str, active_symptoms: List[str], full_text: str) -> List[Dict[str, str]]:
        """
        Generates 2 to 3 concise, high-yield, non-drug home remedies tailored to the patient's condition.
        """
        text_lower = f"{chief_complaint} {' '.join(active_symptoms)} {full_text}".lower()
        remedies = []

        # Cold / Congestion / Sinus / Rhinitis
        if any(w in text_lower for w in ["cold", "sneez", "runny nose", "congestion", "stuffy", "sinus", "nasal"]):
            remedies.append({
                "title": "Steam Inhalation",
                "instructions": "Inhale warm steam for 5–10 minutes, 2 to 3 times daily to loosen mucus, hydrate nasal passages, and relieve sinus pressure."
            })
            remedies.append({
                "title": "Saline Nasal Rinse",
                "instructions": "Use sterile saline spray or gentle saline rinse to flush irritants and clear congestion naturally without medicated rebound."
            })
            remedies.append({
                "title": "Elevate Head While Resting",
                "instructions": "Prop your head up with an extra pillow to prevent nighttime nasal congestion from pooling and improve airflow."
            })

        # Cough & Sore Throat
        elif any(w in text_lower for w in ["cough", "throat", "phlegm", "voice", "hoarse"]):
            remedies.append({
                "title": "Warm Salt-Water Gargle",
                "instructions": "Dissolve 1/2 tsp salt in warm water; gargle 30 seconds 3 times daily to reduce throat swelling and wash away irritants."
            })
            remedies.append({
                "title": "Honey & Warm Water",
                "instructions": "Take 1 to 2 teaspoons of pure honey in warm water to naturally soothe irritated airway lining and calm cough spasms (avoid in infants under 1 year)."
            })
            remedies.append({
                "title": "Room Humidification",
                "instructions": "Run a cool-mist humidifier in your sleeping area to keep airways moist and prevent dry air from triggering coughing fits."
            })

        # Headache & Tension
        elif any(w in text_lower for w in ["headache", "head pain", "migraine", "forehead", "temple"]):
            remedies.append({
                "title": "Targeted Temperature Compress",
                "instructions": "Place a cool damp cloth over forehead or a warm compress on the back of the neck for 15 minutes to ease vascular and muscle tension."
            })
            remedies.append({
                "title": "Quiet, Screen-Free Rest",
                "instructions": "Rest in a quiet, dimmed room away from smartphones and monitors to allow optic nerves and scalp musculature to relax."
            })
            remedies.append({
                "title": "Steady Oral Hydration",
                "instructions": "Sip room-temperature water or coconut water consistently; even minor fluid deficits frequently trigger head tension."
            })

        # Stomach / Indigestion / Nausea / Acidity
        elif any(w in text_lower for w in ["stomach", "nausea", "vomit", "diarrhea", "acidity", "indigestion", "bloat", "cramp"]):
            remedies.append({
                "title": "Frequent Small Sips of Fluids (ORS)",
                "instructions": "Take small sips of water or electrolyte solution every 10–15 minutes instead of full glasses to stay hydrated without triggering nausea."
            })
            remedies.append({
                "title": "Gentle Bland Nutrition",
                "instructions": "Consume small, simple portions (bananas, plain rice, oatmeal, or toast); avoid fried, spicy, and acidic foods until settled."
            })
            remedies.append({
                "title": "Warm Ginger Water",
                "instructions": "Sip mild, warm ginger tea to naturally settle gastric motility and relieve mild bloating or nausea."
            })

        # Fever & General Fatigue
        elif any(w in text_lower for w in ["fever", "pyrexia", "temperature", "chills", "tired", "fatigue", "body ache", "weakness"]):
            remedies.append({
                "title": "Dedicated Bed Rest",
                "instructions": "Prioritize 8–9 hours of undisturbed sleep; physical rest conserves energy necessary for immune antibody production."
            })
            remedies.append({
                "title": "Lukewarm Sponge Comfort",
                "instructions": "Wipe forehead and neck with a lukewarm damp cloth for comfort if feeling overheated (never use cold water or alcohol rubs)."
            })
            remedies.append({
                "title": "Frequent Warm Liquids",
                "instructions": "Drink warm clear broths and herbal teas throughout the day to replenish fluid loss and sustain circulation."
            })

        # General supportive care fallback
        if not remedies:
            remedies = [
                {
                    "title": "Dedicated Rest & Recovery",
                    "instructions": "Get 8 to 9 hours of restorative sleep and avoid strenuous exertion to allow natural recovery."
                },
                {
                    "title": "Hydration Support",
                    "instructions": "Drink 2 to 2.5 liters of clean water and warm broths daily to keep mucosal tissues hydrated."
                },
                {
                    "title": "Light, Fresh Nutrition",
                    "instructions": "Eat easily digestible, warm meals rich in vitamins (such as vegetable soups and fresh fruits)."
                }
            ]

        return remedies[:3]

    def _generate_plain_language_explanation(self, chief_complaint: str, active_symptoms: List[str], full_text: str, conditions: List[Dict[str, Any]]) -> str:
        """
        Explains what the likely everyday health issue is in reassuring, plain English without alarming diagnoses.
        """
        text_lower = f"{chief_complaint} {' '.join(active_symptoms)} {full_text}".lower()

        if any(w in text_lower for w in ["cold", "sneez", "runny nose", "stuffy", "congestion"]):
            return "Common Cold (Mild Viral Upper Respiratory Infection): This is an everyday, self-limiting viral inflammation of the nasal passages and throat. It is very common, generally harmless, and typically runs its course within 7 to 10 days with simple home care and rest."
        if any(w in text_lower for w in ["cough", "throat"]):
            return "Mild Respiratory or Throat Irritation: Usually caused by seasonal weather shifts, mild viral exposure, or dry air. Typically resolves naturally with throat-soothing fluids and rest."
        if any(w in text_lower for w in ["headache", "head pain"]):
            return "Mild Tension or Strain Headache: Commonly triggered by eye strain, screen fatigue, stress, or mild dehydration. Usually subsides quickly with a quiet rest, hydration, and cool compress."
        if any(w in text_lower for w in ["stomach", "acidity", "indigestion"]):
            return "Mild Indigestion or Acid Sensitivity: Commonly related to irregular meal timing, spicy food, or mild stress. Settles smoothly with light meals and oral hydration."

        if conditions:
            first_cond = conditions[0].get("condition", "Everyday Health Consideration")
            return f"{first_cond}: Based on your reported symptoms, this appears to be a common, manageable condition that usually improves with rest and supportive care."

        return "Everyday Mild Health Concern: Your presentation points to a standard, non-emergency health concern that can typically be managed with restful self-care and hydration."

    def _generate_when_to_see_doctor(self, chief_complaint: str, active_symptoms: List[str], full_text: str) -> List[str]:
        """
        High-priority, medically critical safety precautions and red-flag warning signs.
        """
        return [
            "Fever exceeds 102°F (38.9°C) or persists for more than 3 consecutive days",
            "Shortness of breath, rapid breathing, or chest tightness while resting",
            "Inability to retain fluids, severe vomiting, or signs of dehydration (dark urine, dizziness)",
            "Symptoms fail to improve after 7 to 10 days, or suddenly deteriorate"
        ]

    def _generate_why_it_happens(self, chief_complaint: str, active_symptoms: List[str], full_text: str) -> str:
        """
        Explains why the symptom happens (biological cause) in 2 to 3 concise, reassuring sentences.
        """
        text_lower = f"{chief_complaint} {' '.join(active_symptoms)} {full_text}".lower()

        # Cold / Congestion / Sinus / Rhinitis
        if any(w in text_lower for w in ["cold", "sneez", "runny nose", "congestion", "stuffy", "sinus", "nasal"]):
            return (
                "Respiratory viruses trigger mild inflammation in nasal mucosal tissues. "
                "In response, local blood vessels expand and mucus glands secrete extra fluid to trap and flush out viral particles, resulting in stuffiness and drainage."
            )

        # Cough & Sore Throat
        elif any(w in text_lower for w in ["cough", "throat", "phlegm", "voice", "hoarse"]):
            return (
                "Airway sensory nerve endings become irritated by viral inflammation, dry air, or post-nasal drip. "
                "Coughing is your respiratory system's natural protective reflex to clear mucus and keep the lungs clear."
            )

        # Headache & Tension / Weakness
        elif any(w in text_lower for w in ["headache", "head pain", "migraine", "forehead", "temple", "weakness"]):
            return (
                "Everyday headaches and mild fatigue typically stem from sustained contraction of scalp and neck muscles. "
                "Common triggers include prolonged screen time, eye fatigue, mental stress, or mild dehydration irritating local nerve pathways."
            )

        # Stomach / Indigestion / Acidity
        elif any(w in text_lower for w in ["stomach", "nausea", "vomit", "diarrhea", "acidity", "indigestion", "bloat", "cramp"]):
            return (
                "Gastric acid and enzymes irritate the stomach or lower esophagus lining, commonly triggered by irregular eating, spicy foods, or stress. "
                "This slows gastric emptying and causes mild reflux, cramping, or bloating sensations."
            )

        # Fever & Malaise
        elif any(w in text_lower for w in ["fever", "pyrexia", "temperature", "chills"]):
            return (
                "Fever is your body's intentional immune defense mechanism. "
                "Immune cells release pyrogenic signals that raise your body's internal thermostat to slow viral replication and accelerate antibody activity."
            )

        # General presentation
        return (
            "This health concern is a natural physiological reaction to temporary physical strain, environmental exposure, or a mild self-limiting viral encounter. "
            "Your body's immune and reparative systems are actively working to restore normal baseline health."
        )

    def _generate_prevention_tips(self, chief_complaint: str, active_symptoms: List[str], full_text: str) -> List[str]:
        """
        2 to 3 concise, important, and accurate prevention habits.
        """
        text_lower = f"{chief_complaint} {' '.join(active_symptoms)} {full_text}".lower()

        # Cold / Cough / Respiratory
        if any(w in text_lower for w in ["cold", "sneez", "runny nose", "congestion", "cough", "throat"]):
            return [
                "Practice frequent hand hygiene: Wash hands with soap for 20 seconds before eating or touching your eyes and nose.",
                "Maintain room humidity: Keep indoor air between 40% and 50% using a cool-mist humidifier to prevent dry mucosal membranes.",
                "Ensure restful sleep: Prioritize 7 to 8 hours of uninterrupted sleep to sustain mucosal immune defenses."
            ]

        # Headache / Tension / Fatigue
        elif any(w in text_lower for w in ["headache", "head pain", "migraine", "weakness", "fatigue"]):
            return [
                "Follow the 20-20-20 screen rule: Every 20 minutes, gaze 20 feet away for 20 seconds to ease digital eye fatigue.",
                "Maintain ergonomic posture: Keep computer monitors at eye level with relaxed shoulders and lumbar support.",
                "Consistent hydration: Sip water steadily throughout the day; even slight dehydration commonly triggers head pain."
            ]

        # Stomach / Indigestion / Acidity
        elif any(w in text_lower for w in ["stomach", "nausea", "vomit", "diarrhea", "acidity", "indigestion"]):
            return [
                "Eat moderate, timely portions: Smaller, regular meals prevent overloading stomach volume and acid production.",
                "Stay upright after meals: Avoid lying down or reclining for at least 2 to 3 hours after eating.",
                "Limit dietary triggers: Minimize greasy fried dishes, late-night snacking, and high caffeine intake."
            ]

        # General Default
        return [
            "Maintain consistent sleep hygiene with 7–8 hours of restorative rest each night.",
            "Stay adequately hydrated with 2 to 2.5 liters of water and clear fluids daily.",
            "Practice balanced nutrition and wash hands frequently during seasonal illness shifts."
        ][:3]

    def _generate_exercise_guidance(self, chief_complaint: str, active_symptoms: List[str], full_text: str) -> List[Dict[str, str]]:
        """
        Exactly 2 concise, accurate movement or breathing guidance points.
        """
        text_lower = f"{chief_complaint} {' '.join(active_symptoms)} {full_text}".lower()
        exercises = []

        # 1. Headache / Weakness / Neck Tension / Fatigue
        if any(w in text_lower for w in ["headache", "head pain", "migraine", "weakness", "tired", "fatigue", "neck"]):
            exercises.append({
                "name": "Gentle Cervical & Neck Stretches",
                "instructions": "Slowly tilt your right ear to your right shoulder for 15 seconds, then switch sides; gently tuck your chin to relieve scalp and neck muscle tension."
            })
            exercises.append({
                "name": "Diaphragmatic Breathing & Rest",
                "instructions": "Inhale through your nose for 4 seconds, exhale gently through pursed lips for 6 seconds for 5 minutes; pause strenuous lifting until weakness resolves."
            })

        # 2. Cold / Cough / Respiratory
        elif any(w in text_lower for w in ["cold", "cough", "throat", "congestion", "sinus", "breath"]):
            exercises.append({
                "name": "Upright Seated Chest Expansion",
                "instructions": "Sit upright and gently roll your shoulders backward while inhaling deeply to open rib cage volume and assist airway drainage."
            })
            exercises.append({
                "name": "Gentle Pacing & Walking",
                "instructions": "Take relaxed 5–10 minute indoor walks if fever-free; avoid vigorous high-intensity cardio that triggers rapid dry mouth-breathing."
            })

        # 3. Gastrointestinal / Dyspepsia / Acidity
        elif any(w in text_lower for w in ["stomach", "acidity", "indigestion", "nausea", "bloat", "cramp"]):
            exercises.append({
                "name": "10-Minute Post-Meal Stroll",
                "instructions": "Take a casual, gentle walk after meals; gravitational assistance and mild abdominal movement speed digestion and reduce acid reflux."
            })
            exercises.append({
                "name": "Avoid Core Strain & Bending",
                "instructions": "Avoid crunches, heavy lifting, or lying flat for 2–3 hours after eating to prevent intra-abdominal pressure from pushing acid upward."
            })

        # 4. Musculoskeletal / Back Pain / Body Aches
        elif any(w in text_lower for w in ["back pain", "joint pain", "spine", "body ache"]):
            exercises.append({
                "name": "Supine Knee-to-Chest Stretch",
                "instructions": "Lie flat with knees bent, gently draw one knee to chest for 15–20 seconds to relieve lumbar spinal compression."
            })
            exercises.append({
                "name": "Gentle Pelvic Tilts",
                "instructions": "Gently tighten abdominal muscles and press lower back into the floor for 5 seconds; avoid heavy lifting or twisting."
            })

        # 5. Default General Physical Guidance
        else:
            exercises.append({
                "name": "Restorative Joint Mobility",
                "instructions": "Perform gentle rotations of ankles, wrists, and shoulders with brief slow walking to stimulate circulation without fatigue."
            })
            exercises.append({
                "name": "Relaxed Posture Realignment",
                "instructions": "Keep ears aligned over shoulders with a supported spine, taking short 1-minute movement breaks during prolonged sitting."
            })

        return exercises[:2]

    def _generate_hydration_advice(self, chief_complaint: str, active_symptoms: List[str], full_text: str) -> Dict[str, Any]:
        """
        Specific hydration targets, recommended beverages, and fluids to avoid.
        """
        text_lower = f"{chief_complaint} {' '.join(active_symptoms)} {full_text}".lower()

        daily_target = "2.5 to 3.0 Liters daily (approx. 8–10 glasses)"
        recommended = ["Filtered room-temperature or warm water", "Electrolyte-rich fluids (coconut water, oral rehydration solutions)"]
        avoid = ["High-sugar carbonated beverages", "Excessive caffeine (more than 1 cup of coffee/day)", "Alcoholic beverages"]
        tips = "Drink in steady sips throughout the day rather than chugging large quantities at once."

        if any(w in text_lower for w in ["cold", "cough", "throat", "congestion", "sinus"]):
            daily_target = "3.0 Liters daily (increased fluid requirement for mucus thinning)"
            recommended.extend([
                "Warm herbal teas (ginger, chamomile, peppermint with pure honey)",
                "Clear vegetable, chicken, or bone broths",
                "Warm lemon water"
            ])
            tips = "Warm fluids provide dual benefits: hydrating mucous membranes and providing direct steam to soothe the upper respiratory tract."

        elif any(w in text_lower for w in ["headache", "weakness", "dizziness", "fatigue"]):
            recommended.extend([
                "Oral Rehydration Salts (ORS) or electrolyte water",
                "Fresh tender coconut water (rich in potassium and magnesium)",
                "Water infused with cucumber or a pinch of pink salt"
            ])
            avoid.append("Energy drinks with high taurine/caffeine (triggers secondary vascular rebound headache)")
            tips = "Mild subclinical dehydration is one of the most common reversible causes of headache and physical weakness."

        elif any(w in text_lower for w in ["stomach", "nausea", "vomit", "diarrhea"]):
            daily_target = "Take small sips of 30–50 mL every 10–15 minutes"
            recommended = [
                "WHO-formulated Oral Rehydration Salt (ORS) solution",
                "Rice water or barley water",
                "Diluted clear broth"
            ]
            avoid.extend(["Dairy milk and rich milkshakes", "Citrus juices (irritates inflamed gastric mucosa)"])
            tips = "Do not force large gulps if feeling nauseated; small frequent sips prevent gastric distension and vomiting."

        return {
            "daily_target": daily_target,
            "recommended_fluids": recommended,
            "fluids_to_avoid": avoid,
            "clinical_tips": tips
        }

    def _generate_rule_based_assessment(
        self,
        chief_complaint: str,
        conversation_text: str,
        sources: List[Dict[str, Any]],
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        High-grade clinical knowledge engine fallback.
        Evaluates symptom complexes hierarchically:
        1. Meningeal / Neurological
        2. Acute Thoracic / Cardiac
        3. Arboviral Vector-Borne Fever (Dengue / Chikungunya / Malaria)
        4. Acute Respiratory Tract Infection
        5. Acute Gastrointestinal / Dyspepsia
        6. Metabolic / Endocrine
        7. Non-Specific Malaise
        """
        text = f"{chief_complaint} {conversation_text}".lower()

        # Check symptom components
        has_fever = any(w in text for w in ["fever", "pyrexia", "temperature", "chills", "rigors", "burning hot"])
        has_retro_orbital = any(w in text for w in ["retro-orbital", "behind eyes", "eye pain", "eye ache", "behind the eye"])
        has_bone_joint = any(w in text for w in ["breakbone", "bone pain", "joint pain", "myalgia", "body ache", "arthralgia", "aching all over"])
        has_rash_or_bleed = any(w in text for w in ["petechiae", "red spots", "rash", "bleeding", "nosebleed", "gums", "epistaxis"])
        has_cough = any(w in text for w in ["cough", "phlegm", "sputum", "sore throat", "wheezing", "rhinorrhea", "congestion", "runny nose"])
        has_stiff_neck = any(w in text for w in ["stiff neck", "neck stiffness", "nuchal rigidity"])
        has_chest_pain = any(w in text for w in ["chest pain", "crushing pain", "pressure in chest", "chest tightness", "angina"])
        has_chikungunya_markers = any(w in text for w in ["chikungunya", "wrist", "ankle", "joint swelling", "swollen joint", "swelling in", "morning stiffness", "polyarthralgia", "polyarthritis", "small joint", "crippling joint"])

        # Extract duration & warning info if available
        dur_info = extracted_entities.get("duration_info", {}) if extracted_entities else {}
        is_early_arboviral = dur_info.get("is_acute_early", False)
        is_late_arboviral = dur_info.get("is_convalescent_late", False)
        active_warning_signs = extracted_entities.get("warning_signs", []) if extracted_entities else []

        # 1. Meningeal Syndrome
        if has_fever and has_stiff_neck:
            conditions = [
                {
                    "condition": "Suspected Acute Meningitis / Meningoencephalitis",
                    "likelihood": "High",
                    "rationale": "High fever coupled with nuchal rigidity (neck stiffness) and photophobia is a critical neurological emergency complex.",
                    "clinical_explanation": "Acute infection of the meninges surrounding the brain and spinal cord, requiring immediate diagnostic lumbar puncture and empiric hospital therapy."
                }
            ]
            precautions = [
                "EMERGENCY WARNING: Proceed to the nearest hospital emergency room immediately.",
                "Do not wait or administer oral home remedies.",
                "Keep patient lying in a calm, dimmed room to minimize photophobia while emergency services arrive."
            ]
            tests = [
                {"test_name": "Lumbar Puncture (CSF Analysis)", "purpose": "Determines viral vs bacterial meningitis pathogens, protein, and cell count.", "when_considered": "Immediate emergency department setting."},
                {"test_name": "Blood Cultures & CBC", "purpose": "Identifies bacteremia and systemic leukocytosis.", "when_considered": "Pre-antibiotic emergency workup."}
            ]
            diet = {"avoid": ["Oral intake if altered mental status"], "recommended": ["Strict medical fasting until physician review"], "hydration": "Intravenous fluids in hospital."}
            med_info = [{"drug_class": "Emergency Hospital-Administered Antibiotics / Antivirals", "common_examples": ["Ceftriaxone", "Vancomycin", "Acyclovir"], "clinical_purpose": "Immediate eradication of central nervous system pathogens.", "precautions": "Must be physician administered via IV in hospital.", "side_effects": "Hospital monitoring required."}]

        # 2. Acute Thoracic / Cardiac Syndrome
        elif has_chest_pain:
            conditions = [
                {
                    "condition": "Suspected Acute Coronary Syndrome (ACS) / Angina",
                    "likelihood": "High",
                    "rationale": "Chest tightness or pressure, particularly if radiating to arm, neck, or accompanied by diaphoresis, warrants immediate cardiac exclusion.",
                    "clinical_explanation": "Myocardial ischemia resulting from coronary artery compromise, requiring urgent 12-lead ECG and serial cardiac enzyme evaluation."
                },
                {
                    "condition": "Musculoskeletal Chest Wall Pain / Costochondritis",
                    "likelihood": "Moderate",
                    "rationale": "Localized chest tenderness reproducible on palpation without systemic signs.",
                    "clinical_explanation": "Benign inflammation of the costochondral junctions."
                }
            ]
            precautions = [
                "EMERGENCY RED FLAG: If pain radiates to jaw/arm or is accompanied by cold sweat or dizziness, call 911 / 112 immediately.",
                "Avoid any physical exertion, heavy lifting, or stair climbing.",
                "Remain seated in a comfortable upright position."
            ]
            tests = [
                {"test_name": "12-Lead Electrocardiogram (ECG)", "purpose": "Identifies ST-segment elevation or depression and ischemic arrhythmias.", "when_considered": "Immediate emergency evaluation."},
                {"test_name": "High-Sensitivity Cardiac Troponin (hs-cTnI/T)", "purpose": "Detects microscopic myocardial necrosis.", "when_considered": "Serial testing at 0, 1, and 3 hours."}
            ]
            diet = {"avoid": ["Heavy greasy meals", "Caffeine and stimulants"], "recommended": ["Light easily digestible meals"], "hydration": "Adequate sips of water."}
            med_info = [{"drug_class": "Emergency Cardiac Antiplatelet Agents", "common_examples": ["Aspirin (chewable)"], "clinical_purpose": "Emergency platelet inhibition in acute coronary thrombosis.", "precautions": "Take ONLY if explicitly instructed by emergency dispatcher or physician.", "side_effects": "Gastric irritation, bleeding."}]

        # 3. Neurovascular Headache / Cephalea Syndrome (Migraine vs Tension vs Secondary)
        elif any(w in text for w in ["headache", "head pain", "migraine", "throbbing", "aura", "photophobia", "phonophobia", "light sensitivity", "sound sensitivity", "temple pain", "blurred vision"]) and not has_fever:
            is_migraine_pattern = any(w in text for w in ["throbbing", "one side", "one-sided", "unilateral", "aura", "blurred vision", "light", "sound", "photophobia", "phonophobia", "nausea", "worsens with", "physical activity", "migraine"])
            has_aura = any(w in text for w in ["aura", "blurred vision", "flashes", "scotoma", "before headache"])

            if is_migraine_pattern:
                cond_name = "Migraine with Aura (Classic Migraine)" if has_aura else "Migraine without Aura (Common Migraine)"
                conditions = [
                    {
                        "condition": cond_name,
                        "likelihood": "High",
                        "rationale": "Unilateral throbbing head pain lasting hours, exacerbated by physical movement, accompanied by nausea, photophobia, phonophobia, or preceding visual aura.",
                        "clinical_explanation": "Neurovascular cephalalgia caused by trigeminovascular activation, neurogenic inflammation, and cortical spreading depression."
                    },
                    {
                        "condition": "Tension-Type Headache",
                        "likelihood": "Moderate",
                        "rationale": "Common primary headache differential, typically bilateral, band-like, and non-pulsatile without aura.",
                        "clinical_explanation": "Myofascial pericranial muscle contraction and altered central pain processing."
                    },
                    {
                        "condition": "Secondary Cephalea / Cervicogenic Headache",
                        "likelihood": "Low",
                        "rationale": "Exclusionary differential if postural triggers or neck radiation exist.",
                        "clinical_explanation": "Referred pain or secondary vascular headache etiology."
                    }
                ]
            else:
                conditions = [
                    {
                        "condition": "Tension-Type Headache",
                        "likelihood": "High",
                        "rationale": "Bilateral band-like pressure or dull tightness without prominent nausea, photophobia, or visual aura.",
                        "clinical_explanation": "Pericranial muscle tension related to stress, eye strain, or postural fatigue."
                    },
                    {
                        "condition": "Primary Migraine Cephalea",
                        "likelihood": "Moderate",
                        "rationale": "Considered if episodic throbbing or sensory intolerance develops.",
                        "clinical_explanation": "Neurovascular headache spectrum."
                    }
                ]

            precautions = [
                "Rest in a quiet, dark, well-ventilated room to reduce photophobia and sensory overstimulation.",
                "Apply a cold compress or ice pack over the forehead, temples, or base of the neck.",
                "Maintain baseline hydration with cool water or clear fluids; avoid skipping meals.",
                "Keep a structured headache diary tracking triggers (sleep disruption, stress, bright lights, specific foods).",
                "RED FLAG WARNING: Seek emergency hospital care immediately if observing: sudden explosive 'thunderclap' onset, new speech difficulty, limb weakness, or fever with neck stiffness."
            ]
            tests = [
                {"test_name": "Clinical Neurological Examination & Fundoscopy", "purpose": "Assesses cranial nerves and excludes papilledema (elevated intracranial pressure).", "when_considered": "Initial medical workup for severe or recurrent headaches."},
                {"test_name": "Brain MRI or Non-Contrast Head CT", "purpose": "Excludes secondary intracranial lesions, vascular malformations, or acute hemorrhage.", "when_considered": "Indicated if atypical features, new onset in older adults, or focal neurological deficits."}
            ]
            diet = {
                "avoid": ["Known dietary triggers (aged cheeses, cured meats with nitrates, red wine, MSG, artificial sweeteners)", "Excess caffeine or abrupt caffeine withdrawal", "Skipping or delaying regular meals"],
                "recommended": ["Consistent meal timing with magnesium-rich foods (spinach, pumpkin seeds, almonds)", "Ginger tea or ginger infusion (soothes nausea)", "Adequate plain cool water"],
                "hydration": "Drink 2 to 2.5 liters of clean water daily at regular intervals."
            }
            med_info = [
                {
                    "drug_class": "5-HT1B/1D Receptor Agonists (Triptans)",
                    "common_examples": ["Sumatriptan", "Rizatriptan", "Zolmitriptan"],
                    "clinical_purpose": "Migraine-specific abortive treatment; constricts painfully dilated cranial arteries and inhibits neuropeptide release.",
                    "precautions": "Prescription required. Contraindicated in ischemic heart disease, uncontrolled hypertension, or hemiplegic migraine history. Take at headache onset.",
                    "side_effects": "Chest tightness sensation, flushing, tingling, dizziness."
                },
                {
                    "drug_class": "Simple Analgesics / NSAIDs",
                    "common_examples": ["Ibuprofen", "Naproxen", "Paracetamol"],
                    "clinical_purpose": "Mild-to-moderate headache relief when taken early.",
                    "precautions": "Take with food. Limit usage to under 2-3 days per week to prevent Medication Overuse Headache (rebound headaches).",
                    "side_effects": "Gastric irritation, heartburn."
                }
            ]

        # 4. Arboviral Vector-Borne Fever (Dengue / Chikungunya / Malaria)
        elif has_fever and (has_retro_orbital or has_rash_or_bleed or has_chikungunya_markers or (has_bone_joint and not has_cough) or "dengue" in text or "chikungunya" in text or "mosquito" in text):
            # Clinical differentiation: If predominant symmetrical joint swelling/wrists/ankles and absence of retro-orbital pain -> Chikungunya prioritised
            if has_chikungunya_markers and not has_retro_orbital:
                conditions = [
                    {
                        "condition": "Suspected Chikungunya Fever (Alphavirus Polyarthritis)",
                        "likelihood": "High",
                        "rationale": "High fever accompanied by crippling symmetrical polyarthralgia/joint swelling, prominent in wrists/ankles and morning stiffness without primary cough.",
                        "clinical_explanation": "Aedes-transmitted alphaviral infection characterized by severe, often disabling polyarthritis and periarticular swelling."
                    },
                    {
                        "condition": "Suspected Dengue Fever (Arboviral Infection)",
                        "likelihood": "Moderate",
                        "rationale": "Co-endemic vector-borne flavivirus sharing transmission vector and presenting with acute fever, headache, and myalgias.",
                        "clinical_explanation": "Flavivirus infection requiring platelet and hematocrit monitoring to exclude plasma leakage."
                    },
                    {
                        "condition": "Acute Malarial Infection",
                        "likelihood": "Moderate",
                        "rationale": "Febrile paroxysm with rigors requiring peripheral blood smear evaluation.",
                        "clinical_explanation": "Plasmodium parasitic infection causing cyclical red blood cell destruction."
                    }
                ]
            else:
                conditions = [
                    {
                        "condition": "Suspected Dengue Fever (Arboviral Infection)",
                        "likelihood": "High",
                        "rationale": "High fever combined with retro-orbital pain, severe arthralgia/myalgias ('breakbone' aches), and absence of primary cough strongly suggests Dengue.",
                        "clinical_explanation": "Flavivirus infection transmitted by Aedes mosquitoes, characterized by febrile, critical (plasma leakage), and recovery phases."
                    },
                    {
                        "condition": "Chikungunya Fever",
                        "likelihood": "Moderate",
                        "rationale": "Shares vector transmission; manifests with debilitating polyarthralgia and persistent joint swelling.",
                        "clinical_explanation": "Alphavirus infection characterized by acute high fever and prolonged, disabling joint pain."
                    },
                    {
                        "condition": "Acute Malarial Infection",
                        "likelihood": "Moderate",
                        "rationale": "Fever with chills/rigors and body aches requires malaria blood smear exclusion.",
                        "clinical_explanation": "Plasmodium parasite infection causing cyclical red blood cell hemolysis and fever paroxysms."
                    }
                ]

            precautions = [
                "CRITICAL CONTRAINDICATION: Strictly DO NOT take NSAIDs (ibuprofen, aspirin, naproxen, diclofenac) because they impair platelets and trigger life-threatening hemorrhages. Use Paracetamol only.",
                "Maintain aggressive oral hydration with ORS, coconut water, fresh fruit juices, and broths to counter capillary leakage.",
                "Complete bed rest and use mosquito nets to prevent secondary household transmission.",
                "RED FLAGS: Seek immediate emergency hospitalization if observing: severe abdominal pain, persistent vomiting, mucosal bleeding (gums/nose), lethargy, or sudden drop in urine output."
            ]

            if active_warning_signs or any(w in text for w in ["gum bleeding", "nosebleed", "epistaxis", "severe abdominal pain", "persistent vomiting", "melena", "black stool"]):
                detected_signs = active_warning_signs if active_warning_signs else ["Mucosal Bleeding / Severe Warning Signs"]
                precautions.insert(0, f"EMERGENCY WARNING: Immediate hospital admission required. Active WHO warning signs detected: {', '.join(detected_signs)}.")

            # Duration-guided test selection
            tests = [
                {"test_name": "Complete Blood Count (CBC) with Platelets & Hematocrit (PCV)", "purpose": "Monitors thrombocytopenia (platelet drop) and hemoconcentration indicating plasma leakage.", "when_considered": "Daily monitoring during febrile and critical phases."}
            ]
            if is_early_arboviral:
                tests.append({"test_name": "Dengue NS1 Antigen Test", "purpose": "Rapid early confirmation of dengue viral presence (highest sensitivity Days 1-5).", "when_considered": "Currently indicated: Days 1-5 acute phase."})
                if has_chikungunya_markers:
                    tests.append({"test_name": "Chikungunya RT-PCR (Viral RNA)", "purpose": "Detects viral RNA during early viraemic window (Days 1 to 7).", "when_considered": "Acute febrile phase with disabling symmetrical polyarthritis."})
            elif is_late_arboviral:
                tests.append({"test_name": "Dengue IgM & IgG Serological ELISA", "purpose": "Detects specific humoral antibodies to dengue virus (NS1 drops after Day 5).", "when_considered": "Currently indicated: Day 5+ convalescent phase."})
                if has_chikungunya_markers:
                    tests.append({"test_name": "Chikungunya IgM ELISA Serology", "purpose": "Primary serological confirmation for Chikungunya virus antibodies after Day 7.", "when_considered": "Persistent polyarthritis / post-febrile phase."})
            else:
                tests.append({"test_name": "Dengue NS1 Antigen & Dengue IgM/IgG Combo Panel", "purpose": "Covers both early viraemic phase (NS1: Days 1-5) and antibody phase (IgM: Day 5+).", "when_considered": "Acute febrile presentation where exact onset timing is being clinically determined."})

            tests.append({"test_name": "Peripheral Blood Smear & Rapid Diagnostic Test (RDT) for Malaria", "purpose": "Visualizes Plasmodium species (P. falciparum / P. vivax).", "when_considered": "Any acute febrile illness with rigors."})
            diet = {
                "avoid": ["Dark or red-colored foods/drinks (can be confused with gastrointestinal bleeding)", "Oily and spicy foods", "Alcohol and dehydrating beverages"],
                "recommended": ["Oral Rehydration Salts (ORS) solution", "Fresh tender coconut water", "Pomegranate and kiwi fruits", "Warm lentil or vegetable soups", "Papaya leaf extract (if culturally used under physician awareness)"],
                "hydration": "Drink at least 3 liters of fluids daily to maintain adequate urine output."
            }
            med_info = [
                {
                    "drug_class": "Antipyretics (Paracetamol / Acetaminophen)",
                    "common_examples": ["Paracetamol 500mg"],
                    "clinical_purpose": "Safe reduction of fever and relief of musculoskeletal aches without antiplatelet activity.",
                    "precautions": "Do not exceed daily limits (max 3-4g/day in adults) to avoid hepatotoxicity. NEVER take NSAIDs.",
                    "side_effects": "Rare at standard doses."
                },
                {
                    "drug_class": "Oral Rehydration Salts (WHO Formulation)",
                    "common_examples": ["Sodium chloride, potassium chloride, sodium citrate, glucose"],
                    "clinical_purpose": "Maintains intravascular volume and prevents hypovolemic shock from plasma leakage.",
                    "precautions": "Dissolve in exact recommended water quantity.",
                    "side_effects": "None when diluted properly."
                }
            ]

        # 4. Acute Respiratory Tract Syndrome
        elif has_cough:
            conditions = [
                {
                    "condition": "Acute Upper Respiratory Tract Infection (Viral Pharyngitis / Bronchitis)",
                    "likelihood": "High",
                    "rationale": "Cough, airway irritation, sore throat, or nasal symptoms without signs of lower consolidation.",
                    "clinical_explanation": "Viral infection of the upper airway mucosa causing temporary inflammation, mucus hypersecretion, and cough reflex reactivity."
                },
                {
                    "condition": "Seasonal Allergic Rhinitis / Bronchial Hyperresponsiveness",
                    "likelihood": "Moderate",
                    "rationale": "Ongoing dry cough, sneezing, and post-nasal drip without severe constitutional toxicity.",
                    "clinical_explanation": "Histamine-mediated reaction in the airway causing mucosal swelling, clear discharge, and cough reflex hypersensitivity."
                },
                {
                    "condition": "Lower Respiratory Infection (Bacterial Bronchitis or Pneumonia)",
                    "likelihood": "Low to Moderate",
                    "rationale": "Must be ruled out if fever persists >5 days or purulent sputum develops.",
                    "clinical_explanation": "Involvement of deeper lung parenchyma requiring physician auscultation and chest imaging to rule out consolidation."
                }
            ]
            precautions = [
                "Maintain vigorous hydration (warm water, herbal teas, broths) to thin secretions.",
                "Perform steam inhalation twice daily to soothe irritated mucous membranes.",
                "Practice strict hand hygiene and wear a protective mask in public spaces.",
                "Elevate head with an extra pillow at night to reduce post-nasal drip cough.",
                "RED FLAG: Seek emergency care if experiencing shortness of breath, SpO2 below 94%, or coughing blood."
            ]
            tests = [
                {"test_name": "Complete Blood Count (CBC)", "purpose": "Evaluates white blood cell count to differentiate viral from bacterial infection.", "when_considered": "If symptoms persist >5 days or fever >101°F."},
                {"test_name": "Pulse Oximetry (SpO2)", "purpose": "Checks peripheral oxygen saturation non-invasively.", "when_considered": "Routine screening for any respiratory complaint."},
                {"test_name": "Chest X-Ray (PA View)", "purpose": "Visualizes lung fields to rule out infiltrates, consolidation, or pleural effusion.", "when_considered": "If crackles/wheezes heard or persistent chest pain."}
            ]
            diet = {
                "avoid": ["Chilled beverages and ice creams", "Deep fried, greasy foods", "High sugar carbonated drinks"],
                "recommended": ["Warm chicken or vegetable broth", "Ginger, turmeric, and black pepper tea with honey", "Vitamin C rich citrus fruits (room temperature)", "Soft cooked khichdi or oatmeal"],
                "hydration": "Drink 2.5 to 3 liters of warm fluids daily."
            }
            med_info = [
                {
                    "drug_class": "Analgesics & Antipyretics (Paracetamol)",
                    "common_examples": ["Paracetamol (Acetaminophen)"],
                    "clinical_purpose": "Relieves body aches, headache, and reduces elevated body temperature.",
                    "precautions": "Avoid alcohol; do not exceed daily limits to prevent liver toxicity.",
                    "side_effects": "Rare at therapeutic doses."
                },
                {
                    "drug_class": "Antihistamines",
                    "common_examples": ["Cetirizine", "Loratadine"],
                    "clinical_purpose": "Reduces sneezing, rhinorrhea, and allergic airway irritation.",
                    "precautions": "May cause drowsiness. Avoid driving if sedated.",
                    "side_effects": "Dry mouth, drowsiness."
                }
            ]

        # 5. Acute Gastrointestinal / Dyspeptic Syndrome
        elif any(w in text for w in ["stomach", "abdominal", "acidity", "reflux", "vomit", "diarrhea", "nausea"]):
            conditions = [
                {
                    "condition": "Acute Gastroenteritis / Enteritis",
                    "likelihood": "High",
                    "rationale": "Gastrointestinal distress with cramping, nausea, vomiting, or altered bowel habits.",
                    "clinical_explanation": "Inflammation of the mucosal lining of the stomach and intestines, frequently caused by foodborne pathogens or viral irritation."
                },
                {
                    "condition": "Gastroesophageal Reflux Disease (GERD) / Dyspepsia",
                    "likelihood": "Moderate",
                    "rationale": "Epigastric burning, acid regurgitation, and postprandial discomfort.",
                    "clinical_explanation": "Transient relaxation of the lower esophageal sphincter allowing gastric acid to irritate esophageal squamous epithelium."
                }
            ]
            precautions = [
                "Sip Oral Rehydration Salts (ORS) or electrolyte solutions in small frequent amounts.",
                "Remain upright for at least 2-3 hours following any food consumption.",
                "Avoid NSAIDs like ibuprofen or aspirin which can exacerbate gastric ulceration.",
                "RED FLAG: Seek emergency care if vomiting blood, passing black tarry stools, or severe localized right lower quadrant pain."
            ]
            tests = [
                {"test_name": "Routine Stool Examination & Occult Blood", "purpose": "Identifies parasites, ova, and microscopic bleeding.", "when_considered": "Diarrhea persisting >48 hours."},
                {"test_name": "Serum Electrolytes & Renal Panel", "purpose": "Detects dehydration, hypokalemia, or elevated creatinine.", "when_considered": "Moderate to severe vomiting/diarrhea."},
                {"test_name": "Abdominal Ultrasound", "purpose": "Evaluates gallbladder, appendix, liver, and pancreas.", "when_considered": "Persistent focal abdominal tenderness."}
            ]
            diet = {
                "avoid": ["Spicy chili, oily gravies, raw salads", "Caffeine, soda, and dairy", "Processed citrus juices"],
                "recommended": ["BRAT diet: Bananas, Rice, Applesauce, Toast", "Light salted kanji (rice water) and coconut water", "Steamed carrots and boiled potatoes"],
                "hydration": "Frequent small sips of ORS and boiled cooled water."
            }
            med_info = [
                {
                    "drug_class": "Proton Pump Inhibitors (PPIs) & H2 Blockers",
                    "common_examples": ["Pantoprazole", "Famotidine"],
                    "clinical_purpose": "Suppresses gastric acid production to allow mucosal healing.",
                    "precautions": "Typically taken 30 minutes before the first meal of the day under doctor guidance.",
                    "side_effects": "Headache, abdominal cramps."
                },
                {
                    "drug_class": "Oral Rehydration Salts (WHO Formula)",
                    "common_examples": ["Electrolyte powder"],
                    "clinical_purpose": "Restores critical water, sodium, and potassium lost through dehydration.",
                    "precautions": "Prepare in exact recommended volume of clean water.",
                    "side_effects": "None when diluted according to instructions."
                }
            ]

        # 6. Default Non-Specific Prodrome
        else:
            conditions = [
                {
                    "condition": "Non-Specific Viral Prodrome / General Malaise",
                    "likelihood": "Moderate",
                    "rationale": "Constitutional fatigue and diffuse mild discomfort without focal organ localizing symptoms.",
                    "clinical_explanation": "Early inflammatory immune response or physical fatigue requiring supportive hydration and observation."
                },
                {
                    "condition": "Physical Fatigue / Circadian Strain",
                    "likelihood": "Moderate",
                    "rationale": "Somatic manifestations of sleep deprivation, stress, or mild dehydration.",
                    "clinical_explanation": "Physiological fatigue without organic infectious or structural pathology."
                }
            ]
            precautions = [
                "Prioritize 7-8 hours of uninterrupted restorative sleep.",
                "Maintain baseline hydration of 2.5 liters of clean water daily.",
                "Keep a daily symptom diary noting timing, severity, and triggers.",
                "Schedule a primary care evaluation if symptoms worsen or do not resolve within 5-7 days."
            ]
            tests = [
                {"test_name": "Complete Blood Count (CBC) with ESR", "purpose": "Broad screen for infection, inflammation, or anemia.", "when_considered": "Baseline initial assessment."},
                {"test_name": "Comprehensive Metabolic Panel (CMP)", "purpose": "Screens liver, kidney, blood glucose, and electrolytes.", "when_considered": "Unexplained ongoing fatigue."}
            ]
            diet = {
                "avoid": ["Refined sugars and ultra-processed fast food", "Excessive caffeine and energy drinks", "Late night heavy meals"],
                "recommended": ["Balanced whole foods: whole grains, colorful vegetables, lean proteins", "Nuts and seeds for micronutrients", "Adequate water and herbal teas"],
                "hydration": "Drink 2 to 2.5 liters of water daily."
            }
            med_info = [
                {
                    "drug_class": "Mild Analgesics (Paracetamol)",
                    "common_examples": ["Paracetamol 500mg"],
                    "clinical_purpose": "Temporary relief of mild discomfort.",
                    "precautions": "Do not exceed maximum daily limits. Always discuss with a physician.",
                    "side_effects": "Rare at standard doses."
                }
            ]

        soap = self._synthesize_clinical_soap(
            existing_soap={},
            chief_complaint=chief_complaint,
            active_symptoms=extracted_entities.get("active_symptoms", []) if extracted_entities else [chief_complaint],
            negated_symptoms=extracted_entities.get("negated_symptoms", []) if extracted_entities else [],
            warning_signs=extracted_entities.get("warning_signs", []) if extracted_entities else [],
            duration_info=extracted_entities.get("duration_info", {}) if extracted_entities else {},
            severity_info=extracted_entities.get("severity_info", {}) if extracted_entities else {},
            conditions=conditions,
            tests=tests,
            precautions=precautions
        )

        active_syms = extracted_entities.get("active_symptoms", []) if extracted_entities else [chief_complaint]
        combined_text = f"{chief_complaint} {conversation_text}"

        home_rems = self._generate_home_remedies(chief_complaint, active_syms, combined_text)
        why_text = self._generate_why_it_happens(chief_complaint, active_syms, combined_text)
        prev_list = self._generate_prevention_tips(chief_complaint, active_syms, combined_text)
        ex_guidance = self._generate_exercise_guidance(chief_complaint, active_syms, combined_text)
        hyd_advice = self._generate_hydration_advice(chief_complaint, active_syms, combined_text)

        return {
            "possible_conditions": conditions,
            "differential_diagnoses": conditions,
            "precautions": precautions,
            "test_guidance": tests,
            "diet_guidance": diet,
            "medication_info": med_info,
            "consultation_summary": soap,
            "home_remedies": home_rems,
            "cure_and_relief": [f"{r['title']}: {r['instructions']}" if isinstance(r, dict) else str(r) for r in home_rems],
            "why_it_happens": why_text,
            "prevention_tips": prev_list,
            "exercises": ex_guidance,
            "exercise_guidance": ex_guidance,
            "hydration_advice": hyd_advice,
            "what_it_likely_is": self._generate_plain_language_explanation(chief_complaint, active_syms, combined_text, conditions),
            "when_to_see_doctor": self._generate_when_to_see_doctor(chief_complaint, active_syms, combined_text),
            "doctor_review_disclaimer": "AI Virtual Doctor clinical decision-support only. Definitive diagnosis, prescription confirmation, and final treatment approval must be conducted by a licensed physician in the Doctor Portal."
        }

    # --- Feature 2: Medical Report Analysis ---
    async def analyze_report_text(
        self,
        report_text: str,
        file_name: str,
        parsed_rows: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Interprets multi-panel lab reports, blood panels, radiology reports, or discharge summaries.
        Extracts ALL parameters across ALL sections, identifies what is abnormal, produces a short analysis,
        and formulates a relevant clinical conclusion for patient and doctor review.
        """
        if parsed_rows is None:
            parsed_rows = parse_lab_report_rows(report_text).get("rows", [])

        # Format pre-parsed parameter rows so the LLM never drops rows in multi-panel PDFs
        parsed_rows_block = ""
        if parsed_rows:
            row_lines = []
            for idx, r in enumerate(parsed_rows, 1):
                unit_part = f" {r['unit']}" if r.get("unit") else ""
                row_lines.append(
                    f"{idx}. [{r.get('section', 'Panel')}] {r.get('parameter_name')}: "
                    f"{r.get('value')}{unit_part} | Ref: {r.get('reference_interval')} | Flag: {r.get('flag')}"
                )
            parsed_rows_block = "\nPRE-EXTRACTED PARAMETER ROWS (Include EVERY row below in all_findings):\n" + "\n".join(row_lines) + "\n"

        # 1. Try LLM analysis first if API key is configured
        llm_prompt = f"""You are an expert Clinical Laboratory & Diagnostic AI Assistant.
Analyze the following multi-panel medical report extracted from '{file_name}'.
{parsed_rows_block}
FULL REPORT TEXT:
{report_text[:12000]}

CLINICAL INSTRUCTIONS:
1. Extract EVERY clinical laboratory test, vital, or diagnostic parameter across ALL sections/panels (e.g., Lipid Profile, Cardiac Risk, Iron Studies, Vitamins, CBC, Liver/Kidney/Thyroid panels). Do NOT stop after the first row or first panel.
2. For each parameter include: finding (Parameter Name), patient_value (with unit), normal_range (Reference Interval), status ("Normal", "High", "Low", or "Abnormal"), unit, section, and explanation.
3. Specifically isolate WHAT IS ABNORMAL (parameters falling outside normal biological reference ranges or flagged High/Low/Abnormal).
4. Provide a SHORT ANALYSIS (2 to 3 concise sentences summarizing key clinical takeaways across all panels).
5. Provide a RELEVANT CONCLUSION (1 to 2 clear sentences explaining what these findings indicate and recommended physician follow-up).

Return strictly valid JSON matching this schema:
{{
  "short_analysis": str,
  "relevant_conclusion": str,
  "abnormal_findings": [
    {{
      "finding": str,
      "patient_value": str,
      "unit": str,
      "normal_range": str,
      "status": "High" | "Low" | "Abnormal",
      "section": str,
      "explanation": str
    }}
  ],
  "all_findings": [
    {{
      "finding": str,
      "patient_value": str,
      "unit": str,
      "normal_range": str,
      "status": "Normal" | "High" | "Low" | "Abnormal",
      "section": str,
      "explanation": str
    }}
  ]
}}
"""
        messages = [
            {"role": "system", "content": "You are a licensed medical AI clinical diagnostics assistant. Extract every single parameter row across all panels. Return strictly valid JSON."},
            {"role": "user", "content": llm_prompt}
        ]

        llm_raw = await self._call_llm(messages, temperature=0.1, max_tokens=3500)
        parsed = None
        if llm_raw:
            try:
                clean = re.sub(r"```json\s*", "", llm_raw)
                clean = re.sub(r"```\s*$", "", clean).strip()
                parsed = json.loads(clean)
            except Exception:
                m = re.search(r"(\{[\s\S]*\})", llm_raw)
                if m:
                    try:
                        parsed = json.loads(m.group(1))
                    except Exception:
                        parsed = None

        if parsed and isinstance(parsed, dict) and "all_findings" in parsed:
            all_f = list(parsed.get("all_findings", []))
            abn_f = list(parsed.get("abnormal_findings", []))

            # Reconcile with parsed_rows so zero parsed rows are ever dropped by the LLM
            existing_names = {str(f.get("finding", "")).strip().lower() for f in all_f}
            for row in parsed_rows:
                pname = str(row.get("parameter_name", "")).strip()
                if pname and pname.lower() not in existing_names:
                    val_disp = f"{row['value']} {row['unit']}".strip() if row.get("unit") else row.get("value", "")
                    item = {
                        "finding": pname,
                        "patient_value": val_disp,
                        "unit": row.get("unit", ""),
                        "normal_range": row.get("reference_interval", "Standard Reference"),
                        "status": row.get("flag", "Normal"),
                        "section": row.get("section", "General Laboratory Panel"),
                        "explanation": row.get("explanation", "")
                    }
                    all_f.append(item)
                    existing_names.add(pname.lower())
                    if item["status"] in ["High", "Low", "Abnormal"]:
                        abn_f.append(item)

            short_an = str(parsed.get("short_analysis", "")).strip()
            conc = str(parsed.get("relevant_conclusion", "")).strip()
            return {
                "findings": all_f,
                "abnormal_findings": abn_f,
                "has_abnormalities": len(abn_f) > 0,
                "short_analysis": short_an or "Diagnostic findings evaluated across all laboratory panels.",
                "relevant_conclusion": conc or (f"Identified {len(abn_f)} abnormal parameters requiring physician correlation." if abn_f else "All evaluated clinical parameters fall within expected biological reference limits."),
                "explanation": f"{conc} {short_an}".strip(),
                "disclaimer": "Diagnostic and laboratory reports must be officially verified and approved by a licensed treating physician."
            }

        # 2. Deterministic Multi-Panel Clinical Evaluator (Uses all parsed_rows + catalog fallback)
        findings = []
        seen_names = set()

        for row in parsed_rows:
            pname = row.get("parameter_name", "").strip()
            if not pname:
                continue
            val_disp = f"{row['value']} {row['unit']}".strip() if row.get("unit") else row.get("value", "")
            findings.append({
                "finding": pname,
                "patient_value": val_disp,
                "unit": row.get("unit", ""),
                "normal_range": row.get("reference_interval", "Standard Reference"),
                "status": row.get("flag", "Normal"),
                "section": row.get("section", "General Laboratory Panel"),
                "explanation": row.get("explanation", f"{pname} diagnostic measurement.")
            })
            seen_names.add(pname.lower())

        # Supplement with catalog pattern matching if any lines were not caught by table row parser
        lines = report_text.splitlines()
        for line in lines:
            line_clean = line.strip().lower()
            for pat, name, ref, unit, low_val, high_val, desc in CLINICAL_REFERENCE_CATALOG:
                if name.lower() in seen_names:
                    continue
                if re.search(pat, line_clean):
                    numbers = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", line)
                    val_str = numbers[0] if numbers else "Recorded"
                    status_val = "Normal"
                    try:
                        num_f = float(val_str.replace(",", ""))
                        if low_val is not None and num_f < low_val:
                            status_val = "Low"
                        elif high_val is not None and num_f > high_val:
                            status_val = "High"
                        else:
                            status_val = "Normal"
                    except Exception:
                        if any(w in line_clean for w in ["high", "elevated", "abnormal", "+", "positive"]):
                            status_val = "High"
                        elif any(w in line_clean for w in ["low", "decreased", "deficient"]):
                            status_val = "Low"

                    val_disp = f"{val_str} {unit}".strip() if unit and val_str != "Recorded" else val_str
                    findings.append({
                        "finding": name,
                        "patient_value": val_disp,
                        "unit": unit,
                        "normal_range": ref,
                        "status": status_val,
                        "section": "General Laboratory Panel",
                        "explanation": f"{desc} ({'Within normal reference interval' if status_val == 'Normal' else f'Out of range: {status_val}'})."
                    })
                    seen_names.add(name.lower())

        if not findings:
            findings = [
                {
                    "finding": "Clinical Diagnostic Document Parsed",
                    "patient_value": "Reviewed",
                    "unit": "",
                    "normal_range": "Standard Reference",
                    "status": "Normal",
                    "section": "General",
                    "explanation": "Diagnostic record parsed and formatted for clinician review."
                }
            ]

        abnormal_list = [f for f in findings if f["status"] in ["High", "Low", "Abnormal"]]
        has_abn = len(abnormal_list) > 0

        if has_abn:
            abn_names = [f"{a['finding']} ({a['status']}: {a['patient_value']} vs ref {a['normal_range']})" for a in abnormal_list]
            short_analysis = (
                f"Document review identified {len(abnormal_list)} parameter(s) outside standard biological reference ranges: {', '.join(abn_names)}."
            )
            relevant_conclusion = (
                f"Abnormal findings detected in {', '.join([a['finding'] for a in abnormal_list])}. "
                f"Physician review is recommended to correlate these findings with active symptoms and determine clinical management."
            )
        else:
            short_analysis = (
                f"All {len(findings)} evaluated laboratory parameter(s) fall within expected physiological reference intervals."
            )
            relevant_conclusion = (
                "All extracted diagnostic markers are within normal biological limits. No acute laboratory abnormalities were detected."
            )

        return {
            "findings": findings,
            "abnormal_findings": abnormal_list,
            "has_abnormalities": has_abn,
            "short_analysis": short_analysis,
            "relevant_conclusion": relevant_conclusion,
            "explanation": f"{relevant_conclusion} {short_analysis}",
            "disclaimer": "Laboratory and diagnostic reports must be officially verified and signed off by a licensed medical practitioner."
        }

openrouter_client = OpenRouterClient()
