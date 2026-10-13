"""Generate the synthetic demo files in samples/claimback/ (spec section 9).

Every insurer, person, number and clause here is invented. Re-run to regenerate:
    python scripts/make_samples.py
"""
import shutil
from pathlib import Path

import pymupdf as fitz

OUT = Path(__file__).resolve().parent.parent / "samples" / "claimback"
INSURER = "Navdhara General Insurance Ltd (fictional)"

POLICY = """NAVDHARA SURAKSHA HEALTH PLAN - POLICY WORDING
(Synthetic document created for software testing. Not a real insurance product.)

1. DEFINITIONS
1.1 Pre-existing Disease means any condition, ailment, injury or disease that was diagnosed by a physician, or for which medical advice or treatment was recommended by or received from a physician, within 36 months prior to the effective date of the first policy issued by the Company.
1.2 Hospitalisation means admission in a hospital for a minimum period of 24 consecutive in-patient care hours.
1.3 Medically Necessary treatment means any treatment, test or stay in hospital that is required for the medical management of the illness or injury suffered by the insured, and that is prescribed by a medical practitioner.
1.4 Continuous Coverage means uninterrupted coverage under this policy, including renewals without a break, from the effective date of the first policy.

2. COVERAGE
2.1 The Company will pay reasonable and customary in-patient hospitalisation expenses incurred for medically necessary treatment, up to the sum insured.
2.2 Day-care procedures listed in Annexure A are covered even where hospitalisation is less than 24 hours.

3. WAITING PERIODS
3.1 Initial waiting period: expenses for any illness contracted within 30 days of the first policy start date are excluded, except claims arising from an accident.
3.2 Specified disease waiting period: expenses for the following are excluded until 24 months of continuous coverage have elapsed: cataract, hernia of all types, joint replacement, kidney or ureteric calculus, benign prostatic hypertrophy, sinusitis.
3.3 Pre-existing disease waiting period: expenses related to a pre-existing disease are excluded until 36 months of continuous coverage have elapsed.

4. EXCLUSIONS
4.1 Expenses related to treatment of a pre-existing disease during the waiting period in clause 3.3.
4.2 Cosmetic or plastic surgery unless needed to treat injury or illness.
4.3 Admission primarily for investigation or evaluation that is not followed by active treatment, or that is not medically necessary as defined in clause 1.3.

5. DISCLOSURE
5.1 The policy may be voided for non-disclosure or misrepresentation of a material fact that the insured knew of at the time of the proposal.

6. CLAIMS AND GRIEVANCES
6.1 The insured must notify the Company within 24 hours of an emergency hospitalisation.
6.2 Grievances may be sent to the Company's Grievance Redressal Officer. If not resolved within 14 days, the insured may approach Bima Bharosa or the Insurance Ombudsman.
"""

CASES = {
    "case_a": {
        "rejection": f"""{INSURER}
Claims Department

Date: 18-Jun-2026
To: Mr. Arvind Kulkarni (fictional)
Claim No: NGI-CL-2026-40112
Policy No: NGI/SHP/2023/00481234
Policy inception date: 01-Mar-2023

Subject: Repudiation of claim

Your claim for hospitalisation from 10-Jun-2026 to 14-Jun-2026 has been examined. The discharge summary records a history of Type 2 Diabetes Mellitus, which is a pre-existing disease as per clause 1.1. Expenses for pre-existing disease are excluded under clause 4.1. The claim is therefore repudiated.

Claims Manager
""",
        "discharge": """CITYCARE MULTISPECIALITY HOSPITAL (fictional)
DISCHARGE SUMMARY

Patient: Arvind Kulkarni   Age/Sex: 52/M   IP No: CC-88213
Date of admission: 10-Jun-2026
Date of discharge: 14-Jun-2026

Diagnosis: Diabetic ketoacidosis with Type 2 Diabetes Mellitus

History: Patient k/c/o Type 2 DM since 1 yr, on oral hypoglycaemics. Presented with vomiting and breathlessness for 2 days. No other known comorbidities.

Treatment: IV fluids, insulin infusion, electrolyte correction.
Procedures: None.
Condition at discharge: Stable.
""",
    },
    "case_b": {
        "rejection": f"""{INSURER}
Claims Department

Date: 29-Jul-2026
To: Ms. Farah Siddiqui (fictional)
Claim No: NGI-CL-2026-40987
Policy No: NGI/SHP/2023/00517760
Policy inception date: 15-May-2023

Subject: Repudiation of claim

Your claim for treatment of left ureteric calculus has been examined. Kidney and ureteric calculus is subject to a waiting period under clause 3.2. The claim is therefore not payable.

Claims Manager
""",
        "discharge": """SUNRISE HOSPITAL (fictional)
DISCHARGE SUMMARY

Patient: Farah Siddiqui   Age/Sex: 38/F   IP No: SR-20419
Date of admission: 20-Jul-2026
Date of discharge: 22-Jul-2026

Diagnosis: Left ureteric calculus (8 mm) with hydronephrosis

History: Acute left flank pain for 1 day. No known comorbidities.

Treatment: Analgesics, IV antibiotics.
Procedures: Left ureteroscopic lithotripsy with DJ stenting.
Condition at discharge: Stable.
""",
    },
    "case_c": {
        "rejection": f"""{INSURER}
Claims Department

Date: 12-Aug-2026
To: Mr. Joseph Dsouza (fictional)
Claim No: NGI-CL-2026-41530
Policy No: NGI/SHP/2025/00733019
Policy inception date: 01-Nov-2025

Subject: Repudiation of claim

Your claim for inguinal hernia repair has been examined. Hernia is subject to a 24 month waiting period under clause 3.2, which has not been completed. The claim is therefore not payable.

Claims Manager
""",
        "discharge": """GREENVALLEY HOSPITAL (fictional)
DISCHARGE SUMMARY

Patient: Joseph Dsouza   Age/Sex: 61/M   IP No: GV-5531
Date of admission: 05-Aug-2026
Date of discharge: 07-Aug-2026

Diagnosis: Right inguinal hernia

History: Swelling in right groin for 3 months. No known comorbidities.

Treatment: Elective repair.
Procedures: Laparoscopic right inguinal hernioplasty with mesh.
Condition at discharge: Stable.
""",
    },
    "case_d": {
        "rejection": f"""{INSURER}
Claims Department

Date: 09-Sep-2026
To: Ms. Meera Pillai (fictional)
Claim No: NGI-CL-2026-42277
Policy No: NGI/SHP/2022/00390551
Policy inception date: 10-Jan-2022

Subject: Repudiation of claim

Your claim for hospitalisation for fever has been examined. The admission was primarily for investigation and could have been managed on an out-patient basis. It is not medically necessary under clause 4.3. The claim is therefore repudiated.

Claims Manager
""",
        # Rendered as a tilted PNG to stand in for a phone photo of a paper summary.
        "discharge": """LAKESHORE HOSPITAL (fictional)
DISCHARGE SUMMARY

Patient: Meera Pillai   Age/Sex: 29/F   IP No: LS-77120
Date of admission: 01-Sep-2026
Date of discharge: 05-Sep-2026

Diagnosis: Dengue fever with thrombocytopenia

History: Fever with body ache for 4 days. No known comorbidities.

Investigations: NS1 antigen positive. Platelet count 38,000/cumm on admission, lowest 22,000/cumm.

Treatment: IV fluids, platelet monitoring every 12 hours, 1 unit platelet transfusion.
Procedures: Platelet transfusion.
Condition at discharge: Stable, platelets 96,000/cumm.
""",
    },
}


def write_pdf(path: Path, text: str) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page()  # A4
    rc = page.insert_textbox(fitz.Rect(50, 50, 545, 800), text, fontsize=10, fontname="helv")
    assert rc >= 0, f"text overflowed page in {path.name}"
    doc.save(path)
    return doc


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write_pdf(OUT / "policy_wording.pdf", POLICY)
    for name, files in CASES.items():
        d = OUT / name
        d.mkdir(exist_ok=True)
        write_pdf(d / "rejection_letter.pdf", files["rejection"])
        if name == "case_d":
            tmp = write_pdf(d / "_tmp.pdf", files["discharge"])
            tmp[0].get_pixmap(matrix=fitz.Matrix(1.6, 1.6).prerotate(3), clip=fitz.Rect(30, 30, 565, 420)).save(
                d / "discharge_summary_photo.png"
            )
            tmp.close()
            (d / "_tmp.pdf").unlink()
        else:
            write_pdf(d / "discharge_summary.pdf", files["discharge"])
    # Same files served by the frontend for the "Try a sample case" buttons.
    shutil.copytree(OUT, OUT.parents[1] / "frontend" / "public" / "samples", dirs_exist_ok=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
