"""Synthetic data generators for ML module cold-start seeding.

Produces realistic ETL step-timing records and labeled NHI classification
examples for training the models when no historical data exists.
"""

import random
from typing import Dict, List, Tuple


# ── ETL timing data ──────────────────────────────────────────────────

_ETL_BASELINES: Dict[str, Tuple[float, float]] = {
    "FREEZE":        (5.0,  1.5),
    "EXPORT":        (30.0, 8.0),
    "TRANSFORM":     (10.0, 3.0),
    "SAFE_CREATION": (8.0,  2.0),
    "IMPORT":        (20.0, 5.0),
    "HEARTBEAT":     (15.0, 4.0),
    "UNFREEZE":      (3.0,  1.0),
}

_PLATFORMS = [
    ("WinServerLocal", 1.0),
    ("WinDomain", 1.2),
    ("UnixSSH", 1.1),
    ("UnixSSHKeys", 1.5),
    ("Oracle", 1.4),
    ("MSSql", 1.3),
    ("AWSAccessKeys", 1.6),
    ("AzureServicePrincipal", 1.7),
]


def generate_etl_timing_data(n: int = 200, seed: int = 42) -> List[Dict]:
    """Generate n ETL step-timing records with ~12% injected anomalies."""
    rng = random.Random(seed)
    records: List[Dict] = []

    for i in range(n):
        wave = rng.choices([1, 2, 3, 4, 5], weights=[20, 25, 25, 15, 15])[0]
        step_name = rng.choice(list(_ETL_BASELINES.keys()))
        base_mean, base_std = _ETL_BASELINES[step_name]

        wave_factor = 1.4 if wave >= 4 else 1.0
        nhi_ratio = rng.uniform(0.3, 0.7) if wave >= 4 else rng.uniform(0.0, 0.2)

        platform_name, plat_factor = rng.choice(_PLATFORMS)
        account_count = rng.randint(5, 80)
        batch_position = rng.randint(1, 10)

        mean = base_mean * wave_factor * plat_factor
        duration = max(0.5, rng.gauss(mean, base_std))

        is_anomaly = rng.random() < 0.12
        if is_anomaly:
            multiplier = rng.uniform(2.0, 5.0)
            duration *= multiplier

        records.append({
            "step_name": step_name,
            "duration": round(duration, 2),
            "account_count": account_count,
            "nhi_ratio": round(nhi_ratio, 3),
            "platform_complexity": round(plat_factor, 2),
            "batch_position": batch_position,
            "wave": wave,
            "is_anomaly": is_anomaly,
        })

    return records


# ── NHI classification data ──────────────────────────────────────────

_NHI_NAME_PREFIXES = ["svc-", "svc_", "app-", "app_", "bot-", "rpa-", "api-"]
_HUMAN_NAME_PREFIXES = ["john.", "jane.", "admin.", "user.", "mgr.", "dev."]


def generate_nhi_labeled_data(n: int = 150, seed: int = 42) -> List[Dict]:
    """Generate n labeled NHI classification examples (~40% NHI, ~60% human)."""
    rng = random.Random(seed)
    records: List[Dict] = []

    for i in range(n):
        is_nhi = rng.random() < 0.40
        is_borderline = rng.random() < 0.15
        is_conflicting = rng.random() < 0.05

        if is_nhi:
            platform_signal = rng.uniform(0.6, 1.0)
            name_signal = rng.uniform(0.5, 1.0)
            container_signal = rng.uniform(0.3, 0.8)
            dependency_signal = rng.uniform(0.4, 0.9)
            audit_signal = rng.uniform(0.3, 0.8)
            name_prefix = rng.choice(_NHI_NAME_PREFIXES)
        else:
            platform_signal = rng.uniform(0.0, 0.3)
            name_signal = rng.uniform(0.0, 0.3)
            container_signal = rng.uniform(0.0, 0.3)
            dependency_signal = rng.uniform(0.0, 0.3)
            audit_signal = rng.uniform(0.0, 0.4)
            name_prefix = rng.choice(_HUMAN_NAME_PREFIXES)

        if is_borderline:
            platform_signal = rng.uniform(0.35, 0.65)
            name_signal = rng.uniform(0.35, 0.65)

        if is_conflicting:
            if is_nhi:
                platform_signal = rng.uniform(0.8, 1.0)
                name_signal = rng.uniform(0.0, 0.2)
            else:
                platform_signal = rng.uniform(0.0, 0.2)
                name_signal = rng.uniform(0.7, 1.0)

        account_name = name_prefix + "".join(
            rng.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=rng.randint(4, 12))
        )

        records.append({
            "platform_signal": round(platform_signal, 3),
            "name_signal": round(name_signal, 3),
            "container_signal": round(container_signal, 3),
            "dependency_signal": round(dependency_signal, 3),
            "audit_signal": round(audit_signal, 3),
            "account_name_length": len(account_name),
            "safe_depth": rng.randint(1, 4),
            "has_linked_accounts": 1.0 if rng.random() < (0.6 if is_nhi else 0.15) else 0.0,
            "is_nhi": is_nhi,
        })

    return records
