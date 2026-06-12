"""Multi-step chat scenario tests — real-life flows from Testrunde 08.06.

Each test simulates a multi-turn conversation with mocked LLM responses,
verifying that the coordinator routes correctly and never asks about m²
when sufficient data is available.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from products.dguv_v3.chat import (
    DGUVSession,
    coordinator_respond,
    _has_minimum,
    UV_TO_M2_FACTOR,
)


def _mock_llm(result_dict: dict):
    mock_response = MagicMock()
    mock_response.text = json.dumps(result_dict, ensure_ascii=False)
    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value=mock_response)
    return mock_llm


def _session():
    return DGUVSession()


M2_KEYWORDS = {"m²", "quadratmeter", "fläche", "wie groß", "gesamtfläche"}


def _has_m2_question(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in M2_KEYWORDS)


class TestS1Scenarios:
    """Real-life scenarios from Testrunde 08.06 — S1 complaints."""

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_pausch_48uv_verwaltung(self, MockLLM):
        """Pausch: '48 UV auf 4 Gebäude' → calculate, NOT ask for m²."""
        MockLLM.return_value = _mock_llm({
            "message": "48 Unterverteilungen auf 4 Gebäude — ich benötige noch die Gesamtfläche in m².",
            "action": "chat",
            "params": {"nutzung": "buerogebaeude", "pruefart": "dguv_ortsfest", "anzahl_verteilungen_uv": 48},
            "missing": ["gesamtflaeche_m2"],
        })
        session = _session()
        result = await coordinator_respond(session, "48 Unterverteilungen auf 4 Gebäude, Verwaltungsgebäude")
        assert result["action"] == "calculate", "Should force-calculate with 48 UV"
        assert not _has_m2_question(result["message"]), f"Should not ask about m²: {result['message']}"
        assert result["params"]["anzahl_verteilungen_uv"] == 48

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_steinwidder_545bm_rechenzentrum(self, MockLLM):
        """Steinwidder: '545 ortsveränderliche Geräte RZ' → MA560, no m²."""
        MockLLM.return_value = _mock_llm({
            "message": "545 Betriebsmittel im Rechenzentrum — Geräteprüfung. Wie groß ist die Fläche?",
            "action": "calculate",
            "params": {"nutzung": "industrie", "pruefart": "dguv_ortsv", "anzahl_betriebsmittel": 545},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "545 ortsveränderliche Geräte im Rechenzentrum")
        assert result["action"] == "calculate"
        assert result["params"]["pruefart"] == "dguv_ortsv"
        assert not _has_m2_question(result["message"])

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_pausch_schaltschrank(self, MockLLM):
        """Pausch: '1 Schaltschrank' → Kleinauftrag, no Mitarbeiter question."""
        MockLLM.return_value = _mock_llm({
            "message": "Schaltschrank-Prüfung. Wie viele Mitarbeiter hat der Standort?",
            "action": "chat",
            "params": {"nutzung": "sonstige", "pruefart": "dguv_ortsfest", "anzahl_verteilungen_nshv": 1},
            "missing": [],
        })
        session = _session()
        result = await coordinator_respond(session, "1 Schaltschrank prüfen lassen")
        assert result["action"] == "calculate"
        assert result["params"]["anzahl_verteilungen_nshv"] == 1
        assert "Mitarbeiter" not in result["message"]

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_weiss_uv_maschinen(self, MockLLM):
        """Weiß: 'UV und Maschinen' → should not redirect to m²."""
        MockLLM.return_value = _mock_llm({
            "message": "Industriegebäude mit 12 UV. Wie groß ist die Gesamtfläche in m²?",
            "action": "chat",
            "params": {"nutzung": "industrie", "pruefart": "dguv_ortsfest", "anzahl_verteilungen_uv": 12},
            "missing": ["gesamtflaeche_m2"],
        })
        session = _session()
        result = await coordinator_respond(session, "Industriegebäude, 12 Unterverteilungen und diverse Maschinen")
        assert result["action"] == "calculate"
        assert not _has_m2_question(result["message"])

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_pfilf_motel_one_ortsv(self, MockLLM):
        """Pfilf: 'Motel One ortsveränderlich' → MA560, ask Geräte count NOT Zimmer."""
        MockLLM.return_value = _mock_llm({
            "message": "Motel One — ortsveränderliche Geräteprüfung. Wie viele Geräte sollen geprüft werden?",
            "action": "chat",
            "params": {"nutzung": "hotel", "pruefart": "dguv_ortsv"},
            "missing": ["anzahl_betriebsmittel"],
        })
        session = _session()
        result = await coordinator_respond(session, "Motel One, ortsveränderliche Geräte prüfen")
        assert result["action"] == "chat"  # legitimately missing BM count
        assert "Geräte" in result["message"] or "Betriebsmittel" in result["message"]


class TestProxyFlowsPreserved:
    """Ensure legitimate proxy questions still work in multi-turn."""

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_hotel_zimmer_flow(self, MockLLM):
        """Hotel without size → asks Zimmer (turn 1) → calculate (turn 2)."""
        session = _session()

        # Turn 1: Hotel, no size → should ask for Zimmer
        MockLLM.return_value = _mock_llm({
            "message": "Hotel in München — wie viele Zimmer hat das Hotel?",
            "action": "chat",
            "params": {"nutzung": "hotel", "adresse_ort": "München"},
            "missing": ["gesamtflaeche_m2"],
        })
        r1 = await coordinator_respond(session, "Hotel in München prüfen")
        assert r1["action"] == "chat"
        assert "Zimmer" in r1["message"]

        # Turn 2: User gives Zimmer → calculate
        MockLLM.return_value = _mock_llm({
            "message": "120 Zimmer ≈ 3.600 m² — Kalkulation startet.",
            "action": "calculate",
            "params": {"nutzung": "hotel", "gesamtflaeche_m2": 3600, "adresse_ort": "München"},
            "missing": [],
        })
        r2 = await coordinator_respond(session, "120 Zimmer")
        assert r2["action"] == "calculate"
        assert r2["params"]["gesamtflaeche_m2"] == 3600

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_krankenhaus_betten_flow(self, MockLLM):
        """Krankenhaus → asks Betten → calculate."""
        session = _session()

        MockLLM.return_value = _mock_llm({
            "message": "Krankenhaus — wie viele Betten hat die Klinik?",
            "action": "chat",
            "params": {"nutzung": "krankenhaus"},
            "missing": [],
        })
        r1 = await coordinator_respond(session, "Krankenhaus prüfen")
        assert r1["action"] == "chat"
        assert "Betten" in r1["message"]

        MockLLM.return_value = _mock_llm({
            "message": "200 Betten ≈ 10.000 m² — Kalkulation startet.",
            "action": "calculate",
            "params": {"nutzung": "krankenhaus", "gesamtflaeche_m2": 10000},
            "missing": [],
        })
        r2 = await coordinator_respond(session, "200 Betten")
        assert r2["action"] == "calculate"

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_buero_flaeche_legitimate(self, MockLLM):
        """Büro without ANY info → asking for m² is legitimate."""
        session = _session()

        MockLLM.return_value = _mock_llm({
            "message": "Bürogebäude — wie groß ist die Fläche in m²?",
            "action": "chat",
            "params": {"nutzung": "buerogebaeude"},
            "missing": ["gesamtflaeche_m2"],
        })
        r1 = await coordinator_respond(session, "Bürogebäude prüfen")
        assert r1["action"] == "chat"  # legitimately missing


class TestEdgeCases:

    @pytest.mark.asyncio
    @patch("products.dguv_v3.chat.ClaudeLLM")
    async def test_uv_then_flaeche_update(self, MockLLM):
        """Turn 1: UV→calculate. Turn 2: user provides m² → recalculate with real m²."""
        session = _session()

        MockLLM.return_value = _mock_llm({
            "message": "10 UV — Kalkulation startet.",
            "action": "calculate",
            "params": {"nutzung": "buerogebaeude", "anzahl_verteilungen_uv": 10},
            "missing": [],
        })
        r1 = await coordinator_respond(session, "Büro, 10 UV")
        assert r1["action"] == "calculate"
        assert r1["params"]["gesamtflaeche_m2"] == 10 * UV_TO_M2_FACTOR

        # Simulate injection of kalkulation result
        session.last_kalkulation = {"total": 5000}

        MockLLM.return_value = _mock_llm({
            "message": "5.000 m² — Neuberechnung mit exakter Fläche.",
            "action": "calculate",
            "params": {"nutzung": "buerogebaeude", "anzahl_verteilungen_uv": 10, "gesamtflaeche_m2": 5000},
            "missing": [],
        })
        r2 = await coordinator_respond(session, "Die Fläche ist 5000m²")
        assert r2["action"] == "calculate"
        assert r2["params"]["gesamtflaeche_m2"] == 5000  # real m², not estimated
