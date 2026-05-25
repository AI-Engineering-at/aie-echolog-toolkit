"""echo_log-Voice-Pattern-Helfer — Pure-Python Heuristik (Mac-lokal).

Diese Helfer sind die Mac-lokale Heuristik-Spiegelung der Brand-Voice-
Watcher-Skill-Regeln (`~/.claude/skills/brand-voice-watcher/SKILL.md`),
damit der MCP-Server ohne Live-LLM-Call eine erste Voice-Klassifikation
liefern kann. Live-Korrektheit bleibt beim Brand-Voice-Watcher-Skill
selbst — diese Heuristik ist die schnelle Pre-Gate-Schicht.

7-Dimensionen-Voice-Profil (aus SKILL.md §Schritt 2):
  Tonalität / Anrede / Konzeptdichte / Selbstpositionierung /
  Compliance-Bezug / Region-Heimat / Substanz-vs-Schein.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

VoiceLabel = Literal["on_brand", "drift", "off_brand", "unknown"]


# --------------------------------------------------------------------------- #
# Pattern-Listen — Drift-Marker (englische Floskeln, Buzzwords, Sycophancy)   #
# --------------------------------------------------------------------------- #
ENGLISH_BUZZWORDS = {
    "synergy", "leverage", "best-in-class", "next-gen", "cutting-edge",
    "game-changer", "disruptive", "world-class", "seamless", "end-to-end",
    "stakeholder", "value proposition", "thought leader", "deep dive",
    "low-hanging fruit", "circle back", "actionable insights", "scale up",
    "growth hacking", "pain point", "user-centric", "data-driven",
    "ai-powered", "ai-driven", "compliance-ready", "future-proof",
}

GENERIC_PRONOUNS = {
    "wir bieten", "wir lösen", "wir liefern", "unsere lösung",
    "der kunde", "der user", "der nutzer",
}

CONCRETE_ANCHORS = {
    "joe", "kmu", "burgenland", "österreich", "dach", "ai-engineering",
    "schulung", "art. 4", "art 4", "dsgvo", "eu ai act", "eu-ai-act",
    "edps", "ai office", "ai-office",
}

SYCOPHANCY_MARKERS = {
    "absolut", "selbstverständlich", "exzellente frage", "sehr gerne",
    "großartige idee", "fantastisch", "wunderbar", "perfekt!",
}

EVIDENCE_MARKERS = (
    re.compile(r"~/kb/(raw|company|ops|projects)/"),
    re.compile(r"https?://"),
    re.compile(r"\b(stand|datum|quelle|raw/\d+|m\d+|dec-\d+|gap-\d+)\b", re.IGNORECASE),
)


@dataclass
class VoiceScore:
    label: VoiceLabel
    score: float  # 0.0 = off_brand, 1.0 = on_brand
    findings: list[str]
    dimensions: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "score": round(self.score, 3),
            "findings": self.findings,
            "dimensions": {k: round(v, 3) for k, v in self.dimensions.items()},
        }


def _normalize(text: str) -> str:
    return (text or "").lower()


def _score_tonalitaet(text_l: str) -> tuple[float, list[str]]:
    findings: list[str] = []
    hits = [b for b in ENGLISH_BUZZWORDS if b in text_l]
    sycos = [s for s in SYCOPHANCY_MARKERS if s in text_l]
    if hits:
        findings.append(f"english-buzzword-hits: {hits[:5]}")
    if sycos:
        findings.append(f"sycophancy-marker: {sycos[:3]}")
    deduct = min(0.4, 0.1 * len(hits)) + min(0.4, 0.15 * len(sycos))
    return max(0.0, 1.0 - deduct), findings


def _score_anrede(text_l: str) -> tuple[float, list[str]]:
    findings: list[str] = []
    generic_hits = [p for p in GENERIC_PRONOUNS if p in text_l]
    concrete_hits = [a for a in CONCRETE_ANCHORS if a in text_l]
    if generic_hits:
        findings.append(f"generic-anrede: {generic_hits[:3]}")
    score = 0.5
    if concrete_hits:
        score = min(1.0, 0.6 + 0.1 * len(concrete_hits))
        findings.append(f"concrete-anchor: {concrete_hits[:5]}")
    if generic_hits and not concrete_hits:
        score = 0.2
    return score, findings


def _score_substanz(text_l: str, text_raw: str) -> tuple[float, list[str]]:
    findings: list[str] = []
    hits: list[str] = []
    for rx in EVIDENCE_MARKERS:
        m = rx.search(text_raw)
        if m:
            hits.append(m.group(0))
    if hits:
        findings.append(f"evidence-marker: {hits[:3]}")
        return min(1.0, 0.5 + 0.15 * len(hits)), findings
    # Wenn der Output keinerlei Quelle/Stand/Link/Raw-Beleg hat → drift.
    return 0.4, findings


def _score_compliance(text_l: str) -> tuple[float, list[str]]:
    findings: list[str] = []
    explicit = bool(
        re.search(r"\b(art\.?\s?\d+|dsgvo|eu ai act|eu-ai-act|datenschutz)\b", text_l)
    )
    generic = "compliance-ready" in text_l or "compliance ready" in text_l
    if generic:
        findings.append("generic-compliance-claim")
    if explicit:
        findings.append("explicit-compliance-anchor")
        return 1.0, findings
    if generic:
        return 0.3, findings
    return 0.6, findings


def _score_region(text_l: str) -> tuple[float, list[str]]:
    findings: list[str] = []
    concrete = any(
        a in text_l for a in ("burgenland", "österreich", "wien", "dach", "graz", "linz")
    )
    abstract = any(
        a in text_l for a in ("weltweit", "global", "everywhere", "worldwide")
    )
    if concrete:
        findings.append("region-anchor-konkret")
        return 1.0, findings
    if abstract:
        findings.append("region-anchor-abstrakt")
        return 0.3, findings
    return 0.6, findings


def _score_selbstpositionierung(text_l: str) -> tuple[float, list[str]]:
    findings: list[str] = []
    sehen_vermitteln = bool(
        re.search(r"\bich\s+(sehe|vermittle|prüfe|verifiziere|zeige|begleite)\b", text_l)
    )
    wir_anbieten = bool(
        re.search(r"\bwir\s+(bieten|liefern|verkaufen|lösen)\b", text_l)
    )
    if sehen_vermitteln:
        findings.append("sehen-vermitteln-marker")
        return 1.0, findings
    if wir_anbieten:
        findings.append("wir-anbieten-marker")
        return 0.3, findings
    return 0.6, findings


def _score_konzeptdichte(text_l: str) -> tuple[float, list[str]]:
    findings: list[str] = []
    anchors = [a for a in CONCRETE_ANCHORS if a in text_l]
    # Plus T1-Begriffe als Konzeptdichte-Indikator
    t1_terms = (
        "art. 4", "art 4", "dsgvo", "eu ai act", "edps", "merkle",
        "ed25519", "hash-chain", "audit-trail", "kmu", "fhir",
    )
    t1_hits = [t for t in t1_terms if t in text_l]
    if t1_hits:
        findings.append(f"t1-terms: {t1_hits[:5]}")
    density = len(anchors) + len(t1_hits)
    return min(1.0, 0.4 + 0.1 * density), findings


# --------------------------------------------------------------------------- #
# Composite-Score                                                             #
# --------------------------------------------------------------------------- #
DIMENSION_WEIGHTS = {
    "tonalitaet": 0.18,
    "anrede": 0.15,
    "konzeptdichte": 0.15,
    "selbstpositionierung": 0.15,
    "compliance": 0.12,
    "region": 0.10,
    "substanz": 0.15,
}


def voice_classify(text: str) -> VoiceScore:
    """7-Dimensionen-Voice-Klassifikation für echo_log-Persona.

    Mac-lokale Heuristik (keine LLM-Call), Pre-Gate-Schicht.
    Live-Gate bleibt brand-voice-watcher Skill (LLM + open-notebook).
    """
    if not text or not text.strip():
        return VoiceScore(
            label="unknown",
            score=0.0,
            findings=["empty-input"],
            dimensions={},
        )
    text_raw = text
    text_l = _normalize(text)

    findings: list[str] = []
    dims: dict[str, float] = {}

    s, f = _score_tonalitaet(text_l)
    dims["tonalitaet"] = s
    findings.extend(f)
    s, f = _score_anrede(text_l)
    dims["anrede"] = s
    findings.extend(f)
    s, f = _score_konzeptdichte(text_l)
    dims["konzeptdichte"] = s
    findings.extend(f)
    s, f = _score_selbstpositionierung(text_l)
    dims["selbstpositionierung"] = s
    findings.extend(f)
    s, f = _score_compliance(text_l)
    dims["compliance"] = s
    findings.extend(f)
    s, f = _score_region(text_l)
    dims["region"] = s
    findings.extend(f)
    s, f = _score_substanz(text_l, text_raw)
    dims["substanz"] = s
    findings.extend(f)

    total = sum(dims[k] * DIMENSION_WEIGHTS[k] for k in dims)

    if total >= 0.75:
        label: VoiceLabel = "on_brand"
    elif total >= 0.50:
        label = "drift"
    else:
        label = "off_brand"

    return VoiceScore(
        label=label,
        score=total,
        findings=findings,
        dimensions=dims,
    )


# --------------------------------------------------------------------------- #
# Pattern-Extraction Helpers (for pattern_learn tool)                         #
# --------------------------------------------------------------------------- #
def extract_pattern_signals(text: str) -> dict:
    """Extrahiert die Schlüssel-Signale eines Voice-Patterns für Persistenz.

    Wird von `pattern_learn` aufgerufen, um aus einem successful echo_log-
    Post ein wiederverwendbares Pattern-Snippet zu bilden, das in Open-
    Notebook (Evolution-Notes) wandern kann.
    """
    text_l = _normalize(text)
    anchors = [a for a in CONCRETE_ANCHORS if a in text_l]
    t1_terms = []
    for t in ("art. 4", "art 4", "dsgvo", "eu ai act", "edps", "merkle",
              "ed25519", "hash-chain", "audit-trail", "kmu"):
        if t in text_l:
            t1_terms.append(t)
    return {
        "text_len": len(text),
        "concrete_anchors": anchors,
        "t1_terms": t1_terms,
        "has_evidence_link": any(rx.search(text) for rx in EVIDENCE_MARKERS),
        "first_120_chars": text.strip()[:120],
    }
