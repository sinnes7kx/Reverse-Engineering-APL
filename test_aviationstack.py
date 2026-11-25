"""Aviationstack tests use synthetic fixtures and never consume API requests."""
import io
import json
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from aviationstack_client import AviationstackClient, normalize_flight, utc_time
from flightinfo import FlightInfoError, upcoming
from airport import main


def fixture():
    return {"flight_date": "2026-11-24", "flight_status": "scheduled",
            "departure": {"airport": "Arlanda", "iata": "ARN", "timezone": "Europe/Stockholm",
                          "scheduled": "2026-11-24T12:00:00+01:00", "actual": None,
                          "terminal": "5", "gate": "12"},
            "arrival": {"airport": "Heathrow", "iata": "LHR", "timezone": "Europe/London",
                        "scheduled": "2026-11-24T14:00:00+00:00", "baggage": "3"},
            "airline": {"name": "Example airline", "iata": "SK"},
            "flight": {"iata": "SK532"}}


class AviationstackTests(unittest.TestCase):
    def setUp(self):
        self.client = AviationstackClient("test-placeholder")
        self.today = patch("aviationstack_client.swedish_today", return_value=date(2026, 11, 24))
        self.today.start()
        self.addCleanup(self.today.stop)

    def response(self, payload):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode()
        return response

    def test_normalization_and_timezones(self):
        result = normalize_flight(fixture(), "departures")
        self.assertEqual(result["flightId"], "SK532")
        self.assertEqual(result["departureTime"]["scheduledUtc"], "2026-11-24T11:00:00Z")
        self.assertEqual(result["locationAndStatus"]["gate"], "12")
        self.assertEqual(result["departureAirportEnglish"], "Stockholm Arlanda")
        self.assertEqual(utc_time("2026-07-01T12:00:00", "Europe/Stockholm"), "2026-07-01T10:00:00Z")
        self.assertIsNone(utc_time("2026-07-01T12:00:00"))
        self.assertIsNone(utc_time("bad", "Europe/Stockholm"))

    def test_cancelled_flight_and_missing_fields(self):
        row = fixture()
        row["flight_status"] = "cancelled"
        row["airline"] = None
        result = normalize_flight(row, "departures")
        self.assertFalse(upcoming(result))
        self.assertIsNone(result["airlineOperator"]["name"])
        self.assertIsNone(normalize_flight({}, "arrivals")["arrivalTime"]["scheduledUtc"])

    def test_request_filters_https_and_key(self):
        with patch("aviationstack_client.urlopen", return_value=self.response({"data": [fixture()]})) as request:
            rows = self.client.search("ARN", "2026-11-24", "D", "sk532")
        self.assertEqual(len(rows), 1)
        url = urlparse(request.call_args.args[0].full_url)
        params = parse_qs(url.query)
        self.assertEqual((url.scheme, url.netloc, url.path), ("https", "api.aviationstack.com", "/v1/flights"))
        self.assertEqual(params["dep_iata"], ["ARN"])
        self.assertEqual(params["flight_iata"], ["SK532"])
        self.assertEqual(params["access_key"], ["test-placeholder"])
        self.assertNotIn("flight_date", params)  # Avoid invoking historical functionality.

    def test_date_airport_and_flight_filters(self):
        wrong_day = fixture()
        wrong_day["departure"]["scheduled"] = "2026-11-25T12:00:00Z"
        wrong_airport = fixture()
        wrong_airport["departure"]["iata"] = "GOT"
        with patch.object(self.client, "get", return_value={"data": [fixture(), wrong_day, wrong_airport]}):
            self.assertEqual(len(self.client.flights("ARN", "2026-11-24", "departures")), 1)
            self.assertEqual(self.client.search("ARN", "2026-11-24", "D", "XX999"), [])

    def test_other_dates_and_odata_do_not_consume_requests(self):
        with patch.object(self.client, "get") as request:
            for day in ["2026-11-23", "2026-11-25"]:
                with self.assertRaises(ValueError):
                    self.client.flights("ARN", day, "departures")
            with self.assertRaises(ValueError):
                self.client.query("airport eq 'ARN'")
        request.assert_not_called()

    def test_truncation_is_visible_and_uses_one_request(self):
        with patch.object(self.client, "get", return_value={"data": [fixture()], "pagination": {"total": 200}}) as request:
            with self.assertWarnsRegex(UserWarning, "1 av 200"):
                self.client.flights("ARN", "2026-11-24", "departures")
        request.assert_called_once()

    def test_auth_errors_do_not_expose_url_or_key(self):
        for failure in [HTTPError("https://example.test/?access_key=test-placeholder", 401, "secret", {}, None), URLError("test-placeholder")]:
            with patch("aviationstack_client.urlopen", side_effect=failure):
                with self.assertRaises(FlightInfoError) as error:
                    self.client.heartbeat()
            self.assertNotIn("test-placeholder", str(error.exception))
        with patch("aviationstack_client.urlopen", return_value=self.response({"error": {"code": "invalid_access_key", "message": "test-placeholder"}})):
            with self.assertRaisesRegex(FlightInfoError, "Ogiltig") as error:
                self.client.heartbeat()
        self.assertNotIn("test-placeholder", str(error.exception))

    def test_missing_key_empty_results_and_status_request(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(FlightInfoError):
                AviationstackClient()
        with patch("aviationstack_client.urlopen", return_value=self.response({"data": []})):
            self.assertEqual(self.client.flights("ARN", "2026-11-24", "arrivals"), [])
            self.assertEqual(self.client.heartbeat()["status"], "OK")
        with patch("aviationstack_client.urlopen", return_value=self.response({"data": None})):
            with self.assertRaises(FlightInfoError):
                self.client.heartbeat()

    def test_aviationstack_menu_and_private_prompt(self):
        with patch("sys.argv", ["airport.py", "--aviationstack", "--ask-key"]), patch("aviationstack_client.getpass", return_value="test-placeholder"), patch("builtins.input", side_effect=["4", "q"]), patch("aviationstack_client.urlopen") as request, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 0)
        request.assert_not_called()
        self.assertIn("stöder inte OData", output.getvalue())
        self.assertNotIn("test-placeholder", output.getvalue())


if __name__ == "__main__":
    unittest.main()
