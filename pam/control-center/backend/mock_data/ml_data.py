"""
Mock ML module data for the SHIFT Migration Control Center.

Simulates output from core/ml/ — ETL anomaly detection (EWMA + Isolation Forest)
and NHI classification blending (LightGBM + rule blending).
"""

ML_STATUS = {
    "enabled": True,
    "version": "0.1.0",
    "etl_detector": {
        "state": "warm",
        "training_samples": 147,
        "anomalies_detected": 8,
        "last_retrained": "2026-02-28T14:22:00Z",
        "model_type": "EWMA + Isolation Forest",
        "ewma_alpha": 0.3,
        "if_contamination": 0.1,
        "blend_weight_ewma": 0.4,
        "blend_weight_if": 0.6,
    },
    "nhi_classifier": {
        "state": "warm",
        "training_samples": 83,
        "human_corrections": 7,
        "accuracy": 0.91,
        "last_retrained": "2026-02-27T09:15:00Z",
        "model_type": "LightGBM + Rule Blending",
        "blend_weights": {"rules": 0.6, "ml": 0.4},
    },
}


# ── Per-wave ETL anomaly data ────────────────────────────────────────
# Each entry: step name, EWMA z-score, Isolation Forest score,
# blended score (0.4*ewma_norm + 0.6*if), and explanation.
# Blended >= 0.55 = anomaly flag.

ETL_ANOMALIES = {
    "1": [],  # Wave 1 (Test/Dev): clean run, no anomalies
    "2": [
        {
            "step": "TRANSFORM",
            "ewma_z": 2.4,
            "if_score": 0.72,
            "blended": 0.61,
            "flagged": True,
            "explanation": "Transform duration 3.1x above EWMA baseline — Oracle platform mapping added unexpected field conversions",
        },
    ],
    "3": [
        {
            "step": "IMPORT",
            "ewma_z": 2.8,
            "if_score": 0.68,
            "blended": 0.63,
            "flagged": True,
            "explanation": "Import latency spike — domain controller accounts triggered additional AD validation calls",
        },
        {
            "step": "HEARTBEAT",
            "ewma_z": 1.9,
            "if_score": 0.74,
            "blended": 0.58,
            "flagged": True,
            "explanation": "Heartbeat response time 2x baseline — firewall accounts require extended connectivity checks",
        },
    ],
    "4": [
        {
            "step": "EXPORT",
            "ewma_z": 2.1,
            "if_score": 0.65,
            "blended": 0.55,
            "flagged": True,
            "explanation": "Export batch size anomaly — NHI service accounts have more linked account references than human accounts",
        },
        {
            "step": "TRANSFORM",
            "ewma_z": 3.2,
            "if_score": 0.81,
            "blended": 0.74,
            "flagged": True,
            "explanation": "Transform pipeline stall — WinServiceAccount platform requires NHI-specific field injection (owner, rotation policy, dependency list)",
        },
        {
            "step": "HEARTBEAT",
            "ewma_z": 2.6,
            "if_score": 0.77,
            "blended": 0.67,
            "flagged": True,
            "explanation": "Heartbeat failure rate 18% — NHI accounts with expired rotation schedules failing initial connectivity",
        },
    ],
    "5": [],  # Wave 5 (NHI+CCP/AAM): clean after Wave 4 learnings applied
}


# ── Per-step baseline scores (non-anomalous) ────────────────────────
# Used by the frontend to render score bars for all steps in a wave.
ETL_STEP_BASELINES = {
    "FREEZE":    {"ewma_z": 0.3, "if_score": 0.08, "blended": 0.05},
    "EXPORT":    {"ewma_z": 0.7, "if_score": 0.15, "blended": 0.12},
    "TRANSFORM": {"ewma_z": 0.5, "if_score": 0.12, "blended": 0.09},
    "CREATE":    {"ewma_z": 0.4, "if_score": 0.10, "blended": 0.07},
    "IMPORT":    {"ewma_z": 0.6, "if_score": 0.14, "blended": 0.11},
    "HEARTBEAT": {"ewma_z": 0.8, "if_score": 0.18, "blended": 0.14},
    "UNFREEZE":  {"ewma_z": 0.2, "if_score": 0.06, "blended": 0.04},
}


# ── Per-account ML classification data ──────────────────────────────
# source: "rule_only" (ML cold start), "blended" (ML active), "human_corrected"
# rule_score: Agent 12 weighted signal score (0.0 = human, 1.0 = definite NHI)
# ml_confidence: LightGBM prediction (None if cold start)
# blended_score: weighted combo (None if rule_only)

ACCOUNT_ML = {
    # Wave 1: Test/Dev — all rule-only (ML cold start), low NHI scores
    "ACC-00001": {"rule_score": 0.05, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00002": {"rule_score": 0.03, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00003": {"rule_score": 0.08, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00004": {"rule_score": 0.04, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00005": {"rule_score": 0.02, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00006": {"rule_score": 0.06, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00007": {"rule_score": 0.07, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00008": {"rule_score": 0.04, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00009": {"rule_score": 0.11, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00010": {"rule_score": 0.03, "ml_confidence": None, "blended_score": None, "source": "rule_only"},

    # Wave 2: Standard — rule-only, low NHI scores
    "ACC-00011": {"rule_score": 0.09, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00012": {"rule_score": 0.06, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00013": {"rule_score": 0.02, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00014": {"rule_score": 0.04, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00015": {"rule_score": 0.07, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00016": {"rule_score": 0.05, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00017": {"rule_score": 0.03, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00018": {"rule_score": 0.02, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00019": {"rule_score": 0.06, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00020": {"rule_score": 0.04, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00021": {"rule_score": 0.05, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00022": {"rule_score": 0.08, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00023": {"rule_score": 0.07, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00024": {"rule_score": 0.03, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00025": {"rule_score": 0.05, "ml_confidence": None, "blended_score": None, "source": "rule_only"},

    # Wave 3: Infrastructure — ML starts warming up, first blended results
    "ACC-00026": {"rule_score": 0.10, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00027": {"rule_score": 0.08, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00028": {"rule_score": 0.12, "ml_confidence": None, "blended_score": None, "source": "rule_only"},
    "ACC-00029": {"rule_score": 0.09, "ml_confidence": 0.07, "blended_score": 0.08, "source": "blended"},
    "ACC-00030": {"rule_score": 0.11, "ml_confidence": 0.05, "blended_score": 0.09, "source": "blended"},
    "ACC-00031": {"rule_score": 0.06, "ml_confidence": 0.04, "blended_score": 0.05, "source": "blended"},
    "ACC-00032": {"rule_score": 0.14, "ml_confidence": 0.10, "blended_score": 0.12, "source": "blended"},
    "ACC-00033": {"rule_score": 0.07, "ml_confidence": 0.06, "blended_score": 0.07, "source": "blended"},
    "ACC-00034": {"rule_score": 0.05, "ml_confidence": 0.03, "blended_score": 0.04, "source": "blended"},
    "ACC-00035": {"rule_score": 0.08, "ml_confidence": 0.09, "blended_score": 0.08, "source": "blended"},

    # Wave 4: NHI (no CCP/AAM) — ML active, high scores, blended
    "ACC-00036": {"rule_score": 0.95, "ml_confidence": 0.93, "blended_score": 0.94, "source": "blended"},
    "ACC-00037": {"rule_score": 0.92, "ml_confidence": 0.89, "blended_score": 0.91, "source": "blended"},
    "ACC-00038": {"rule_score": 0.88, "ml_confidence": 0.91, "blended_score": 0.89, "source": "blended"},
    "ACC-00039": {"rule_score": 0.91, "ml_confidence": 0.88, "blended_score": 0.90, "source": "blended"},
    "ACC-00040": {"rule_score": 0.93, "ml_confidence": 0.90, "blended_score": 0.92, "source": "blended"},
    "ACC-00041": {"rule_score": 0.87, "ml_confidence": 0.84, "blended_score": 0.86, "source": "blended"},
    "ACC-00042": {"rule_score": 0.78, "ml_confidence": 0.71, "blended_score": 0.75, "source": "blended"},
    "ACC-00043": {"rule_score": 0.85, "ml_confidence": 0.82, "blended_score": 0.84, "source": "blended"},

    # Wave 5: NHI (CCP/AAM) — human-corrected (most critical, manual review)
    "ACC-00044": {"rule_score": 0.97, "ml_confidence": 0.95, "blended_score": 0.96, "source": "human_corrected"},
    "ACC-00045": {"rule_score": 0.96, "ml_confidence": 0.94, "blended_score": 0.95, "source": "human_corrected"},
    "ACC-00046": {"rule_score": 0.94, "ml_confidence": 0.91, "blended_score": 0.93, "source": "human_corrected"},
    "ACC-00047": {"rule_score": 0.90, "ml_confidence": 0.87, "blended_score": 0.89, "source": "human_corrected"},
    "ACC-00048": {"rule_score": 0.96, "ml_confidence": 0.93, "blended_score": 0.95, "source": "human_corrected"},
    "ACC-00049": {"rule_score": 0.94, "ml_confidence": 0.92, "blended_score": 0.93, "source": "human_corrected"},
    "ACC-00050": {"rule_score": 0.89, "ml_confidence": 0.86, "blended_score": 0.88, "source": "human_corrected"},
}


# ── Summary statistics ──────────────────────────────────────────────
ML_SUMMARY = {
    "total_accounts": 50,
    "rule_only": 28,
    "blended": 15,
    "human_corrected": 7,
    "anomalies_by_wave": {
        "1": 0,
        "2": 1,
        "3": 2,
        "4": 3,
        "5": 0,
    },
}
