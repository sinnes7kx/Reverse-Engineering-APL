"""Group flight records by city and add countries from a local lookup."""
import argparse
from aviationstack_client import AviationstackClient
import json
from zoneinfo import ZoneInfoNotFoundError
from collections import Counter
from pathlib import Path
from flightinfo import (DemoClient, LiveClient, FlightInfoError, airport_code,
                        parse_date, folded, value)


def destination_rows(flights, direction, search=""):
    with Path(__file__).with_name("city_country.json").open(encoding="utf-8") as stream:
        countries = {folded(k): v for k, v in json.load(stream)["city_to_country"].items()}
    key = "departureAirportEnglish" if direction == "arrivals" else "arrivalAirportEnglish"
    # Group names without case/accent differences but retain their display form.
    names, counts = {}, Counter()
    for flight in flights:
        city = value(flight, key) or "Unknown"
        normalized = folded(city.strip())
        names.setdefault(normalized, city)
        counts[normalized] += 1
    rows = []
    for normalized, count in counts.items():
        city = names[normalized]
        country = countries.get(normalized, "Unknown")
        if not search or folded(search) in folded(city) or folded(search) in folded(country):
            rows.append((city, country, count))
    return sorted(rows, key=lambda row: (-row[2], row[0].casefold()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--aviationstack", action="store_true")
    parser.add_argument("--ask-key", action="store_true")
    parser.add_argument("--airport", default="ARN", help="Airport name, IATA code or number from the main menu's airport list (1-10).")
    parser.add_argument("--date", default="idag", help="YYYY-MM-DD, YYYYMMDD or DD/MM/YYYY; defaults to today in Sweden. Also accepts idag, imorgon or igår.")
    parser.add_argument("--direction", choices=["arrivals", "departures"], default="departures")
    parser.add_argument("--filter", default="", help="City or country name (countries are in English).")
    args = parser.parse_args()
    if args.ask_key and not args.aviationstack:
        parser.error("--ask-key requires --aviationstack")
    try:
        client = (AviationstackClient.with_prompt() if args.ask_key else AviationstackClient()) if args.aviationstack else DemoClient() if args.demo else LiveClient()
        airport, day = airport_code(args.airport), parse_date(args.date)
        flights = client.flights(airport, day, args.direction)
        print(client.mode)
        if args.aviationstack:
            print("Grupperar flygplatsnamn från Aviationstack; landlistan kan sakna dessa namn. Antal gäller endast hämtade poster.")
        print(f"\n{airport} | {day} | {args.direction}\n")
        rows = destination_rows(flights, args.direction, args.filter)
        for city, country, count in rows:
            print(f"{city:28} {count:4} flyg  [{country}]")
        print(f"\n{len(rows)} städer, {sum(row[2] for row in rows)} flygposter.")
        print("Unknown = staden saknas i den lokala landlistan.")
        return 0
    except ZoneInfoNotFoundError:
        print("Tidszonsdata saknas. Kör: python -m pip install -r requirements.txt")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nAvslutar.")
        return 0
    except (ValueError, FlightInfoError, OSError) as error:
        print("Fel:", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
