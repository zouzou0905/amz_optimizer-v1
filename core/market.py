MARKET_CONFIGS = {
    "UK": {
        "domain": "www.amazon.co.uk",
        "zip": "M1 1AG",
        "locale": "en-GB",
        "state_file": "amazon_uk_state.json",
        "expert_role": "Senior Amazon UK SEO Expert",
        "lang_name": "British English",
        "suffix": "(英语)",
        "system_language": "English",
        "instructions": {
            "step1": "KEYWORD WEIGHTING: Identify British English keyword phrases (2-3 words) with the highest relevance for ranking.",
            "step2": "USP SYNTHESIS: Which selling arguments in the bullet points lead to the highest conversion in the UK market?",
            "step3": "TITLE OPTIMIZATION: Create a new optimized title within 150 characters. Integrate core keywords organically, mimic top UK bestseller tone, and address review pain points with positive wording.",
            "json_req": "Keywords/Selling Points/Title in British English, Pain Points in Chinese",
        },
    },
    "DE": {
        "domain": "www.amazon.de",
        "zip": "10115",
        "locale": "de-DE",
        "state_file": "amazon_de_state.json",
        "expert_role": "Senior Amazon SEO Experte",
        "lang_name": "German",
        "suffix": "(德语)",
        "system_language": "German",
        "instructions": {
            "step1": "KEYWORD-GEWICHTUNG: Identifiziere deutsche Keyword-Phrasen (2-3 Wörter), die die höchste Relevanz für das Ranking haben.",
            "step2": "USP-SYNTHESE: Welche Verkaufsargumente in den Bullet Points führen zur höchsten Conversion?",
            "step3": "TITEL-OPTIMIERUNG: Erstelle einen neuen optimierten Titel mit maximal 150 Zeichen. Integriere Core-Keywords organisch und orientiere dich am Tonfall der Top-Bestseller.",
            "json_req": "Keywords/Selling Points/Titel auf Deutsch, Pain Points auf Chinesisch",
        },
    },
}


def normalize_market(market):
    value = (market or "UK").upper()
    if value not in MARKET_CONFIGS:
        raise ValueError(f"不支持的市场: {market}。可选值: UK, DE")
    return value


def get_market_config(market):
    return MARKET_CONFIGS[normalize_market(market)]
