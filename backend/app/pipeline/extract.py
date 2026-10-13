"""Steps 2, 3, 5: classify documents, extract the rejection, extract medical facts (fast tier)."""
from app.llm.client import call_json
from app.models import DocClass, MedicalFacts, Rejection

CLASSIFY = ("Classify this Indian health-insurance document as one of: rejection_letter (insurer letter denying "
            "or repudiating a claim), policy (policy wording or terms), discharge_summary, bill, other.")

REJECTION = ("Extract fields from this insurer claim rejection letter. Copy reason_text verbatim. "
             "cited_clauses: the clause numbers the letter cites, e.g. \"4.1\". policy_start_date: the policy "
             "inception or start date if stated, else null. Dates as YYYY-MM-DD. reason_type: pre_existing, "
             "waiting_period, non_disclosure, not_medically_necessary or other.")

MEDICAL = ("Extract facts from this hospital discharge summary. history_mentioned: verbatim phrases about past "
           "or known conditions and their duration (e.g. \"k/c/o HTN 2 yrs\"); empty list if none. "
           "Dates as YYYY-MM-DD.")


def classify(text: str, case_id: str | None) -> str:
    return call_json("fast", CLASSIFY, text[:4000], DocClass, case_id).doc_type


def extract_rejection(text: str, case_id: str | None) -> Rejection:
    return call_json("fast", REJECTION, text, Rejection, case_id)


def extract_medical_facts(text: str, case_id: str | None) -> MedicalFacts:
    return call_json("fast", MEDICAL, text, MedicalFacts, case_id)
