"""Optional current-flight provider. Credentials are never written to disk."""
import json
import os
import re
import warnings
from datetime import datetime, timezone
from getpass import getpass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from flightinfo import AIRPORTS, FlightInfoError, airport_code, parse_date, swedish_today


def utc_time(raw, timezone_name=None):
    if not raw:
        return None
    try:
        instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if instant.tzinfo is None:
            if not timezone_name:
                return None
            instant = instant.replace(tzinfo=ZoneInfo(timezone_name))
        return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, AttributeError, KeyError):
        return None


def normalize_flight(row, direction):
    """Adapt provider fields into the existing terminal's flight representation."""
    departure = row.get("departure") or {}
    arrival = row.get("arrival") or {}
    airline = row.get("airline") or {}
    flight = row.get("flight") or {}
    leg = arrival if direction == "arrivals" else departure
    status = row.get("flight_status") or "unknown"
    status_codes = {"scheduled": "SCH", "active": "ACT", "landed": "LAN",
                    "cancelled": "CAN", "incident": "INC", "diverted": "DIV"}
    times = {target: utc_time(leg.get(source), leg.get("timezone"))
             for source, target in [("scheduled", "scheduledUtc"),
                                    ("estimated", "estimatedUtc"), ("actual", "actualUtc")]}
    # flight_status is the whole flight's state; departure actual is the local event.
    label = "Departed" if direction == "departures" and times["actualUtc"] else status.capitalize()
    def name(airport):
        return AIRPORTS.get(airport.get("iata")) or airport.get("airport") or airport.get("iata")
    return {
        "flightId": flight.get("iata") or flight.get("icao") or flight.get("number"),
        "departureAirportEnglish": name(departure),
        "arrivalAirportEnglish": name(arrival),
        "airlineOperator": {"name": airline.get("name"), "iata": airline.get("iata")},
        "arrivalTime" if direction == "arrivals" else "departureTime": times,
        "locationAndStatus": {"terminal": leg.get("terminal"), "gate": leg.get("gate"),
                              "flightLegStatus": status_codes.get(status, status),
                              "flightLegStatusEnglish": label},
        "baggage": {"baggageClaimUnit": arrival.get("baggage") if direction == "arrivals" else None},
        "flightLegIdentifier": {"departureAirportIata": departure.get("iata"),
                                 "arrivalAirportIata": arrival.get("iata")},
        "remarksEnglish": [{"text": "Source: Aviationstack"}],
    }


class AviationstackClient:
    mode = "LIVE - Aviationstack (dagens flyg; separat datakälla)"

    def __init__(self, api_key=None):
        self.api_key = (api_key or os.environ.get("AVIATIONSTACK_API_KEY", "")).strip()
        if not self.api_key:
            raise FlightInfoError("Sätt AVIATIONSTACK_API_KEY eller använd --ask-key tillsammans med --aviationstack.")

    @classmethod
    def with_prompt(cls):
        return cls(getpass("Aviationstack API-nyckel (visas inte): "))

    def get(self, params):
        # HTTPS only. Do not log this URL: this provider authenticates in the query.
        url = "https://api.aviationstack.com/v1/flights?" + urlencode({**params, "access_key": self.api_key})
        request = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read())
        except HTTPError as error:
            messages = {401: "Kontrollera din Aviationstack-nyckel.",
                        403: "Nyckeln eller abonnemanget saknar åtkomst.",
                        429: "Anropsgränsen är nådd. Kontrollera din kvot."}
            raise FlightInfoError(f"Aviationstack HTTP {error.code}: " + messages.get(error.code, "Anropet misslyckades.")) from None
        except (URLError, TimeoutError, OSError):
            raise FlightInfoError("Aviationstack: nätverksfel eller timeout.") from None
        except (ValueError, UnicodeDecodeError):
            raise FlightInfoError("Aviationstack skickade inte giltig JSON.") from None
        if not isinstance(payload, dict):
            raise FlightInfoError("Aviationstack skickade ett oväntat svarsformat.")
        if payload.get("error"):
            # Never echo provider messages: they might contain the request URL/key.
            error = payload["error"]
            code = error.get("code") if isinstance(error, dict) else None
            message = {"invalid_access_key": "Ogiltig API-nyckel.",
                       "usage_limit_reached": "Månadskvoten är slut.",
                       "function_access_restricted": "Funktionen ingår inte i abonnemanget.",
                       "https_access_restricted": "HTTPS nekades av abonnemanget; ingen osäker anslutning görs."}.get(code, "Åtkomst nekad eller ogiltiga parametrar. Kontrollera kontot och abonnemanget.")
            raise FlightInfoError("Aviationstack: " + message)
        records = payload.get("data", payload.get("results"))
        if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
            raise FlightInfoError("Aviationstack-svaret saknar en giltig flyglista.")
        return payload

    def flights(self, airport, day, direction, flight_id=None):
        airport, day = airport_code(airport), parse_date(day)
        if day != swedish_today().isoformat():
            raise ValueError("Aviationstack-läget stöder dagens realtidsflöde. Historiska/framtida datum stöds inte av denna adapter.")
        if direction not in {"arrivals", "departures"}:
            raise ValueError("Välj arrivals eller departures.")
        params = {"arr_iata" if direction == "arrivals" else "dep_iata": airport,
                  "limit": 100, "offset": 0}
        if flight_id:
            if not re.fullmatch(r"[A-Za-z0-9]{2,10}", flight_id):
                raise ValueError("Ange ett giltigt flygnummer, t.ex. SK532.")
            params["flight_iata"] = flight_id.upper()
        # One request per search keeps free-plan usage predictable. Never hide truncation.
        payload = self.get(params)
        records = payload.get("data", payload.get("results"))
        pagination = payload.get("pagination") or {}
        total = pagination.get("total") if isinstance(pagination, dict) else None
        if isinstance(total, int) and total > len(records):
            warnings.warn(f"Aviationstack: hämtade {len(records)} av {total} API-poster. Resultatet är begränsat till första sidan för att spara anrop.", UserWarning)
        elif len(records) >= 100:
            warnings.warn("Aviationstack: sidgränsen 100 nåddes; fler flyg kan finnas.", UserWarning)
        result = []
        for row in records:
            leg = row.get("arrival" if direction == "arrivals" else "departure") or {}
            if leg.get("iata") != airport:
                continue
            normalized = normalize_flight(row, direction)
            times = normalized["arrivalTime" if direction == "arrivals" else "departureTime"]
            scheduled = times["scheduledUtc"]
            # The selected airport's local scheduled day is the date shown to the user.
            if not scheduled:
                continue
            local_day = datetime.fromisoformat(scheduled.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Stockholm")).date().isoformat()
            if local_day == day and (not flight_id or ((row.get("flight") or {}).get("iata") or "").upper() == flight_id.upper()):
                result.append(normalized)
        return result

    def search(self, airport, day, direction, flight_id):
        if direction not in {"A", "D"}:
            raise ValueError("Riktningen måste vara A eller D.")
        return self.flights(airport, day, "arrivals" if direction == "A" else "departures", flight_id)

    def query(self, expression):
        raise ValueError("Aviationstack stöder inte Swedavias OData. Använd menyval 1, 2 eller 3.")

    def heartbeat(self):
        self.get({"dep_iata": "ARN", "limit": 1})
        return {"status": "OK", "mode": self.mode,
                "note": "Verifierat med ett flights-anrop (förbrukar ett API-anrop)."}
