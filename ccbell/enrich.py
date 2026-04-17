"""
ccbell.enrich — optional context enrichment (git branch, GPU, Slurm).

Pure functions, never raise. Return empty string on any failure.
Designed to be called from notify.py if the user uncomments the hook.

Input:  cwd (str), environment variables
Output: multi-line context string, or ""
Usage:
    from ccbell.enrich import build_context
    ctx = build_context("/path/to/project")
Created: 2026-04-17
"""

from __future__ import annotations

import os
import subprocess


def git_branch(cwd: str) -> str:
    """Return current git branch name, or ''."""
    try:
        r = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def nvidia_smi_summary() -> str:
    """Return GPU utilization summary like 'GPU 45% 2048/8192MB', or ''."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            parts = r.stdout.strip().split(", ")
            if len(parts) == 3:
                return f"GPU {parts[0].strip()}% {parts[1].strip()}/{parts[2].strip()}MB"
    except Exception:
        pass
    return ""


def slurm_job_info() -> str:
    """Return Slurm job info like 'Slurm 12345 train.py', or ''."""
    job_id = os.environ.get("SLURM_JOB_ID", "")
    if not job_id:
        return ""
    job_name = os.environ.get("SLURM_JOB_NAME", "")
    return f"Slurm {job_id} {job_name}".strip()


def build_context(cwd: str) -> str:
    """Aggregate all context lines. Returns '' if nothing available."""
    lines: list[str] = []
    branch = git_branch(cwd)
    if branch:
        lines.append(f"Git: {branch}")
    gpu = nvidia_smi_summary()
    if gpu:
        lines.append(gpu)
    slurm = slurm_job_info()
    if slurm:
        lines.append(slurm)
    return "\n".join(lines)
