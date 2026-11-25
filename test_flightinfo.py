"""Offline behavioral tests; these never contact Swedavia."""
import contextlib
import io
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from airport import main, print_flights_paged, ask_date, ask_airport
from destinationer import destination_rows
from flightinfo import (DemoClient, LiveClient, FlightInfoError, airport_code,
                        parse_date, format_time, upcoming, flights_from,
                        flight_filter, swedish_today)


class InputTests(unittest.TestCase):
    def test_airport_aliases_and_ambiguity(self):
        self.assertEqual(airport_code("göteborg"), "GOT")
        self.assertEqual(airport_code("visby"), "VBY")
        with self.assertRaises(ValueError):
            airport_code("Stockholm")
        with self.assertRaises(ValueError):
            airport_code("")

    def test_date_rollover_and_invalid_dates(self):
        self.assertEqual(parse_date("imorgon", date(2026, 12, 31)), "2027-01-01")
        for invalid in ["2026-02-30", "26-2-3", "garbage"]:
            with self.assertRaises(ValueError):
                parse_date(invalid)

    def test_airport_numbers_partial_names_and_defaults(self):
        self.assertEqual(airport_code("2"), "GOT")
        self.assertEqual(airport_code("10"), "KRN")
        self.assertEqual(airport_code("landv"), "GOT")
        with self.assertRaisesRegex(ValueError, "Arlanda.*Bromma"):
            airport_code("Stockholm")
        for invalid in ["0", "11"]:
            with self.assertRaises(ValueError):
                airport_code(invalid)
        with patch("builtins.input", side_effect=["Stockholm", "3"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ask_airport(), "BMA")
        with patch("builtins.input", return_value="") as prompt, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ask_airport("GOT"), "GOT")
        self.assertIn("[GOT - Göteborg Landvetter]", prompt.call_args.args[0])

    def test_date_quick_choices_cross_year_boundary(self):
        for choice, expected in [("1", "2026-12-31"), ("2", "2027-01-01"), ("3", "2026-12-30")]:
            with self.subTest(choice=choice), patch("airport.swedish_today", return_value=date(2026, 12, 31)), patch("builtins.input", return_value=choice), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ask_date(), expected)

    def test_alternative_full_date_formats(self):
        for text in ["20261125", "25/11/2026"]:
            self.assertEqual(parse_date(text), "2026-11-25")
        self.assertEqual(parse_date("2/1/2027"), "2027-01-02")
        for invalid in ["20260230", "30/2/2026", "25/11/26", "25112026"]:
            with self.assertRaises(ValueError):
                parse_date(invalid)

    def test_menu_remembers_last_airport(self):
        # Two searches: choose GOT once, then accept it with Enter.
        with patch("sys.argv", ["airport.py", "--demo"]), patch("builtins.input", side_effect=["1", "2", "", "n", "2", "", "", "n", "q"]) as prompt, patch("airport.print_flights_paged"), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)
        prompts = [call.args[0] for call in prompt.call_args_list]
        self.assertTrue(any("[GOT - Göteborg Landvetter]" in text for text in prompts))

    def test_swedish_dst_and_midnight(self):
        self.assertIn("2026-01-02 00:30 CET", format_time("2026-01-01T23:30:00Z"))
        self.assertIn("12:00 CEST", format_time("2026-07-01T10:00:00Z"))
        self.assertIn("03:30 CEST", format_time("2026-03-29T01:30:00Z"))
        self.assertEqual(format_time(None), "-")

    def test_complete_dates_and_default(self):
        today = date(2026, 11, 23)
        for text, expected in [("", "2026-11-23"), ("2027-01-02", "2027-01-02"),
                               (" 2028-02-29 ", "2028-02-29")]:
            with self.subTest(text=text):
                self.assertEqual(parse_date(text, today), expected)
        for invalid in ["25", "25/11", "25-11", "+3", "-1", "2026-02-29"]:
            with self.subTest(text=invalid), self.assertRaises(ValueError):
                parse_date(invalid, today)

    def test_today_uses_swedish_date_near_midnight(self):
        with patch("flightinfo.datetime") as clock:
            clock.now.return_value = datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc)
            self.assertEqual(swedish_today(), date(2027, 1, 1))
            self.assertEqual(parse_date(""), "2027-01-01")

    def test_date_prompt_shows_default_and_retries(self):
        output = io.StringIO()
        with patch("airport.swedish_today", return_value=date(2026, 11, 23)), patch("builtins.input", side_effect=["25/11", "2026-11-26"]) as prompt, contextlib.redirect_stdout(output):
            self.assertEqual(ask_date(), "2026-11-26")
        prompt.assert_called_with("Ange datum (YYYY-MM-DD) [2026-11-23]: ")
        self.assertIn("Valt datum: 2026-11-26", output.getvalue())

    def test_date_prompt_accepts_placeholder_on_enter(self):
        with patch("airport.swedish_today", return_value=date(2026, 11, 23)), patch("builtins.input", return_value="") as prompt, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ask_date(), "2026-11-23")
        prompt.assert_called_once_with("Ange datum (YYYY-MM-DD) [2026-11-23]: ")

    def test_filter_validation(self):
        self.assertIn("scheduled eq '260226'", flight_filter("ARN", "2026-02-26", "D", "sk532"))
        with self.assertRaises(ValueError):
            flight_filter("ARN", "2026-02-26", "D", "SK' or '1")


class FlightTests(unittest.TestCase):
    def setUp(self):
        self.demo = DemoClient()
        self.flights = self.demo.flights("ARN", "2026-02-26", "arrivals")

    def test_empty_and_pascal_case_responses(self):
        self.assertEqual(flights_from({"Flights": [{}, None, {"FlightId": "SK1"}]}), [{"FlightId": "SK1"}])
        self.assertEqual(flights_from({"flights": []}), [])
        with self.assertRaises(FlightInfoError):
            flights_from({"unexpected": True})

    def test_upcoming_excludes_completed_cancelled_and_unknown(self):
        now = datetime(2026, 2, 26, 4, tzinfo=timezone.utc)
        self.assertFalse(upcoming(self.flights[0], now))
        self.assertFalse(upcoming(self.flights[7], now))
        self.assertFalse(upcoming({}, now))
        self.assertTrue(upcoming(self.flights[10], now))

    def test_delayed_flight_uses_estimate(self):
        flight = {"departureTime": {"scheduledUtc": "2026-02-26T10:00:00Z", "estimatedUtc": "2026-02-26T12:00:00Z"}}
        self.assertTrue(upcoming(flight, datetime(2026, 2, 26, 11, tzinfo=timezone.utc)))

    def test_demo_search_and_unsupported_odata(self):
        result = self.demo.query(flight_filter("ARN", "2026-02-26", "A", "SK532"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["flightId"], "SK532")
        self.assertEqual(self.demo.query(flight_filter("ARN", "2026-02-26", "A", "XX999")), [])
        with self.assertRaises(ValueError):
            self.demo.query("airport eq 'ARN' or airport eq 'GOT'")

    def test_destinations_and_country_filter(self):
        rows = destination_rows(self.flights, "arrivals", "Germany")
        self.assertEqual(rows, [("Frankfurt", "Germany", 10)])
        self.assertEqual(destination_rows([{"arrivalAirportEnglish": "New place"}], "departures"), [("New place", "Unknown", 1)])

    def test_paging_quit_next_all(self):
        for choices, expected in [(["q"], 50), ([""], 60), (["a"], 60)]:
            with patch("builtins.input", side_effect=choices), patch("airport.print_flight") as printer, contextlib.redirect_stdout(io.StringIO()):
                print_flights_paged(self.flights)
            self.assertEqual(printer.call_count, expected)

    def test_menu_returns_after_invalid_input(self):
        output = io.StringIO()
        with patch("sys.argv", ["airport.py", "--demo"]), patch("builtins.input", side_effect=["bad", "5", "q"]), contextlib.redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertIn("simulerad OK", output.getvalue())


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = LiveClient("test-only-placeholder")

    def test_query_pagination(self):
        pages = [{"flights": [{"flightId": "SK1"}], "continuationToken": "a+/="},
                 {"flights": [{"flightId": "SK2"}], "continuationToken": "b"},
                 {"flights": []}]
        tokens = []
        def get(path, params):
            tokens.append(params.get("continuationtoken"))
            return pages.pop(0)
        with patch.object(self.client, "get", side_effect=get):
            result = self.client.query("airport eq 'ARN'")
        self.assertEqual([f["flightId"] for f in result], ["SK1", "SK2"])
        self.assertEqual(tokens, [None, "a+/=", "b"])

    def test_repeated_token_is_not_infinite_loop(self):
        with patch.object(self.client, "get", return_value={"flights": [{"flightId": "SK1"}], "continuationToken": "same"}):
            with self.assertRaises(FlightInfoError):
                self.client.query("x")

    def test_http_request_encodes_token_and_sets_key(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b'{"flights": []}'
        with patch("flightinfo.urlopen", return_value=response) as opener:
            self.client.get("/query", {"continuationtoken": "a+/="})
        request = opener.call_args.args[0]
        self.assertEqual(parse_qs(urlparse(request.full_url).query)["continuationtoken"], ["a+/="])
        self.assertIn("test-only-placeholder", request.headers.values())
        self.assertEqual(opener.call_args.kwargs["timeout"], 20)

    def test_errors_are_actionable_and_do_not_echo_key(self):
        for code in [401, 403, 429, 500]:
            with patch("flightinfo.urlopen", side_effect=HTTPError("https://example.test", code, "error", {}, None)):
                with self.assertRaises(FlightInfoError) as caught:
                    self.client.heartbeat()
            self.assertIn(str(code), str(caught.exception))
            self.assertNotIn(self.client.api_key, str(caught.exception))
        with patch("flightinfo.urlopen", side_effect=URLError("offline")):
            with self.assertRaises(FlightInfoError):
                self.client.heartbeat()

    def test_empty_response_and_non_json_heartbeat(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 204
        response.read.return_value = b""
        with patch("flightinfo.urlopen", return_value=response):
            self.assertEqual(self.client.flights("ARN", "2026-02-26", "arrivals"), [])
            response.status = 200
            response.read.return_value = b"OK"
            self.assertEqual(self.client.heartbeat()["status"], 200)
            with self.assertRaises(FlightInfoError):
                self.client.flights("ARN", "2026-02-26", "arrivals")


if __name__ == "__main__":
    unittest.main()
