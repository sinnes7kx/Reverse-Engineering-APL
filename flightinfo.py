"""Swedavia FlightInfo v2 client and an explicitly synthetic offline data source."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE_URL = "https://api.swedavia.se/flightinfo/v2"
AIRPORTS = {
    "ARN": "Stockholm Arlanda", "GOT": "Göteborg Landvetter",
    "BMA": "Stockholm Bromma", "MMX": "Malmö", "LLA": "Luleå",
    "UME": "Umeå", "OSD": "Åre Östersund", "VBY": "Visby",
    "RNB": "Ronneby", "KRN": "Kiruna",
}


class FlightInfoError(Exception):
    """An actionable error that can be shown without exposing credentials."""


def value(obj, key, default=None):
    """Accept both camelCase and PascalCase JSON keys."""
    if not isinstance(obj, dict):
        return default
    return next((v for k, v in obj.items() if k.casefold() == key.casefold()), default)


def folded(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def airport_code(text):
    text = text.strip()
    codes = list(AIRPORTS)
    if text.isascii() and text.isdigit() and 1 <= int(text) <= len(codes):
        return codes[int(text) - 1]
    if text.upper() in AIRPORTS:
        return text.upper()
    aliases = {"arlanda": "ARN", "bromma": "BMA", "landvetter": "GOT",
               "gothenburg": "GOT", "goteborg": "GOT", "ostersund": "OSD"}
    if folded(text) in aliases:
        return aliases[folded(text)]
    matches = [code for code, name in AIRPORTS.items()
               if folded(text) and folded(text) in folded(name)]
    if len(matches) == 1:
        return matches[0]
    if matches:
        options = ", ".join(f"{codes.index(code) + 1}: {AIRPORTS[code]} ({code})" for code in matches)
        raise ValueError(f"Flera flygplatser matchar. Välj {options}.")
    raise ValueError("Ingen flygplats matchar. Välj nummer 1-10, kod eller namn från listan.")


def swedish_today():
    """Use the user's Swedish calendar day, including around UTC midnight."""
    return datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Stockholm")).date()


def parse_date(text, today=None):
    """Accept a complete date or a named shortcut; blank input selects today."""
    today = today if today is not None else swedish_today()
    aliases = {"": 0, "nu": 0, "idag": 0, "today": 0,
               "imorgon": 1, "i morgon": 1, "tomorrow": 1,
               "igår": -1, "igar": -1, "yesterday": -1}
    text = text.strip().lower()
    if text in aliases:
        return (today + timedelta(days=aliases[text])).isoformat()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return date.fromisoformat(text).isoformat()
        if re.fullmatch(r"\d{8}", text):
            return date(int(text[:4]), int(text[4:6]), int(text[6:])).isoformat()
        swedish = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if swedish:
            return date(int(swedish[3]), int(swedish[2]), int(swedish[1])).isoformat()
    except (ValueError, OverflowError):
        raise ValueError("Datumet finns inte eller ligger utanför tillåtet datumintervall.") from None
    raise ValueError("Ange datum med årtal: YYYY-MM-DD, YYYYMMDD eller DD/MM/YYYY. Enter väljer idag.")


def parse_time(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (result if result.tzinfo else result.replace(tzinfo=timezone.utc))
    except ValueError:
        return None


def format_time(raw):
    instant = parse_time(raw)
    if instant is None:
        return "-" if not raw else f"{raw} (ogiltig tid)"
    utc = instant.astimezone(timezone.utc)
    local = instant.astimezone(ZoneInfo("Europe/Stockholm"))
    return f"{utc:%Y-%m-%d %H:%M} UTC -> {local:%Y-%m-%d %H:%M %Z}"


def flight_times(flight):
    return value(flight, "arrivalTime") or value(flight, "departureTime") or {}


def valid_flight(flight):
    return isinstance(flight, dict) and bool(
        value(flight, "flightId") or value(flight, "departureAirportEnglish")
        or value(flight, "arrivalAirportEnglish")
        or value(flight_times(flight), "scheduledUtc"))


def upcoming(flight, now=None):
    times = flight_times(flight)
    status = value(value(flight, "locationAndStatus"), "flightLegStatus", "")
    if str(status).upper() in {"CAN", "DEL", "LAN"} or value(times, "actualUtc"):
        return False
    planned = parse_time(value(times, "estimatedUtc")) or parse_time(value(times, "scheduledUtc"))
    return planned is not None and planned >= (now or datetime.now(timezone.utc))


def flights_from(payload):
    flights = payload if isinstance(payload, list) else value(payload, "flights")
    if not isinstance(flights, list):
        raise FlightInfoError("API-svaret saknar en giltig flights-lista.")
    return [f for f in flights if valid_flight(f)]


def flight_filter(airport, day, direction, flight_id=""):
    airport = airport_code(airport)
    day = parse_date(day)
    if direction not in {"A", "D"}:
        raise ValueError("Riktningen måste vara A eller D.")
    expression = (f"airport eq '{airport}' and scheduled eq '{date.fromisoformat(day):%y%m%d}'"
                  f" and flightType eq '{direction}'")
    if flight_id:
        if not re.fullmatch(r"[A-Za-z0-9]{2,10}", flight_id):
            raise ValueError("Flygnummer ska innehålla 2-10 bokstäver eller siffror.")
        expression += f" and flightId eq '{flight_id.upper()}'"
    return expression


class LiveClient:
    mode = "LIVE - Swedavia API"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("SWEDAVIA_API_KEY", "")
        if not self.api_key:
            local = Path(__file__).with_name(".env")
            if local.exists():
                for line in local.read_text(encoding="utf-8").splitlines():
                    name, separator, secret = line.partition("=")
                    if separator and name.strip() == "SWEDAVIA_API_KEY":
                        self.api_key = secret.strip().strip("\"'")
        if not self.api_key:
            raise FlightInfoError("Sätt SWEDAVIA_API_KEY eller starta med --demo.")
        self._last_query = None

    def get(self, path, params=None):
        if path == "/query":
            if self._last_query is not None:
                time.sleep(max(0, 2.1 - (time.monotonic() - self._last_query)))
            self._last_query = time.monotonic()
        url = BASE_URL + path + (("?" + urlencode(params)) if params else "")
        request = Request(url, headers={"Ocp-Apim-Subscription-Key": self.api_key,
                                        "Accept": "application/json"})
        try:
            with urlopen(request, timeout=20) as response:
                body = response.read()
                if path == "/heartBeat":
                    return {"status": response.status, "mode": self.mode}
                if response.status == 204 or not body.strip():
                    return {"flights": []}
                try:
                    return json.loads(body)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise FlightInfoError("API:et skickade inte giltig JSON.") from exc
        except HTTPError as exc:
            messages = {400: "Kontrollera datum och OData-filter.",
                        401: "Kontrollera din API-nyckel.",
                        403: "Kontrollera din FlightInfo-prenumeration.",
                        429: "Anropsgränsen är nådd. Vänta och försök igen."}
            raise FlightInfoError(f"HTTP {exc.code}: " + messages.get(exc.code, "API-anropet misslyckades.")) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise FlightInfoError("Nätverksfel eller timeout. Kontrollera anslutningen.") from None

    def flights(self, airport, day, direction):
        airport, day = airport_code(airport), parse_date(day)
        if direction not in {"arrivals", "departures"}:
            raise ValueError("Välj arrivals eller departures.")
        return flights_from(self.get(f"/{airport}/{direction}/{day}"))

    def query(self, expression, max_pages=50):
        result, seen_tokens = [], set()
        params = {"filter": expression, "count": 1000}
        for _ in range(max_pages):
            payload = self.get("/query", params)
            batch = flights_from(payload)
            result.extend(batch)
            token = value(payload, "continuationToken")
            if not batch or not token:
                return result
            if token in seen_tokens:
                raise FlightInfoError("API:et upprepade sin continuation token; hämtningen avbröts.")
            seen_tokens.add(token)
            params["continuationtoken"] = token
        raise FlightInfoError("Sidgränsen nåddes. Begränsa filtret till flygplats och datum.")

    def heartbeat(self):
        return self.get("/heartBeat")


class DemoClient:
    mode = "DEMO - syntetiska exempeldata, inga riktiga flyguppgifter"

    def flights(self, airport, day, direction):
        airport, day = airport_code(airport), parse_date(day)
        if direction not in {"arrivals", "departures"}:
            raise ValueError("Välj arrivals eller departures.")
        arrival = direction == "arrivals"
        cities = [("London LHR", "LHR", "SK", "SAS Scandinavian Airlines"),
                  ("Frankfurt", "FRA", "LH", "Lufthansa"),
                  ("Amsterdam", "AMS", "KL", "KLM"),
                  ("Copenhagen", "CPH", "SK", "SAS Scandinavian Airlines"),
                  ("Oslo", "OSL", "DY", "Norwegian"),
                  ("Paris", "CDG", "AF", "Air France")]
        flights = []
        for index in range(60):
            city, code, airline, name = cities[index % len(cities)]
            stamp = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(hours=5, minutes=index * 15)
            iso = lambda t: t.isoformat().replace("+00:00", "Z")
            complete = index < 5
            cancelled = index == 7
            times = {"scheduledUtc": iso(stamp),
                     "estimatedUtc": iso(stamp + timedelta(minutes=20)) if index % 8 == 0 else None,
                     "actualUtc": iso(stamp + timedelta(minutes=2)) if complete else None}
            flights.append({
                "flightId": "SK532" if index == 0 else f"{airline}{100 + index}",
                "departureAirportEnglish": city if arrival else AIRPORTS[airport],
                "arrivalAirportEnglish": AIRPORTS[airport] if arrival else city,
                "airlineOperator": {"name": name, "iata": airline},
                "arrivalTime" if arrival else "departureTime": times,
                "locationAndStatus": {"terminal": "T5" if airport == "ARN" else "T1",
                    "gate": None if index % 4 == 0 else str(10 + index % 20),
                    "flightLegStatus": "CAN" if cancelled else "LAN" if complete and arrival else "ACT" if complete else "SCH",
                    "flightLegStatusEnglish": "Cancelled" if cancelled else ("Landed" if arrival else "Departed") if complete else "Scheduled"},
                "baggage": {"baggageClaimUnit": "3" if arrival else None},
                "flightLegIdentifier": {"departureAirportIata": code if arrival else airport,
                                         "arrivalAirportIata": airport if arrival else code},
                "diIndicator": "I" if code == "LHR" else "S",
                "remarksEnglish": [{"text": "Synthetic demonstration flight"}],
            })
        return flights

    def query(self, expression, max_pages=50):
        # Deliberately a small, explicit subset, never eval() user input.
        clauses = re.split(r"\s+and\s+", expression.strip(), flags=re.IGNORECASE)
        fields = {}
        for clause in clauses:
            match = re.fullmatch(r"(airport|scheduled|flightType|flightId)\s+eq\s+'([A-Za-z0-9]+)'", clause, re.IGNORECASE)
            if not match or match[1].lower() in fields:
                raise ValueError("Demo stöder unika fält med eq, kombinerade med and: airport, scheduled, flightType, flightId.")
            fields[match[1].lower()] = match[2]
        if not {"airport", "scheduled", "flighttype"} <= fields.keys():
            raise ValueError("Demo kräver airport, scheduled (YYMMDD) och flightType (A/D).")
        if not re.fullmatch(r"\d{6}", fields["scheduled"]):
            raise ValueError("scheduled måste vara YYMMDD.")
        day = date.fromisoformat(f"20{fields['scheduled'][:2]}-{fields['scheduled'][2:4]}-{fields['scheduled'][4:]}").isoformat()
        direction = fields["flighttype"].upper()
        if direction not in {"A", "D"}:
            raise ValueError("flightType måste vara A eller D.")
        flights = self.flights(fields["airport"], day, "arrivals" if direction == "A" else "departures")
        return [f for f in flights if not fields.get("flightid") or f["flightId"].upper() == fields["flightid"].upper()]

    def heartbeat(self):
        return {"status": "simulerad OK", "mode": self.mode}
