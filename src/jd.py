"""
jd.py — The job description, translated from prose into structured rules.

This is the single most important file in the project. The whole challenge is
about the GAP between what the JD literally says and what it actually MEANS.
We read job_description.md once, by hand, and encode that understanding here so
the rest of the code can reason about it.

If a teammate or judge asks "why is candidate X ranked where they are?", the
answer should always trace back to something in THIS file.
"""

# ---------------------------------------------------------------------------
# 1. EXPERIENCE BAND
# The JD says "5-9 years (this is a range, not a requirement)" and that the
# imagined ideal is "6-8 years total, 4-5 in applied ML at product companies".
# We reward the sweet spot and softly (not harshly) penalise outside it.
# ---------------------------------------------------------------------------
EXPERIENCE = {
    "ideal_min": 6.0,
    "ideal_max": 8.0,
    "acceptable_min": 5.0,
    "acceptable_max": 9.0,
    # Outside acceptable is allowed ("we'll seriously consider candidates
    # outside the band if other signals are strong") but scored lower.
    "hard_floor": 2.0,   # below this, the "senior" framing really breaks down
}

# ---------------------------------------------------------------------------
# 2. CORE REQUIREMENTS ("Things you absolutely need")
# Each concept has a weight and a list of phrases we look for in the candidate's
# summary + career descriptions + skills. We match CONCEPTS, not single keywords,
# and crucially we read the free-text career descriptions — that is how we catch
# the "plain-language Tier-5 gems" who built the right systems without using the
# trendy vocabulary.
# ---------------------------------------------------------------------------
MUST_HAVE = {
    "embeddings_retrieval": {
        "weight": 3.0,
        "phrases": [
            "embedding", "embeddings", "sentence-transformer", "sentence transformers",
            "bge", "e5", "openai embedding", "semantic search", "dense retrieval",
            "vector representation", "nearest neighbor", "nearest neighbour", "ann ",
        ],
    },
    "vector_db_hybrid_search": {
        "weight": 2.5,
        "phrases": [
            "vector database", "vector db", "pinecone", "weaviate", "qdrant",
            "milvus", "opensearch", "elasticsearch", "faiss", "hybrid search",
            "bm25", "inverted index", "lucene", "solr",
        ],
    },
    "ranking_recsys_search": {
        # The JD's clearest tell: "if their career history shows they built a
        # recommendation system at a product company, they're a fit."
        "weight": 3.0,
        "phrases": [
            "ranking system", "ranker", "re-rank", "rerank", "learning to rank",
            "recommendation system", "recommender", "recommendation engine",
            "search system", "search relevance", "relevance tuning",
            "matching system", "candidate retrieval", "personalization",
            "personalisation", "feed ranking",
        ],
    },
    "evaluation_frameworks": {
        "weight": 2.0,
        "phrases": [
            "ndcg", "mrr", " map ", "mean average precision", "precision@",
            "recall@", "a/b test", "ab test", "offline evaluation", "online evaluation",
            "evaluation framework", "eval framework", "offline metric", "ranking metric",
        ],
    },
    "nlp_ir": {
        # JD rejects CV/speech/robotics WITHOUT NLP/IR exposure, so NLP/IR is core.
        "weight": 2.0,
        "phrases": [
            "nlp", "natural language", "information retrieval", " ir ",
            "text classification", "named entity", "language model", "llm",
            "transformer", "bert", "rag", "retrieval augmented", "retrieval-augmented",
        ],
    },
    "strong_python_production": {
        "weight": 1.5,
        "phrases": [
            "python", "production", "deployed", "deployment", "real users",
            "at scale", "microservice", "api", "pipeline",
        ],
    },
}

# ---------------------------------------------------------------------------
# 3. NICE-TO-HAVE ("we'd like you to have but won't reject you for")
# Small positive bumps only.
# ---------------------------------------------------------------------------
NICE_TO_HAVE = {
    "llm_finetuning": {
        "weight": 0.8,
        "phrases": ["fine-tune", "fine tuning", "fine-tuning", "lora", "qlora",
                    "peft", "instruction tuning"],
    },
    "learning_to_rank_models": {
        "weight": 0.8,
        "phrases": ["xgboost", "lightgbm", "gradient boosted", "learning-to-rank",
                    "lambdamart", "ranknet"],
    },
    "hr_marketplace_tech": {
        "weight": 0.6,
        "phrases": ["hr-tech", "hr tech", "recruiting", "recruitment", "marketplace",
                    "two-sided", "talent"],
    },
    "distributed_scale": {
        "weight": 0.5,
        "phrases": ["distributed", "spark", "kafka", "kubernetes", "inference optimization",
                    "low latency", "high throughput"],
    },
    "open_source": {
        "weight": 0.6,
        "phrases": ["open source", "open-source", "github", "maintainer", "contributor",
                    "published", "paper", "talk at", "conference"],
    },
}

# ---------------------------------------------------------------------------
# 4. DISQUALIFIERS ("Things we explicitly do NOT want")
# These are PENALTIES, the part most teams forget. Each returns a multiplier or
# subtractive penalty applied in scoring. We keep them as detectable signatures.
# ---------------------------------------------------------------------------

# "People who have only worked at consulting/services firms in their entire career."
SERVICES_COMPANIES = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "tech mahindra", "mindtree", "ltimindtree", "mphasis",
    "deloitte", "ibm global services", "dxc", "larsen", "l&t infotech",
    "persistent systems", "hexaware", "birlasoft", "coforge", "zensar",
}

# "primary expertise is computer vision, speech, or robotics without NLP/IR"
WRONG_DOMAIN = {
    "weight": 1.2,
    "phrases": ["computer vision", "image classification", "object detection",
                "speech recognition", "asr ", "robotics", "slam", "lidar",
                "autonomous vehicle", "point cloud", "ocr"],
    # Only a real penalty if NLP/IR signal is ABSENT (checked in scoring).
}

# "AI experience consists primarily of recent (<12 months) LangChain -> OpenAI"
FRAMEWORK_ENTHUSIAST = {
    "phrases": ["langchain", "llamaindex", "auto-gpt", "autogpt", "prompt engineering"],
    # Penalty only when paired with thin/recent experience and no deeper ML history.
}

# "pure research environments without any production deployment"
PURE_RESEARCH = {
    "phrases": ["research scientist", "phd researcher", "research fellow",
                "postdoc", "academic", "university", "research lab", "research-only"],
    # Penalty only when NO production/deployment evidence exists.
}

# Title-chasing: hopping every ~1.5 years for title bumps. Detected from career
# history tenure pattern, not keywords (see features/audit).
TITLE_CHASE_MAX_AVG_TENURE_MONTHS = 20    # avg stint shorter than this is a flag
TITLE_CHASE_MIN_JOBS = 3                   # need a few jobs to call it a pattern

# "senior engineer who hasn't written production code in the last 18 months"
STALE_IC_TITLES = {"architect", "tech lead", "engineering manager", "director",
                   "vp ", "head of", "principal architect"}
CODING_RECENCY_MONTHS = 18

# ---------------------------------------------------------------------------
# 5. LOCATION
# "Pune/Noida preferred; Hyderabad, Pune, Mumbai, Delhi NCR welcome.
#  Outside India: case-by-case, no visa sponsorship."
# ---------------------------------------------------------------------------
LOCATION = {
    "preferred": ["pune", "noida"],
    "welcome": ["hyderabad", "mumbai", "delhi", "ncr", "gurgaon", "gurugram",
                "ghaziabad", "faridabad", "bangalore", "bengaluru"],
    "country_ok": "india",
}

# ---------------------------------------------------------------------------
# 6. BEHAVIORAL EXPECTATIONS (from the JD + signals doc)
# "Active on Redrob platform ... a perfect-on-paper candidate who hasn't logged
#  in for 6 months and has a 5% response rate is not actually available."
# Notice period: "We'd love sub-30-day notice. We can buy out up to 30 days."
# ---------------------------------------------------------------------------
BEHAVIORAL = {
    "preferred_notice_days": 30,
    "max_reasonable_notice_days": 90,
    "active_recent_days": 45,      # logged in within ~6 weeks = healthy
    "stale_days": 180,             # ~6 months = "not actually available"
}

# A single date to treat as "today" so the ranking is reproducible regardless of
# when it runs. Set to just after the dataset's latest activity dates.
REFERENCE_TODAY = "2026-06-01"
