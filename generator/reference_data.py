from pathlib import Path

import pandas as pd
import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_lines_of_business() -> pd.DataFrame:
    cfg = load_config()
    targets = cfg["targets"]["denial_rate_by_lob"]
    return pd.DataFrame(
        [
            {
                "lob_id": "commercial",
                "lob_name": "Commercial Group",
                "member_share": 0.40,
                "denial_rate_target": targets["commercial"],
                "sla_days": 30,
            },
            {
                "lob_id": "aca_marketplace",
                "lob_name": "ACA Marketplace",
                "member_share": 0.15,
                "denial_rate_target": targets["aca_marketplace"],
                "sla_days": 30,
            },
            {
                "lob_id": "medicare_advantage",
                "lob_name": "Medicare Advantage",
                "member_share": 0.30,
                "denial_rate_target": targets["medicare_advantage"],
                "sla_days": 30,
            },
            {
                "lob_id": "medicaid_managed_care",
                "lob_name": "Medicaid Managed Care",
                "member_share": 0.15,
                "denial_rate_target": targets["medicaid_managed_care"],
                "sla_days": 45,
            },
        ]
    )


def get_service_lines() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "service_line_id": "office_visit",
                "service_line_name": "Office Visit",
                "volume_share": 0.35,
                "allowed_min": 80.0,
                "allowed_max": 250.0,
                "pa_required": False,
            },
            {
                "service_line_id": "ed",
                "service_line_name": "Emergency Department",
                "volume_share": 0.08,
                "allowed_min": 300.0,
                "allowed_max": 2500.0,
                "pa_required": False,
            },
            {
                "service_line_id": "lab",
                "service_line_name": "Laboratory",
                "volume_share": 0.15,
                "allowed_min": 8.0,
                "allowed_max": 150.0,
                "pa_required": False,
            },
            {
                "service_line_id": "imaging",
                "service_line_name": "Imaging",
                "volume_share": 0.12,
                "allowed_min": 40.0,
                "allowed_max": 1800.0,
                "pa_required": True,
            },
            {
                "service_line_id": "outpatient_surgery",
                "service_line_name": "Outpatient Surgery",
                "volume_share": 0.10,
                "allowed_min": 800.0,
                "allowed_max": 8000.0,
                "pa_required": True,
            },
            {
                "service_line_id": "inpatient_surgery",
                "service_line_name": "Inpatient Surgery",
                "volume_share": 0.05,
                "allowed_min": 5000.0,
                "allowed_max": 45000.0,
                "pa_required": True,
            },
            {
                "service_line_id": "pt",
                "service_line_name": "Physical Therapy",
                "volume_share": 0.15,
                "allowed_min": 75.0,
                "allowed_max": 350.0,
                "pa_required": True,
            },
        ]
    )


def get_cpt_codes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # Office visit
            {
                "cpt_code": "99213",
                "description": "Office visit, established patient, low complexity",
                "service_line_id": "office_visit",
                "base_allowed": 110.0,
            },
            {
                "cpt_code": "99214",
                "description": "Office visit, established patient, moderate complexity",
                "service_line_id": "office_visit",
                "base_allowed": 155.0,
            },
            {
                "cpt_code": "99203",
                "description": "Office visit, new patient, low complexity",
                "service_line_id": "office_visit",
                "base_allowed": 125.0,
            },
            {
                "cpt_code": "99204",
                "description": "Office visit, new patient, moderate complexity",
                "service_line_id": "office_visit",
                "base_allowed": 195.0,
            },
            {
                "cpt_code": "99215",
                "description": "Office visit, established patient, high complexity",
                "service_line_id": "office_visit",
                "base_allowed": 220.0,
            },
            # Emergency department
            {
                "cpt_code": "99282",
                "description": "ED visit, low to moderate severity",
                "service_line_id": "ed",
                "base_allowed": 350.0,
            },
            {
                "cpt_code": "99283",
                "description": "ED visit, moderate severity",
                "service_line_id": "ed",
                "base_allowed": 450.0,
            },
            {
                "cpt_code": "99284",
                "description": "ED visit, high severity",
                "service_line_id": "ed",
                "base_allowed": 750.0,
            },
            {
                "cpt_code": "99285",
                "description": "ED visit, high severity with significant threat",
                "service_line_id": "ed",
                "base_allowed": 1200.0,
            },
            # Laboratory
            {
                "cpt_code": "80053",
                "description": "Comprehensive metabolic panel",
                "service_line_id": "lab",
                "base_allowed": 18.0,
            },
            {
                "cpt_code": "85025",
                "description": "Complete blood count with differential",
                "service_line_id": "lab",
                "base_allowed": 12.0,
            },
            {
                "cpt_code": "80061",
                "description": "Lipid panel",
                "service_line_id": "lab",
                "base_allowed": 22.0,
            },
            {
                "cpt_code": "83036",
                "description": "Hemoglobin A1c",
                "service_line_id": "lab",
                "base_allowed": 25.0,
            },
            {
                "cpt_code": "84443",
                "description": "Thyroid stimulating hormone (TSH)",
                "service_line_id": "lab",
                "base_allowed": 28.0,
            },
            {
                "cpt_code": "81001",
                "description": "Urinalysis with microscopy",
                "service_line_id": "lab",
                "base_allowed": 8.0,
            },
            # Imaging
            {
                "cpt_code": "70450",
                "description": "CT head without contrast",
                "service_line_id": "imaging",
                "base_allowed": 350.0,
            },
            {
                "cpt_code": "70553",
                "description": "MRI brain with and without contrast",
                "service_line_id": "imaging",
                "base_allowed": 1200.0,
            },
            {
                "cpt_code": "72148",
                "description": "MRI lumbar spine without contrast",
                "service_line_id": "imaging",
                "base_allowed": 850.0,
            },
            {
                "cpt_code": "71046",
                "description": "Chest X-ray, two views",
                "service_line_id": "imaging",
                "base_allowed": 45.0,
            },
            {
                "cpt_code": "73721",
                "description": "MRI any joint of lower extremity without contrast",
                "service_line_id": "imaging",
                "base_allowed": 780.0,
            },
            {
                "cpt_code": "74177",
                "description": "CT abdomen and pelvis with contrast",
                "service_line_id": "imaging",
                "base_allowed": 650.0,
            },
            # Outpatient surgery
            {
                "cpt_code": "29881",
                "description": "Knee arthroscopy with meniscectomy",
                "service_line_id": "outpatient_surgery",
                "base_allowed": 3200.0,
            },
            {
                "cpt_code": "45378",
                "description": "Colonoscopy, diagnostic",
                "service_line_id": "outpatient_surgery",
                "base_allowed": 1100.0,
            },
            {
                "cpt_code": "66984",
                "description": "Cataract removal with intraocular lens",
                "service_line_id": "outpatient_surgery",
                "base_allowed": 1800.0,
            },
            {
                "cpt_code": "47562",
                "description": "Laparoscopic cholecystectomy",
                "service_line_id": "outpatient_surgery",
                "base_allowed": 4500.0,
            },
            {
                "cpt_code": "23472",
                "description": "Total shoulder arthroplasty",
                "service_line_id": "outpatient_surgery",
                "base_allowed": 6200.0,
            },
            # Inpatient surgery
            {
                "cpt_code": "27447",
                "description": "Total knee arthroplasty",
                "service_line_id": "inpatient_surgery",
                "base_allowed": 18500.0,
            },
            {
                "cpt_code": "27130",
                "description": "Total hip arthroplasty",
                "service_line_id": "inpatient_surgery",
                "base_allowed": 19200.0,
            },
            {
                "cpt_code": "33533",
                "description": "Coronary artery bypass, single arterial graft",
                "service_line_id": "inpatient_surgery",
                "base_allowed": 38000.0,
            },
            {
                "cpt_code": "44140",
                "description": "Colectomy, partial with anastomosis",
                "service_line_id": "inpatient_surgery",
                "base_allowed": 22000.0,
            },
            # Physical therapy
            {
                "cpt_code": "97110",
                "description": "Therapeutic exercises",
                "service_line_id": "pt",
                "base_allowed": 95.0,
            },
            {
                "cpt_code": "97140",
                "description": "Manual therapy techniques",
                "service_line_id": "pt",
                "base_allowed": 90.0,
            },
            {
                "cpt_code": "97530",
                "description": "Therapeutic activities",
                "service_line_id": "pt",
                "base_allowed": 100.0,
            },
            {
                "cpt_code": "97112",
                "description": "Neuromuscular reeducation",
                "service_line_id": "pt",
                "base_allowed": 95.0,
            },
            {
                "cpt_code": "97035",
                "description": "Ultrasound therapy",
                "service_line_id": "pt",
                "base_allowed": 75.0,
            },
        ]
    )


def get_icd10_codes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"icd10_code": "I10", "description": "Essential (primary) hypertension"},
            {
                "icd10_code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
            },
            {"icd10_code": "E78.5", "description": "Hyperlipidemia, unspecified"},
            {"icd10_code": "M54.5", "description": "Low back pain"},
            {"icd10_code": "M25.561", "description": "Pain in right knee"},
            {
                "icd10_code": "J06.9",
                "description": "Acute upper respiratory infection, unspecified",
            },
            {"icd10_code": "J18.9", "description": "Pneumonia, unspecified organism"},
            {"icd10_code": "N18.3", "description": "Chronic kidney disease, stage 3"},
            {
                "icd10_code": "F32.9",
                "description": "Major depressive disorder, single episode, unspecified",
            },
            {
                "icd10_code": "G43.909",
                "description": "Migraine, unspecified, not intractable",
            },
            {
                "icd10_code": "Z00.00",
                "description": "General adult medical exam without abnormal findings",
            },
            {"icd10_code": "Z23", "description": "Encounter for immunization"},
            {
                "icd10_code": "S82.001A",
                "description": "Fracture of right patella, initial encounter",
            },
            {
                "icd10_code": "S72.001A",
                "description": "Fracture of right femoral neck, initial encounter",
            },
            {
                "icd10_code": "K21.9",
                "description": "Gastro-esophageal reflux disease without esophagitis",
            },
            {
                "icd10_code": "K80.20",
                "description": "Calculus of gallbladder without cholecystitis",
            },
            {"icd10_code": "H25.9", "description": "Age-related cataract, unspecified"},
            {
                "icd10_code": "C50.911",
                "description": "Malignant neoplasm of right breast, unspecified quadrant",
            },
            {
                "icd10_code": "I25.10",
                "description": "Atherosclerotic heart disease of native coronary artery",
            },
            {"icd10_code": "I48.91", "description": "Unspecified atrial fibrillation"},
            {
                "icd10_code": "J44.9",
                "description": "Chronic obstructive pulmonary disease, unspecified",
            },
            {"icd10_code": "E66.9", "description": "Obesity, unspecified"},
            {"icd10_code": "R10.9", "description": "Unspecified abdominal pain"},
            {"icd10_code": "R51.9", "description": "Headache, unspecified"},
            {
                "icd10_code": "M17.11",
                "description": "Primary osteoarthritis, right knee",
            },
            {
                "icd10_code": "M16.11",
                "description": "Primary osteoarthritis, right hip",
            },
            {
                "icd10_code": "Z87.891",
                "description": "Personal history of nicotine dependence",
            },
            {
                "icd10_code": "Z79.4",
                "description": "Long term (current) use of insulin",
            },
            {
                "icd10_code": "Z96.651",
                "description": "Presence of right artificial knee joint",
            },
            {
                "icd10_code": "Z96.641",
                "description": "Presence of right artificial hip joint",
            },
            {"icd10_code": "R73.03", "description": "Prediabetes"},
        ]
    )


def get_carc_codes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # Not denials
            {
                "carc_code": "CO-45",
                "description": "Charge exceeds our contracted amount",
                "cause_category": "not_a_denial",
                "is_denial": False,
                "expected_overturn_rate": 0.00,
                "defensibility": "high",
            },
            {
                "carc_code": "PR-1",
                "description": "Member's deductible",
                "cause_category": "not_a_denial",
                "is_denial": False,
                "expected_overturn_rate": 0.00,
                "defensibility": "high",
            },
            {
                "carc_code": "PR-2",
                "description": "Member's coinsurance",
                "cause_category": "not_a_denial",
                "is_denial": False,
                "expected_overturn_rate": 0.00,
                "defensibility": "high",
            },
            {
                "carc_code": "PR-3",
                "description": "Member's copay",
                "cause_category": "not_a_denial",
                "is_denial": False,
                "expected_overturn_rate": 0.00,
                "defensibility": "high",
            },
            # Eligibility
            {
                "carc_code": "CO-26",
                "description": "Service happened before coverage started",
                "cause_category": "eligibility",
                "is_denial": True,
                "expected_overturn_rate": 0.35,
                "defensibility": "medium",
            },
            {
                "carc_code": "CO-27",
                "description": "Service happened after coverage ended",
                "cause_category": "eligibility",
                "is_denial": True,
                "expected_overturn_rate": 0.35,
                "defensibility": "medium",
            },
            {
                "carc_code": "CO-109",
                "description": "This member isn't ours, or not under this plan",
                "cause_category": "eligibility",
                "is_denial": True,
                "expected_overturn_rate": 0.05,
                "defensibility": "high",
            },
            {
                "carc_code": "CO-22",
                "description": "Another payer should pay first (coordination of benefits)",
                "cause_category": "eligibility",
                "is_denial": True,
                "expected_overturn_rate": 0.15,
                "defensibility": "high",
            },
            # Authorization and credentialing
            {
                "carc_code": "CO-197",
                "description": "No prior authorization on file for this service",
                "cause_category": "authorization",
                "is_denial": True,
                "expected_overturn_rate": 0.70,
                "defensibility": "low",
            },
            {
                "carc_code": "CO-B7",
                "description": "Rendering provider isn't credentialed with us for this service",
                "cause_category": "authorization",
                "is_denial": True,
                "expected_overturn_rate": 0.35,
                "defensibility": "medium",
            },
            # Coding
            {
                "carc_code": "CO-4",
                "description": "The modifier doesn't fit the procedure, or one is missing",
                "cause_category": "coding",
                "is_denial": True,
                "expected_overturn_rate": 0.15,
                "defensibility": "high",
            },
            {
                "carc_code": "CO-11",
                "description": "The diagnosis doesn't support the procedure billed",
                "cause_category": "coding",
                "is_denial": True,
                "expected_overturn_rate": 0.15,
                "defensibility": "high",
            },
            {
                "carc_code": "CO-181",
                "description": "This procedure code wasn't valid on the date of service",
                "cause_category": "coding",
                "is_denial": True,
                "expected_overturn_rate": 0.15,
                "defensibility": "high",
            },
            {
                "carc_code": "CO-97",
                "description": "This service is already included in payment for another service (bundling)",
                "cause_category": "coding",
                "is_denial": True,
                "expected_overturn_rate": 0.20,
                "defensibility": "medium",
            },
            {
                "carc_code": "CO-151",
                "description": "More units billed than we consider plausible in one day",
                "cause_category": "coding",
                "is_denial": True,
                "expected_overturn_rate": 0.20,
                "defensibility": "medium",
            },
            {
                "carc_code": "CO-16",
                "description": "Required information is missing or invalid",
                "cause_category": "coding",
                "is_denial": True,
                "expected_overturn_rate": 0.15,
                "defensibility": "high",
            },
            # Clinical
            {
                "carc_code": "CO-50",
                "description": "Not medically necessary under our policy",
                "cause_category": "clinical",
                "is_denial": True,
                "expected_overturn_rate": 0.70,
                "defensibility": "low",
            },
            {
                "carc_code": "CO-167",
                "description": "This diagnosis isn't covered for this service",
                "cause_category": "clinical",
                "is_denial": True,
                "expected_overturn_rate": 0.35,
                "defensibility": "medium",
            },
            # Benefit design
            {
                "carc_code": "CO-96",
                "description": "Not a covered charge",
                "cause_category": "benefit_design",
                "is_denial": True,
                "expected_overturn_rate": 0.05,
                "defensibility": "high",
            },
            {
                "carc_code": "CO-204",
                "description": "Not covered under this member's plan",
                "cause_category": "benefit_design",
                "is_denial": True,
                "expected_overturn_rate": 0.05,
                "defensibility": "high",
            },
            # Process
            {
                "carc_code": "CO-18",
                "description": "We already have this claim (duplicate)",
                "cause_category": "process",
                "is_denial": True,
                "expected_overturn_rate": 0.05,
                "defensibility": "high",
            },
            {
                "carc_code": "CO-29",
                "description": "Claim arrived past the filing deadline",
                "cause_category": "process",
                "is_denial": True,
                "expected_overturn_rate": 0.05,
                "defensibility": "high",
            },
        ]
    )


if __name__ == "__main__":
    print(get_icd10_codes())
