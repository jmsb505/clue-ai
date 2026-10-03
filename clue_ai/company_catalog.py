from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

GROUP_LABELS = {
    "italian-ai": "Italian AI",
    "italian-tech": "Italian technology",
    "europe-ai": "European AI",
    "data-platform": "Data and ML platforms",
    "global-tech": "Global technology",
}

ROLE_LABELS = {
    "ai_ml": "AI / ML",
    "applied_ai": "Applied AI",
    "llm_nlp": "LLM / NLP",
    "data_analytics": "Data / analytics",
    "data_engineering": "Data engineering",
    "ml_platform": "ML platform / MLOps",
    "ai_product": "AI product / solutions",
    "robotics": "Robotics",
    "research": "Research",
}

DISCOVERY_SOURCES = {
    "europe-ai": {
        "label": "Sifted AI 100 company discovery list",
        "url": "https://sifted.eu/rankings/ai-100-2025",
    },
    "italian-ai": {
        "label": "Italian AI ecosystem map and market research",
        "url": "https://aixia.it/en/ricerca/ecosistema-ai-italiano/",
    },
    "italian-tech": {
        "label": "Italian AI market and employer research",
        "url": "https://www.osservatori.net/comunicato/artificial-intelligence/intelligenza-artificiale-italia/",
    },
    "data-platform": {
        "label": "AI and data infrastructure company map",
        "url": "https://sifted.eu/rankings/ai-100-2025",
    },
    "global-tech": {
        "label": "Italian AI and high-skill job-market research",
        "url": "https://www.osservatori.net/comunicato/artificial-intelligence/intelligenza-artificiale-italia/",
    },
}


def _seed(
    company_id: str,
    name: str,
    homepage_url: str,
    group: str,
    roles: str,
    careers_url: str = "",
    board_url: str = "",
    provider: str = "",
) -> dict[str, Any]:
    discovery = DISCOVERY_SOURCES[group]
    return {
        "id": company_id,
        "name": name,
        "homepage_url": homepage_url,
        "careers_url": careers_url,
        "board_url": board_url,
        "provider": provider,
        "group_id": group,
        "role_tags": tuple(roles.split()),
        "discovery_source": discovery["label"],
        "discovery_url": discovery["url"],
    }


# These are employer leads, not claims that a job is open or can be done from Italy.
# Only ATS details observed on official career pages are filled in; other boards are
# resolved from the employer's own site during a search.
COMPANY_SEEDS = (
    _seed(
        "domyn",
        "Domyn",
        "https://www.domyn.com/",
        "italian-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform",
        "https://www.domyn.com/careers/roles",
    ),
    _seed(
        "aindo",
        "Aindo",
        "https://www.aindo.com/",
        "italian-ai",
        "ai_ml applied_ai data_engineering research",
        "https://www.aindo.com/careers/",
    ),
    _seed(
        "expert-ai",
        "Expert.ai",
        "https://www.expert.ai/",
        "italian-ai",
        "ai_ml applied_ai llm_nlp data_engineering",
        "https://www.expert.ai/careers/",
    ),
    _seed(
        "almawave",
        "Almawave",
        "https://www.almawave.com/",
        "italian-ai",
        "ai_ml applied_ai llm_nlp data_engineering",
        "https://www.almawave.com/join-us/",
    ),
    _seed(
        "datrix",
        "Datrix",
        "https://www.datrixgroup.com/",
        "italian-ai",
        "ai_ml applied_ai data_analytics data_engineering ai_product",
    ),
    _seed(
        "akamas",
        "Akamas",
        "https://akamas.io/",
        "italian-ai",
        "ai_ml ml_platform data_engineering ai_product",
        "https://careers.akamas.io/",
        "https://careers.akamas.io/",
        "Teamtailor",
    ),
    _seed(
        "axyon-ai",
        "Axyon AI",
        "https://axyon.ai/",
        "italian-ai",
        "ai_ml applied_ai data_analytics data_engineering research",
        "https://axyon.ai/careers",
    ),
    _seed(
        "aiko", "AIKO", "https://aikospace.com/", "italian-ai", "ai_ml applied_ai robotics research"
    ),
    _seed(
        "aptus-ai",
        "Aptus.AI",
        "https://www.aptus.ai/",
        "italian-ai",
        "ai_ml applied_ai llm_nlp ai_product",
    ),
    _seed(
        "babelscape",
        "Babelscape",
        "https://babelscape.com/",
        "italian-ai",
        "ai_ml applied_ai llm_nlp research",
    ),
    _seed(
        "clearbox-ai",
        "Clearbox AI",
        "https://clearbox.ai/",
        "italian-ai",
        "ai_ml applied_ai research",
    ),
    _seed(
        "indigo-ai",
        "Indigo.ai",
        "https://indigo.ai/",
        "italian-ai",
        "ai_ml applied_ai llm_nlp ai_product",
    ),
    _seed(
        "latitudo40",
        "Latitudo 40",
        "https://www.latitudo40.com/",
        "italian-ai",
        "ai_ml applied_ai data_analytics research",
    ),
    _seed(
        "next-vision",
        "Next Vision",
        "https://www.nextvision.it/",
        "italian-ai",
        "ai_ml applied_ai robotics research",
    ),
    _seed(
        "questit",
        "QuestIT",
        "https://www.quest-it.com/",
        "italian-ai",
        "ai_ml applied_ai llm_nlp ai_product",
    ),
    _seed(
        "intuendi",
        "Intuendi",
        "https://intuendi.com/",
        "italian-ai",
        "ai_ml applied_ai data_analytics data_engineering",
    ),
    _seed(
        "tuidi",
        "Tuidi",
        "https://tuidi.ai/",
        "italian-ai",
        "ai_ml applied_ai data_analytics data_engineering",
    ),
    _seed(
        "bigprofiles",
        "BigProfiles",
        "https://www.bigprofiles.com/",
        "italian-ai",
        "ai_ml applied_ai data_analytics ai_product",
    ),
    _seed(
        "bending-spoons",
        "Bending Spoons",
        "https://bendingspoons.com/",
        "italian-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "reply",
        "Reply",
        "https://www.reply.com/",
        "italian-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "ntt-data",
        "NTT DATA",
        "https://www.nttdata.com/",
        "italian-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "engineering",
        "Engineering Group",
        "https://www.eng.it/",
        "italian-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "accenture",
        "Accenture",
        "https://www.accenture.com/",
        "italian-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "capgemini",
        "Capgemini",
        "https://www.capgemini.com/",
        "italian-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "deloitte",
        "Deloitte",
        "https://www.deloitte.com/",
        "italian-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "leonardo",
        "Leonardo",
        "https://www.leonardo.com/",
        "italian-tech",
        "ai_ml applied_ai data_engineering ml_platform robotics research",
    ),
    _seed(
        "stmicroelectronics",
        "STMicroelectronics",
        "https://www.st.com/",
        "italian-tech",
        "ai_ml applied_ai data_engineering ml_platform robotics research",
    ),
    _seed(
        "tim",
        "TIM",
        "https://www.gruppotim.it/",
        "italian-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform",
    ),
    _seed(
        "eni",
        "Eni",
        "https://www.eni.com/",
        "italian-tech",
        "ai_ml applied_ai data_analytics data_engineering robotics research",
    ),
    _seed(
        "intesasanpaolo",
        "Intesa Sanpaolo",
        "https://group.intesasanpaolo.com/",
        "italian-tech",
        "ai_ml applied_ai data_analytics data_engineering ai_product",
    ),
    _seed(
        "satispay",
        "Satispay",
        "https://www.satispay.com/",
        "italian-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "banca-sella",
        "Banca Sella",
        "https://www.sella.it/",
        "italian-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform",
    ),
    _seed(
        "d-orbit",
        "D-Orbit",
        "https://www.dorbit.space/",
        "italian-tech",
        "ai_ml applied_ai data_engineering ml_platform robotics research",
    ),
    _seed(
        "mistral-ai",
        "Mistral AI",
        "https://mistral.ai/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
        "https://mistral.ai/careers/",
        provider="Ashby",
    ),
    _seed(
        "deepl",
        "DeepL",
        "https://www.deepl.com/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
        "https://www.deepl.com/en/careers",
    ),
    _seed(
        "hugging-face",
        "Hugging Face",
        "https://huggingface.co/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
    ),
    _seed(
        "aleph-alpha",
        "Aleph Alpha",
        "https://aleph-alpha.com/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
    ),
    _seed(
        "black-forest-labs",
        "Black Forest Labs",
        "https://blackforestlabs.ai/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp research",
    ),
    _seed(
        "multiverse-computing",
        "Multiverse Computing",
        "https://multiversecomputing.com/",
        "europe-ai",
        "ai_ml applied_ai data_engineering ml_platform research",
        "https://multiversecomputing.teamtailor.com/",
        "https://multiversecomputing.teamtailor.com/",
        "Teamtailor",
    ),
    _seed(
        "cuspai",
        "CuspAI",
        "https://www.cusp.ai/",
        "europe-ai",
        "ai_ml applied_ai data_engineering research",
    ),
    _seed(
        "physicsx",
        "PhysicsX",
        "https://physicsx.ai/",
        "europe-ai",
        "ai_ml applied_ai data_engineering ml_platform research",
    ),
    _seed(
        "neura-robotics",
        "NEURA Robotics",
        "https://neura-robotics.com/",
        "europe-ai",
        "ai_ml applied_ai robotics research",
    ),
    _seed(
        "cradle",
        "Cradle",
        "https://cradle.bio/",
        "europe-ai",
        "ai_ml applied_ai data_engineering research",
    ),
    _seed(
        "polyai",
        "PolyAI",
        "https://poly.ai/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering research",
    ),
    _seed(
        "encord",
        "Encord",
        "https://encord.com/",
        "europe-ai",
        "ai_ml applied_ai data_engineering ml_platform",
    ),
    _seed(
        "nabla",
        "Nabla",
        "https://www.nabla.com/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering research",
    ),
    _seed(
        "flexai",
        "FlexAI",
        "https://www.flex.ai/",
        "europe-ai",
        "ai_ml applied_ai data_engineering ml_platform research",
    ),
    _seed(
        "h-company",
        "H Company",
        "https://www.hcompany.ai/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp ml_platform research",
    ),
    _seed(
        "basecamp-research",
        "Basecamp Research",
        "https://basecampresearch.com/",
        "europe-ai",
        "ai_ml applied_ai data_engineering research",
    ),
    _seed(
        "photoroom",
        "Photoroom",
        "https://www.photoroom.com/",
        "europe-ai",
        "ai_ml applied_ai data_engineering ml_platform ai_product",
    ),
    _seed(
        "tandem-health",
        "Tandem Health",
        "https://www.tandemhealth.ai/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ai_product",
    ),
    _seed(
        "bioptimus",
        "Bioptimus",
        "https://www.bioptimus.com/",
        "europe-ai",
        "ai_ml applied_ai data_engineering research",
    ),
    _seed(
        "lighton",
        "LightOn",
        "https://www.lighton.ai/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
    ),
    _seed(
        "axelera-ai",
        "Axelera AI",
        "https://axelera.ai/",
        "europe-ai",
        "ai_ml applied_ai data_engineering ml_platform robotics research",
        "https://axelera.ai/careers",
    ),
    _seed(
        "sereact",
        "Sereact",
        "https://sereact.ai/",
        "europe-ai",
        "ai_ml applied_ai robotics research",
    ),
    _seed(
        "synthesia",
        "Synthesia",
        "https://www.synthesia.io/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform ai_product",
    ),
    _seed(
        "elevenlabs",
        "ElevenLabs",
        "https://elevenlabs.io/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
    ),
    _seed(
        "poolside",
        "Poolside",
        "https://poolside.ai/",
        "europe-ai",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
    ),
    _seed(
        "qdrant",
        "Qdrant",
        "https://qdrant.tech/",
        "data-platform",
        "ai_ml applied_ai data_engineering ml_platform",
        "https://jobs.ashbyhq.com/qdrant.tech",
        "https://jobs.ashbyhq.com/qdrant.tech",
        "Ashby",
    ),
    _seed(
        "deepset",
        "deepset",
        "https://www.deepset.ai/",
        "data-platform",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform",
        "https://deepset.jobs.personio.com/",
        "https://deepset.jobs.personio.com/",
        "Personio",
    ),
    _seed(
        "weaviate",
        "Weaviate",
        "https://weaviate.io/",
        "data-platform",
        "ai_ml applied_ai data_engineering ml_platform",
    ),
    _seed(
        "langfuse",
        "Langfuse",
        "https://langfuse.com/",
        "data-platform",
        "ai_ml applied_ai data_engineering ml_platform",
    ),
    _seed(
        "dataiku",
        "Dataiku",
        "https://www.dataiku.com/",
        "data-platform",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
        "https://www.dataiku.com/company/careers",
    ),
    _seed(
        "databricks",
        "Databricks",
        "https://www.databricks.com/",
        "data-platform",
        "ai_ml applied_ai data_analytics data_engineering ml_platform",
    ),
    _seed(
        "snowflake",
        "Snowflake",
        "https://www.snowflake.com/",
        "data-platform",
        "ai_ml applied_ai data_analytics data_engineering ml_platform",
    ),
    _seed(
        "mongodb",
        "MongoDB",
        "https://www.mongodb.com/",
        "data-platform",
        "ai_ml applied_ai data_engineering ml_platform",
    ),
    _seed(
        "elastic",
        "Elastic",
        "https://www.elastic.co/",
        "data-platform",
        "ai_ml applied_ai data_engineering ml_platform",
    ),
    _seed(
        "confluent",
        "Confluent",
        "https://www.confluent.io/",
        "data-platform",
        "ai_ml applied_ai data_engineering ml_platform",
    ),
    _seed(
        "grafana-labs",
        "Grafana Labs",
        "https://grafana.com/",
        "data-platform",
        "ai_ml applied_ai data_engineering ml_platform",
    ),
    _seed(
        "dbt-labs",
        "dbt Labs",
        "https://www.getdbt.com/",
        "data-platform",
        "ai_ml data_analytics data_engineering ml_platform",
    ),
    _seed(
        "prefect",
        "Prefect",
        "https://www.prefect.io/",
        "data-platform",
        "ai_ml data_engineering ml_platform",
    ),
    _seed(
        "dagster",
        "Dagster",
        "https://dagster.io/",
        "data-platform",
        "ai_ml data_engineering ml_platform",
    ),
    _seed(
        "google",
        "Google / DeepMind",
        "https://careers.google.com/",
        "global-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform robotics research",
    ),
    _seed(
        "microsoft",
        "Microsoft",
        "https://careers.microsoft.com/",
        "global-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform research",
    ),
    _seed(
        "nvidia",
        "NVIDIA",
        "https://www.nvidia.com/",
        "global-tech",
        "ai_ml applied_ai data_engineering ml_platform robotics research",
    ),
    _seed(
        "amazon",
        "Amazon / AWS",
        "https://www.amazon.jobs/",
        "global-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "meta",
        "Meta",
        "https://www.metacareers.com/",
        "global-tech",
        "ai_ml applied_ai llm_nlp data_engineering ml_platform research",
    ),
    _seed(
        "ibm",
        "IBM",
        "https://www.ibm.com/",
        "global-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "adobe",
        "Adobe",
        "https://www.adobe.com/",
        "global-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "salesforce",
        "Salesforce",
        "https://www.salesforce.com/",
        "global-tech",
        "ai_ml applied_ai llm_nlp data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "oracle",
        "Oracle",
        "https://www.oracle.com/",
        "global-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform",
    ),
    _seed(
        "sap",
        "SAP",
        "https://www.sap.com/",
        "global-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
    ),
    _seed(
        "servicenow",
        "ServiceNow",
        "https://www.servicenow.com/",
        "global-tech",
        "ai_ml applied_ai data_analytics data_engineering ml_platform ai_product",
    ),
)


def profile_role_codes(profile: Any) -> set[str]:
    text = " ".join(
        str(getattr(profile, field, ""))
        for field in ("target_roles", "skills", "summary", "experience")
    ).casefold()
    signals = {
        "ai_ml": (
            "machine learning",
            " ml ",
            "ai engineer",
            "pytorch",
            "tensorflow",
            "scikit",
            "model training",
        ),
        "applied_ai": ("applied ai", "artificial intelligence", " ai ", "generative ai"),
        "llm_nlp": (
            "llm",
            "large language",
            "nlp",
            "natural language",
            "rag",
            "language model",
            "hugging face",
        ),
        "data_analytics": (
            "data analyst",
            "analytics",
            "sql",
            "pandas",
            "business intelligence",
            "statistics",
        ),
        "data_engineering": ("data engineer", "data pipeline", "etl", "warehouse", "spark", "dbt"),
        "ml_platform": (
            "mlops",
            "platform engineer",
            "model serving",
            "docker",
            "kubernetes",
            "infrastructure",
        ),
        "ai_product": (
            "solutions engineer",
            "forward deployed",
            "implementation",
            "customer engineer",
            "product engineer",
        ),
        "robotics": ("robotics", "robot", "autonomous systems"),
        "research": ("research", "scientist", "publication", "phd"),
    }
    padded = f" {re.sub(r'[^a-z0-9+#.]+', ' ', text)} "
    roles = {
        code for code, phrases in signals.items() if any(phrase in padded for phrase in phrases)
    }
    # Past reporting work must not steer AI engineering discovery toward generic analytics.
    if roles & {"ai_ml", "applied_ai", "llm_nlp"}:
        roles.discard("data_analytics")
        roles.discard("data_engineering")
    return roles


def filter_and_rank_companies(
    companies: Iterable[dict[str, Any]],
    *,
    query: str = "",
    group_id: str = "",
    profile: Any = None,
) -> list[dict[str, Any]]:
    query_text = query.strip().casefold()
    roles = profile_role_codes(profile) if profile else set()
    rows = []
    for source in companies:
        company = dict(source)
        haystack = " ".join(
            [company.get("name", ""), company.get("group_label", "")]
            + company.get("role_labels", [])
        ).casefold()
        if query_text and query_text not in haystack:
            continue
        if group_id and company.get("group_id") != group_id:
            continue
        company_roles = set(company.get("role_tags", []))
        company["profile_role_matches"] = sorted(company_roles & roles)
        company["profile_match_count"] = len(company["profile_role_matches"])
        rows.append(company)
    rows.sort(
        key=lambda item: (
            -item["profile_match_count"],
            not bool(item.get("tracked")),
            item.get("name", "").casefold(),
        )
    )
    return rows
