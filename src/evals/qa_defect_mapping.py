"""QA Defect Mapping Eval — maps QA defects to acceptance criteria.

Classifies unmapped defects as intent_gap (criterion missing) or
implementation_bug (criterion present but failed).
"""

import re

from src.evals.framework import EvalCase, EvalResult, EvalSuite, EvalType


def _extract_terms(text: str) -> set[str]:
    """Extract meaningful terms from text for matching."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "have",
        "has", "had", "do", "does", "did", "will", "would", "could", "should",
        "may", "might", "shall", "can", "need", "must", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "and", "but", "or",
        "not", "that", "this", "it", "its", "which", "what", "who", "how",
    }
    words = re.findall(r"[a-z][a-z_\-]{2,}", text.lower())
    return {w for w in words if w not in stop_words}


def _match_defect_to_criteria(
    defect_text: str, criteria: list[str]
) -> int | None:
    """Find the best matching criterion index for a defect. Returns None if no match."""
    defect_terms = _extract_terms(defect_text)
    if not defect_terms:
        return None

    best_idx = None
    best_overlap = 0.0

    for i, criterion in enumerate(criteria):
        criterion_terms = _extract_terms(criterion)
        if not criterion_terms:
            continue
        overlap = len(defect_terms & criterion_terms) / len(defect_terms)
        if overlap > best_overlap and overlap >= 0.3:
            best_overlap = overlap
            best_idx = i

    return best_idx


class QADefectMappingEval(EvalSuite):
    """Evaluates mapping of QA defects to acceptance criteria.

    Input data format:
        acceptance_criteria: list[str] — the acceptance criteria
        qa_defects: list[dict] — defects with:
            description: str — defect description
            category: str — defect category
            severity: str — defect severity (s0-s3)

    Expected output format:
        unmapped_classification: dict[str, int] — counts of intent_gap vs implementation_bug
    """

    eval_type = EvalType.QA_DEFECT_MAPPING

    def run(self, cases: list[EvalCase]) -> list[EvalResult]:
        results = []
        for case in cases:
            if case.eval_type != self.eval_type:
                continue
            results.append(self._evaluate_case(case))
        return results

    def _evaluate_case(self, case: EvalCase) -> EvalResult:
        criteria = case.input_data.get("acceptance_criteria", [])
        defects = case.input_data.get("qa_defects", [])

        mapped: list[dict] = []
        unmapped: list[dict] = []
        intent_gaps = 0
        implementation_bugs = 0

        for defect in defects:
            description = defect.get("description", "")
            match_idx = _match_defect_to_criteria(description, criteria)

            if match_idx is not None:
                mapped.append({
                    "defect": description,
                    "criterion_index": match_idx,
                    "criterion": criteria[match_idx],
                    "classification": "implementation_bug",
                })
                implementation_bugs += 1
            else:
                unmapped.append({
                    "defect": description,
                    "classification": "intent_gap",
                })
                intent_gaps += 1

        total = len(defects)
        coverage_score = len(mapped) / total if total else 1.0

        expected = case.expected_output.get("unmapped_classification", {})
        label_correct = True
        failure_reason = None

        if expected:
            expected_gaps = expected.get("intent_gap", 0)
            expected_bugs = expected.get("implementation_bug", 0)
            if intent_gaps != expected_gaps or implementation_bugs != expected_bugs:
                label_correct = False
                failure_reason = (
                    f"Expected intent_gap={expected_gaps}, implementation_bug={expected_bugs} "
                    f"but got intent_gap={intent_gaps}, implementation_bug={implementation_bugs}"
                )

        return EvalResult(
            case_id=case.id,
            eval_type=self.eval_type,
            passed=label_correct,
            score=round(coverage_score, 3),
            details={
                "total_defects": total,
                "mapped_count": len(mapped),
                "unmapped_count": len(unmapped),
                "mapped": mapped,
                "unmapped": unmapped,
                "intent_gaps": intent_gaps,
                "implementation_bugs": implementation_bugs,
                "coverage_score": round(coverage_score, 3),
            },
            failure_reason=failure_reason,
        )
