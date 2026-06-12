"""Chat coordinator routing tests — Phase 5 (Plan v2).

LLM is mocked: deterministic tests for Pruefart dispatch,
equivalent inputs (UV/BM/component), RV-Frage, scope-guards.
Exit-Gate 5: S1 complaints from Runde 1 never trigger m²-nagging.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from products.dguv_v3.chat import (
    DGUVSession,
    coordinator_respond,
    inject_kalkulation_result,
    _has_minimum,
    _apply_uv_estimation,
    _parse_llm_json,
    _sanitize_m2_questions,
    UV_TO_M2_FACTOR,
    RV_BANNER,
)


def _mock_llm_response(result_dict: dict):
    """Create a mock LLM that returns a JSON response."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(result_dict, ensure_ascii=False)
    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=mock_response)
    return mock_llm


def _session():
    return DGUVSession()


class TestHasMinimum:
    def test_no_nutzung(self):
        assert not _has_minimum({})

    def test_nutzung_only(self):
        assert not _has_minimum({"nutzung": "buerogebaeude"})

    def test_nutzung_plus_flaeche(self):
        assert _has_minimum({"nutzung": "buerogebaeude", "gesamtflaeche_m2": 1000})

    def test_nutzung_plus_uv(self):
        assert _has_minimum({"nutzung": "buerogebaeude", "anzahl_verteilungen_uv": 48})

    def test_nutzung_plus_nshv(self):
        assert _has_minimum({"nutzung": "sonstige", "anzahl_verteilungen_nshv": 1})

    def test_ortsv_with_bm(self):
        assert _has_minimum({"nutzung": "industrie", "pruefart": "dguv_ortsv", "anzahl_betriebsmittel": 545})

    def test_ortsv_without_bm(self):
        assert not _has_minimum({"nutzung": "industrie", "pruefart": "dguv_ortsv"})

    def test_ortsv_with_flaeche_but_no_bm(self):
        assert not _has_minimum({"nutzung": "industrie", "pruefart": "dguv_ortsv", "gesamtflaeche_m2": 1000})


class TestUVEstimation:
    def test_uv_to_m2(self):
        params = {"anzahl_verteilungen_uv": 10}
        warnings = _apply_uv_estimation(params)
        assert params["gesamtflaeche_m2"] == 10 * UV_TO_M2_FACTOR
        assert len(warnings) == 1
        assert "Schätzung" in warnings[0]

    def test_nshv_to_m2(self):
        params = {"anzahl_verteilungen_nshv": 1}
        warnings = _apply_uv_estimation(params)
        assert params["gesamtflaeche_m2"] == 1 * UV_TO_M2_FACTOR

    def test_no_estimation_when_flaeche_present(self):
        params = {"gesamtflaeche_m2": 5000, "anzahl_verteilungen_uv": 10}
        warnings = _apply_uv_estimation(params)
        assert params["gesamtflaeche_m2"] == 5000
        assert len(warnings) == 0

    def test_no_estimation_when_no_verteilungen(self):
        params = {}
        warnings = _apply_uv_estimation(params)
        assert "gesamtflaeche_m2" not in params


class TestCoordinatorRouting:
    """S1 complaint scenarios: LLM returns correct pruefart, coordinator routes without m²-nagging."""

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_bm_rechenzentrum_ortsv(self, MockLLM):
        """'545 BM RZ' → dguv_ortsv, calculate without m² question."""
        MockLLM.return_value = _mock_llm_response({
            "message": "545 BM im RZ — Geräteprüfung.",
            "action": "calculate",
            "params": {"nutzung": "industrie", "pruefart": "dguv_ortsv", "anzahl_betriebsmittel": 545},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "545 Betriebsmittel Rechenzentrum")
        assert result["action"] == "calculate"
        assert result["params"]["pruefart"] == "dguv_ortsv"
        assert result["params"]["anzahl_betriebsmittel"] == 545
        assert "gesamtflaeche_m2" not in result["params"] or result["params"].get("gesamtflaeche_m2") is None

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_uv_only_calculate(self, MockLLM):
        """'48 UV, Verwaltung' → calculate, m² estimated from UV."""
        MockLLM.return_value = _mock_llm_response({
            "message": "48 UV, Kalkulation startet.",
            "action": "calculate",
            "params": {"nutzung": "buerogebaeude", "pruefart": "dguv_ortsfest", "anzahl_verteilungen_uv": 48},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "48 Unterverteilungen Verwaltungsgebäude")
        assert result["action"] == "calculate"
        assert result["params"]["gesamtflaeche_m2"] == 48 * UV_TO_M2_FACTOR

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_single_schaltschrank_kleinauftrag(self, MockLLM):
        """'1 Schaltschrank' → Kleinauftrag, no Mitarbeiter question."""
        MockLLM.return_value = _mock_llm_response({
            "message": "Einzelprüfung Schaltschrank.",
            "action": "calculate",
            "params": {"nutzung": "sonstige", "pruefart": "dguv_ortsfest", "anzahl_verteilungen_nshv": 1},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "1 Schaltschrank prüfen")
        assert result["action"] == "calculate"
        assert result["params"]["anzahl_verteilungen_nshv"] == 1
        assert result["params"].get("gesamtflaeche_m2") is None  # Kleinauftrag: no UV estimation
        assert "Mitarbeiter" not in result.get("message", "")

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_vds_only_routing(self, MockLLM):
        """'nur VdS' → pruefart=vds."""
        MockLLM.return_value = _mock_llm_response({
            "message": "VdS-Prüfung, 3000m².",
            "action": "calculate",
            "params": {"nutzung": "buerogebaeude", "pruefart": "vds", "gesamtflaeche_m2": 3000},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "nur VdS-Prüfung, Bürogebäude 3000m²")
        assert result["action"] == "calculate"
        assert result["params"]["pruefart"] == "vds"

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_geraete_kindergarten(self, MockLLM):
        """'20 Geräte Kindergarten' → dguv_ortsv, rechnet sofort."""
        MockLLM.return_value = _mock_llm_response({
            "message": "20 Geräte Kindergarten — Kalkulation.",
            "action": "calculate",
            "params": {"nutzung": "schule", "pruefart": "dguv_ortsv", "anzahl_betriebsmittel": 20},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "20 Geräte Kindergarten")
        assert result["action"] == "calculate"
        assert result["params"]["pruefart"] == "dguv_ortsv"
        assert result["params"]["anzahl_betriebsmittel"] == 20


class TestRVBanner:
    def test_rv_banner_injected(self):
        session = _session()
        session.extracted_params = {"rv_vorhanden": True}
        angebot = {
            "total": 1000,
            "breakdown": {"grund": 250, "pruef": 500, "reise": 150, "bericht": 100},
            "confidence": 0.85,
            "warnings": [],
        }
        inject_kalkulation_result(session, angebot)
        last_msg = session.messages[-1]["content"]
        assert "RAHMENVERTRAG" in last_msg
        assert "30-60%" in last_msg

    def test_no_rv_banner_when_not_set(self):
        session = _session()
        session.extracted_params = {}
        angebot = {
            "total": 1000,
            "breakdown": {"grund": 250, "pruef": 500, "reise": 150, "bericht": 100},
            "confidence": 0.85,
            "warnings": [],
        }
        inject_kalkulation_result(session, angebot)
        last_msg = session.messages[-1]["content"]
        assert "RAHMENVERTRAG" not in last_msg


class TestScopeGuards:
    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_insufficient_params_demoted_to_chat(self, MockLLM):
        """LLM says calculate but params insufficient → demoted to chat."""
        MockLLM.return_value = _mock_llm_response({
            "message": "Was für ein Gebäude?",
            "action": "calculate",
            "params": {"nutzung": "buerogebaeude"},
            "missing": ["gesamtflaeche_m2"],
        })
        session = _session()
        result = await coordinator_respond(session, "Büro prüfen")
        assert result["action"] == "chat"


class TestParseJSON:
    def test_plain_json(self):
        r = _parse_llm_json('{"message":"hi","action":"chat"}')
        assert r["action"] == "chat"

    def test_json_in_code_fence(self):
        r = _parse_llm_json('```json\n{"message":"hi","action":"calculate"}\n```')
        assert r["action"] == "calculate"

    def test_garbage_returns_chat(self):
        r = _parse_llm_json("this is not json")
        assert r["action"] == "chat"


class TestForcePromote:
    """Force-promote chat→calculate when _has_minimum() is True, even on first turn."""

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_llm_says_chat_but_has_uv_promotes(self, MockLLM):
        """LLM returns action=chat + nutzung+UV → force promote to calculate."""
        MockLLM.return_value = _mock_llm_response({
            "message": "Können Sie mir die Fläche nennen?",
            "action": "chat",
            "params": {"nutzung": "buerogebaeude", "anzahl_verteilungen_uv": 48},
            "missing": ["gesamtflaeche_m2"],
        })
        session = _session()
        result = await coordinator_respond(session, "48 UV Verwaltungsgebäude")
        assert result["action"] == "calculate"
        assert result["params"]["anzahl_verteilungen_uv"] == 48

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_llm_says_chat_but_has_bm_ortsv_promotes(self, MockLLM):
        """LLM returns action=chat + BM → force promote to calculate for MA560."""
        MockLLM.return_value = _mock_llm_response({
            "message": "Wie groß ist das Gebäude?",
            "action": "chat",
            "params": {"nutzung": "industrie", "pruefart": "dguv_ortsv", "anzahl_betriebsmittel": 20},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "20 Geräte Kindergarten")
        assert result["action"] == "calculate"

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_genuinely_missing_stays_chat(self, MockLLM):
        """LLM returns action=chat + only nutzung → stays chat (genuinely missing)."""
        MockLLM.return_value = _mock_llm_response({
            "message": "Wie groß ist die Fläche?",
            "action": "chat",
            "params": {"nutzung": "buerogebaeude"},
            "missing": ["gesamtflaeche_m2"],
        })
        session = _session()
        result = await coordinator_respond(session, "Bürogebäude prüfen")
        assert result["action"] == "chat"

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_nshv_schaltschrank_promotes(self, MockLLM):
        """'1 Schaltschrank' with NSHV=1 → force promote."""
        MockLLM.return_value = _mock_llm_response({
            "message": "Wie viele Mitarbeiter hat der Standort?",
            "action": "chat",
            "params": {"nutzung": "sonstige", "anzahl_verteilungen_nshv": 1},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "1 Schaltschrank prüfen")
        assert result["action"] == "calculate"
        assert result["params"]["anzahl_verteilungen_nshv"] == 1


class TestSanitizeMessage:
    """m²-questions removed from message when calculating."""

    def test_m2_question_stripped(self):
        msg = "48 UV — Kalkulation startet. Wie groß ist die Fläche in m²?"
        cleaned = _sanitize_m2_questions(msg)
        assert "m²" not in cleaned
        assert "Fläche" not in cleaned
        assert "Kalkulation" in cleaned

    def test_quadratmeter_stripped(self):
        msg = "Verwaltungsgebäude erkannt. Können Sie die Quadratmeter nennen?"
        cleaned = _sanitize_m2_questions(msg)
        assert "Quadratmeter" not in cleaned
        assert "Verwaltungsgebäude" in cleaned

    def test_wie_gross_stripped(self):
        msg = "Büro erkannt. Wie groß ist das Gebäude? Ich kalkuliere."
        cleaned = _sanitize_m2_questions(msg)
        assert "Wie groß" not in cleaned

    def test_proxy_preserved_zimmer(self):
        msg = "Hotel in München — wie viele Zimmer hat das Hotel?"
        cleaned = _sanitize_m2_questions(msg)
        assert "Zimmer" in cleaned
        assert cleaned == msg

    def test_proxy_preserved_betten(self):
        msg = "Krankenhaus — wie viele Betten?"
        cleaned = _sanitize_m2_questions(msg)
        assert "Betten" in cleaned
        assert cleaned == msg

    def test_proxy_preserved_klassen(self):
        msg = "Grundschule — wie viele Klassenräume?"
        cleaned = _sanitize_m2_questions(msg)
        assert "Klassenräume" in cleaned

    def test_empty_after_strip_returns_original(self):
        msg = "Wie groß ist die Fläche in m²?"
        cleaned = _sanitize_m2_questions(msg)
        assert cleaned == msg  # all stripped → return original

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_sanitize_applied_in_coordinator(self, MockLLM):
        """Full integration: message sanitized when action=calculate."""
        MockLLM.return_value = _mock_llm_response({
            "message": "48 UV im Verwaltungsgebäude. Wie groß ist die Gesamtfläche in m²?",
            "action": "calculate",
            "params": {"nutzung": "buerogebaeude", "anzahl_verteilungen_uv": 48},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "48 UV Verwaltungsgebäude")
        assert result["action"] == "calculate"
        assert "m²" not in result["message"]
        assert "Gesamtfläche" not in result["message"]
