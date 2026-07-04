"""Scorer de backlog con LLM local (Ollama) — corre en background.

Evalúa todas las vacantes sin score (match_score=0) con el pipeline real
(pre-gates gratis + evaluate_job_match → coordinator → fallback a Ollama).
Prioriza portales ATS (aplicables por API) sobre LinkedIn/Indeed.

Uso:
    venv/bin/python scripts/score_backlog_local.py [--limit N]
Parar:
    touch data/stop_scoring.flag
"""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger

from src.agents.master_agent import evaluate_job_match  # noqa: E402

DB = Path("data/jobsearcher.db")
STOP_FLAG = Path("data/stop_scoring.flag")

QUERY = """
SELECT * FROM jobs
WHERE match_score = 0
  AND status NOT IN ('rejected', 'discarded', 'expired', 'applied', 'skip_location')
ORDER BY
  CASE WHEN url LIKE '%greenhouse%' OR url LIKE '%lever.co%' OR url LIKE '%ashbyhq%'
       THEN 0 ELSE 1 END,
  id
LIMIT ?
"""


def main(limit: int) -> None:
    resume = json.load(open("data/resume.json"))
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    rows = con.execute(QUERY, (limit,)).fetchall()
    logger.info(f"[scorer] backlog: {len(rows)} vacantes por evaluar")

    done = llm_calls = gated = errors = 0
    t_start = time.time()
    for r in rows:
        if STOP_FLAG.exists():
            logger.warning("[scorer] stop flag detectado — saliendo limpio")
            break
        job = dict(r)
        t0 = time.time()
        try:
            score, reason = evaluate_job_match(job, resume)
            dt = time.time() - t0
            if dt < 2:
                gated += 1
            else:
                llm_calls += 1
            con.execute(
                "UPDATE jobs SET match_score=? WHERE id=?",
                (score, job["id"]),
            )
            con.commit()
            done += 1
            logger.info(
                f"[scorer] {done}/{len(rows)} [{dt:.0f}s] score={score} "
                f"{job['company'][:18]} — {job['title'][:45]}"
            )
        except Exception as e:  # noqa: BLE001
            errors += 1
            logger.error(f"[scorer] {job['id'][:10]} error: {str(e)[:120]}")
            if errors > 20:
                logger.error("[scorer] demasiados errores — abortando")
                break

    mins = (time.time() - t_start) / 60
    logger.info(
        f"[scorer] FIN — {done} evaluadas ({llm_calls} LLM, {gated} pre-gate) "
        f"{errors} errores en {mins:.1f} min"
    )
    hi = con.execute(
        "SELECT COUNT(*) FROM jobs WHERE match_score >= 75 AND status='found'"
    ).fetchone()[0]
    logger.info(f"[scorer] vacantes con score>=75 pendientes de revisar: {hi}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100000)
    main(ap.parse_args().limit)
