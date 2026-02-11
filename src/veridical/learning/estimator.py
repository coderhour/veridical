"""Difficulty estimator that predicts iteration count based on historical similarity."""

import json
import logging
import math
import re
from collections import Counter
from pathlib import Path

from veridical.learning.models import DifficultyEstimate, SimilarTask

logger = logging.getLogger(__name__)

# Stop words to exclude from keyword extraction
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "when",
        "while",
        "for",
        "of",
        "at",
        "by",
        "from",
        "to",
        "in",
        "on",
        "with",
        "as",
        "into",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "not",
        "no",
        "so",
        "too",
        "very",
        "just",
        "also",
        "than",
        "more",
        "most",
        "fix",
        "add",
        "update",
        "change",
        "make",
        "create",
        "implement",
    }
)

_WORD_RE = re.compile(r"[a-z][a-z0-9_]+")


class DifficultyEstimator:
    """Predicts iteration count for new tasks based on historical similarity."""

    def __init__(self, default_max_iterations: int = 10) -> None:
        """Initialize the estimator.

        Args:
            default_max_iterations: Default max iterations from config, used for fallback.
        """
        self.default_max_iterations = default_max_iterations

    def predict(self, task_description: str, worklog_dir: Path) -> DifficultyEstimate:
        """Predict difficulty for a task based on historical data.

        Args:
            task_description: Description of the new task.
            worklog_dir: Path to the worklog directory.

        Returns:
            DifficultyEstimate with predicted iterations and similar tasks.
        """
        historical = self._load_historical_tasks(worklog_dir)

        if not historical:
            return DifficultyEstimate(
                predicted_iterations=self.default_max_iterations // 2,
                confidence="low",
                similar_tasks=[],
            )

        # Find similar tasks
        similar = self._find_similar_tasks(task_description, historical)

        if not similar:
            return DifficultyEstimate(
                predicted_iterations=self.default_max_iterations // 2,
                confidence="low",
                similar_tasks=[],
            )

        # Predict iterations from similar tasks (weighted average by similarity)
        total_weight = sum(t.similarity_score for t in similar)
        if total_weight > 0:
            predicted = sum(t.iterations_taken * t.similarity_score for t in similar) / total_weight
        else:
            predicted = self.default_max_iterations // 2

        # Determine confidence based on similarity scores
        max_similarity = similar[0].similarity_score if similar else 0.0
        if max_similarity >= 0.6 and len(similar) >= 3:
            confidence = "high"
        elif max_similarity >= 0.3 and len(similar) >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return DifficultyEstimate(
            predicted_iterations=max(1, round(predicted)),
            confidence=confidence,
            similar_tasks=similar[:5],
        )

    def _load_historical_tasks(self, worklog_dir: Path) -> list[dict]:
        """Load historical task data grouped by run."""
        if not worklog_dir.exists():
            return []

        # Group entries by session to get per-run stats
        runs: dict[str, dict] = {}

        for jsonl_file in sorted(worklog_dir.rglob("iterations.jsonl")):
            try:
                with jsonl_file.open() as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        session_id = entry.get("session_id", "unknown")
                        timestamp = entry.get("timestamp", "")
                        date_part = timestamp[:10] if timestamp else "unknown"
                        run_key = f"{session_id}:{date_part}"

                        if run_key not in runs:
                            runs[run_key] = {
                                "task_description": entry.get("task_description", ""),
                                "iterations": 0,
                                "succeeded": False,
                            }

                        runs[run_key]["iterations"] = max(
                            runs[run_key]["iterations"],
                            entry.get("iteration", 0),
                        )

                        if entry.get("verification_passed"):
                            runs[run_key]["succeeded"] = True

            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read {jsonl_file}: {e}")

        return list(runs.values())

    def _find_similar_tasks(
        self, task_description: str, historical: list[dict]
    ) -> list[SimilarTask]:
        """Find historically similar tasks using keyword overlap (TF-IDF-like)."""
        query_keywords = self._extract_keywords(task_description)
        if not query_keywords:
            return []

        # Build document frequency
        doc_freq: Counter[str] = Counter()
        for run in historical:
            keywords = set(self._extract_keywords(run.get("task_description", "")))
            for kw in keywords:
                doc_freq[kw] += 1

        n_docs = len(historical)
        similar: list[SimilarTask] = []

        for run in historical:
            hist_keywords = self._extract_keywords(run.get("task_description", ""))
            if not hist_keywords:
                continue

            score = self._tfidf_similarity(query_keywords, hist_keywords, doc_freq, n_docs)

            if score > 0.1:
                similar.append(
                    SimilarTask(
                        task_description=run.get("task_description", ""),
                        iterations_taken=run.get("iterations", 1),
                        succeeded=run.get("succeeded", False),
                        similarity_score=round(min(1.0, score), 2),
                    )
                )

        return sorted(similar, key=lambda t: t.similarity_score, reverse=True)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        words = _WORD_RE.findall(text.lower())
        return [w for w in words if w not in _STOP_WORDS and len(w) > 2]

    def _tfidf_similarity(
        self,
        query: list[str],
        doc: list[str],
        doc_freq: Counter[str],
        n_docs: int,
    ) -> float:
        """Compute TF-IDF cosine similarity between query and document."""
        query_set = set(query)
        doc_set = set(doc)
        common = query_set & doc_set

        if not common:
            return 0.0

        # IDF-weighted overlap
        score = 0.0
        for term in common:
            df = doc_freq.get(term, 1)
            idf = math.log(1 + n_docs / df)
            score += idf

        # Normalize by geometric mean of vector lengths
        query_norm = math.sqrt(
            sum(math.log(1 + n_docs / doc_freq.get(t, 1)) ** 2 for t in query_set)
        )
        doc_norm = math.sqrt(sum(math.log(1 + n_docs / doc_freq.get(t, 1)) ** 2 for t in doc_set))

        if query_norm == 0 or doc_norm == 0:
            return 0.0

        return score / (query_norm * doc_norm)
