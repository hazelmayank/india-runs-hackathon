"""
reasoning.py — Generate the per-candidate 1-2 sentence justification.

Stage 4 (manual review) checks that reasoning: (1) cites specific facts from the
profile, (2) connects to specific JD requirements, (3) honestly names gaps,
(4) never hallucinates skills/employers not in the profile, (5) varies row to
row, (6) matches the rank's tone.

So we build the sentence DETERMINISTICALLY from facts we actually extracted —
no free-text LLM that could invent things. Every clause is backed by a value we
read from the candidate. Variation comes naturally because it's assembled from
each candidate's own facts and flags.
"""

_CONCEPT_LABEL = {
    "embeddings_retrieval": "embeddings/retrieval",
    "vector_db_hybrid_search": "vector search",
    "ranking_recsys_search": "ranking/recsys",
    "evaluation_frameworks": "ranking evaluation (NDCG/MRR)",
    "nlp_ir": "NLP/IR",
    "strong_python_production": "production Python",
}


def build_reasoning(c, fit_ev, avail_notes, is_honeypot, honeypot_reasons):
    p = c.get("profile", {})
    title = p.get("current_title", "professional")
    yrs = p.get("years_of_experience", 0) or 0

    if is_honeypot:
        return (f"{title} with internal inconsistencies "
                f"({honeypot_reasons[0]}); flagged as likely honeypot and de-ranked.")

    # Positive clause — name the strongest matched JD concepts (specific facts).
    strengths = [_CONCEPT_LABEL[m] for m in fit_ev.get("matched_must", [])
                 if m in _CONCEPT_LABEL][:3]
    loc = p.get("location", "")
    bits = [f"{title} with {yrs:.1f} yrs"]
    if strengths:
        bits.append("strength in " + ", ".join(strengths))
    if fit_ev.get("product_ratio", 0) >= 0.5:
        bits.append("product-company background")
    head = "; ".join(bits)

    # Honest concerns — surface real gaps/penalties and availability issues.
    concerns = []
    concerns.extend(fit_ev.get("penalties", [])[:2])
    if not strengths:
        concerns.append("limited direct retrieval/ranking evidence")
    concerns.extend(avail_notes[:1])
    if loc:
        lo = loc.lower()
        if not any(city in lo for city in
                   ("pune", "noida", "hyderabad", "mumbai", "delhi", "bangalore",
                    "bengaluru", "gurgaon", "gurugram", "ncr")):
            concerns.append(f"based in {loc}")

    if concerns:
        return f"{head}. Concerns: {'; '.join(concerns[:3])}."
    return f"{head}. Strong all-round fit against the JD's core requirements."
