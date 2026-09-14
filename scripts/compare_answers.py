"""Run a fixed question set through the RAG pipeline and snapshot the results.

Run from the project root:
    python scripts/compare_answers.py --label before   # baseline (hash embeddings)
    python scripts/compare_answers.py --label after    # after switching to Gemini

Each run writes data/comparisons/<label>.json containing, per question:
- the retrieved chunks (doc, page, section, vector score, rerank score)
- the composed context that went to the LLM
- the final answer + citations actually used
plus a small summary (avg top score, retrieval hit rate on expected standard).

Compare two snapshots with:
    python scripts/compare_answers.py --compare before after
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database.base import Base, SessionLocal, engine  # noqa: E402
from app.logging_config import configure_logging  # noqa: E402

configure_logging()

COMPARISON_DIR = Path(__file__).resolve().parent.parent / "data" / "comparisons"

# Fixed evaluation set: (question, mode, expected standard substring)
QUESTIONS = [
    ("What standards and requirements should I check before manufacturing cement?", "industry", "IS 1234"),
    ("How do I check if a safety helmet is BIS certified and what should I look for?", "consumer", "IS 2925"),
    ("What is the setting time requirement for ordinary portland cement?", "industry", "IS 1234"),
    ("How can I identify a genuine ISI mark on a product?", "consumer", "CONSUMER-GUIDE"),
    ("What documents are needed to apply for BIS certification as a manufacturer?", "industry", "BIS-PROCESS"),
    ("What is the shelf life of cement and how should it be stored?", "industry", "IS 1234"),
]


def run(label: str) -> int:
    Base.metadata.create_all(bind=engine)
    from app.api.chat import _extract_cited_markers
    from app.rag.llm import ensure_citations, get_llm_provider
    from app.rag.retrieval import RetrievalService, build_prompt

    db = SessionLocal()
    try:
        provider = get_llm_provider()
        retrieval = RetrievalService()
        print("=" * 72)
        print(f"RAG comparison run: label={label!r}")
        print(f"  embedding_provider={settings.embedding_provider}  llm={provider.name}")
        print("=" * 72)

        results = []
        for question, mode, expected in QUESTIONS:
            t0 = time.perf_counter()
            chunks = retrieval.retrieve(db, question)
            prompt = build_prompt(question, mode, [], chunks)
            try:
                answer = provider.generate(prompt)
            except Exception as exc:  # noqa: BLE001
                answer = f"<LLM ERROR: {exc}>"
            answer = ensure_citations(answer, len(chunks))
            elapsed = time.perf_counter() - t0

            cited = _extract_cited_markers(answer, len(chunks))
            used = [chunks[i - 1] for i in cited if 0 <= i - 1 < len(chunks)]

            top = chunks[0] if chunks else None
            hit = bool(top and expected.lower() in (f"{top.standard_number} {top.document_name}".lower()))
            results.append(
                {
                    "question": question,
                    "mode": mode,
                    "expected_standard": expected,
                    "retrieval_hit": hit,
                    "top_doc": top.document_name if top else None,
                    "top_page": top.page_number if top else None,
                    "top_vector_score": round(float(top.score), 4) if top else None,
                    "top_scores": [round(float(c.score), 4) for c in chunks],
                    "citations_used": [
                        {
                            "document_name": u.document_name,
                            "standard_number": u.standard_number,
                            "page": u.page_number,
                            "section": u.section,
                            "score": round(float(u.score), 4),
                        }
                        for u in used
                    ],
                    "answer": answer,
                    "latency_s": round(elapsed, 2),
                }
            )
            flag = "HIT " if hit else "MISS"
            print(f"[{flag}] {question[:58]}...")
            print(f"       top={top.standard_number if top else '-'} p{top.page_number if top else '-'} "
                  f"score={results[-1]['top_vector_score']} llm={provider.name} {elapsed:.1f}s")

        hits = sum(1 for r in results if r["retrieval_hit"])
        scores = [r["top_vector_score"] for r in results if r["top_vector_score"] is not None]
        summary = {
            "label": label,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "embedding_provider": settings.embedding_provider,
            "llm_provider": provider.name,
            "questions": len(results),
            "retrieval_hits": hits,
            "hit_rate": round(hits / len(results), 3) if results else 0.0,
            "avg_top_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "avg_latency_s": round(sum(r["latency_s"] for r in results) / len(results), 2)
            if results
            else 0.0,
            "results": results,
        }

        COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
        out = COMPARISON_DIR / f"{label}.json"
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print("-" * 72)
        print(f"retrieval hit rate: {summary['hit_rate']:.0%}  avg top score: {summary['avg_top_score']}")
        print(f"saved: {out}")
        return 0
    finally:
        db.close()


def compare(a: str, b: str) -> int:
    pa, pb = COMPARISON_DIR / f"{a}.json", COMPARISON_DIR / f"{b}.json"
    if not pa.exists() or not pb.exists():
        print("Missing snapshot(s). Run with --label before/after first.")
        return 1
    A, B = json.loads(pa.read_text(encoding="utf-8")), json.loads(pb.read_text(encoding="utf-8"))

    print("=" * 72)
    print(f"COMPARISON: {A['label']} ({A['embedding_provider']}/{A['llm_provider']})"
          f"  vs  {B['label']} ({B['embedding_provider']}/{B['llm_provider']})")
    print("=" * 72)
    rows = [
        ("Retrieval hit rate", f"{A['hit_rate']:.0%}", f"{B['hit_rate']:.0%}"),
        ("Avg top score", f"{A['avg_top_score']:.3f}", f"{B['avg_top_score']:.3f}"),
        ("Avg latency (s)", f"{A['avg_latency_s']:.2f}", f"{B['avg_latency_s']:.2f}"),
    ]
    for name, va, vb in rows:
        print(f"{name:<22} {va:>10}   ->   {vb:>10}")

    print("\nPer-question top document / score / citations used:")
    for ra, rb in zip(A["results"], B["results"]):
        print(f"\nQ: {ra['question']}")
        print(f"  BEFORE: {ra['top_doc']} p{ra['top_page']} score={ra['top_vector_score']} "
              f"cited={len(ra['citations_used'])}")
        print(f"  AFTER : {rb['top_doc']} p{rb['top_page']} score={rb['top_vector_score']} "
              f"cited={len(rb['citations_used'])}")
        a_short = re.sub(r"\s+", " ", ra["answer"])[:110]
        b_short = re.sub(r"\s+", " ", rb["answer"])[:110]
        print(f"  answer before: {a_short}...")
        print(f"  answer after : {b_short}...")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG quality comparison harness")
    parser.add_argument("--label", help="snapshot label, e.g. before / after")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"), help="compare two snapshots")
    args = parser.parse_args()
    if args.compare:
        return compare(args.compare[0], args.compare[1])
    if not args.label:
        parser.print_help()
        return 1
    return run(args.label)


if __name__ == "__main__":
    sys.exit(main())
