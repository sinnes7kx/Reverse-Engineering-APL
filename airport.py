"""Interactive reconstruction of the terminal application shown in the video."""
import argparse
from aviationstack_client import AviationstackClient
from zoneinfo import ZoneInfoNotFoundError

from flightinfo import (AIRPORTS, DemoClient, LiveClient, FlightInfoError,
                        airport_code, parse_date, value, format_time,
                        flight_times, flight_filter, upcoming, swedish_today)

PAGE_SIZE = 50


def ask(prompt, parser):
    while True:
        try:
            return parser(input(prompt))
        except ValueError as error:
            print(error)


def ask_airport(default="ARN"):
    default = airport_code(default)
    print("\nTillgängliga flygplatser:")
    for number, (code, name) in enumerate(AIRPORTS.items(), 1):
        print(f"  {number:2}. {name} ({code})")
    selected = ask(f"Välj nummer, kod eller namn [{default} - {AIRPORTS[default]}]: ",
                   lambda text: airport_code(text.strip() or default))
    print(f"Vald flygplats: {AIRPORTS[selected]} ({selected})")
    return selected


def ask_date():
    today = swedish_today()
    print("\nDatum: Enter/1 = idag | 2 = imorgon | 3 = igår")
    print("Annat datum: YYYY-MM-DD, YYYYMMDD eller DD/MM/YYYY (med årtal).")
    selected = ask(f"Ange datum (YYYY-MM-DD) [{today.isoformat()}]: ",
                   lambda text: parse_date({"1": "idag", "2": "imorgon", "3": "igår"}.get(text.strip(), text), today=today))
    print(f"Valt datum: {selected}")
    return selected


def print_flight(flight, index):
    airline = value(flight, "airlineOperator") or {}
    status = value(flight, "locationAndStatus") or {}
    identity = value(flight, "flightLegIdentifier") or {}
    times = flight_times(flight)
    print(f"[{index}] {value(flight, 'flightId') or 'N/A'} | {value(airline, 'name') or 'N/A'} ({value(airline, 'iata') or '-'})")
    for label, key in (("From", "departure"), ("To", "arrival")):
        place = value(flight, key + "AirportEnglish") or value(identity, key + "AirportIata") or "N/A"
        print(f"  {label:8}: {place}")
    print(f"  Status  : {value(status, 'flightLegStatusEnglish') or value(status, 'flightLegStatus') or 'N/A'}")
    print(f"  Terminal: {value(status, 'terminal') or 'N/A'}   Gate: {value(status, 'gate') or 'N/A'}")
    print(f"  Baggage : {value(value(flight, 'baggage'), 'baggageClaimUnit') or 'N/A'}")
    for label, key in (("Sched", "scheduledUtc"), ("Est", "estimatedUtc"), ("Actual", "actualUtc")):
        print(f"  {label:8}: {format_time(value(times, key))}")
    print(f"  D/I     : {value(flight, 'diIndicator') or '-'}")
    remarks = value(flight, "remarksEnglish") or []
    if isinstance(remarks, list):
        texts = [str(value(r, "text", "")) if isinstance(r, dict) else str(r) for r in remarks]
        if texts:
            print("  Remarks : " + "; ".join(texts))
    print("-" * 76)


def print_flights_paged(flights, page_size=PAGE_SIZE, interactive=True):
    if not flights:
        print("Inga flyg matchade sökningen.")
        return
    if page_size < 1:
        raise ValueError("Sidstorlek måste vara större än noll.")
    show_all = not interactive
    for start in range(0, len(flights), page_size):
        for i, flight in enumerate(flights[start:start + page_size], start + 1):
            print_flight(flight, i)
        shown = min(start + page_size, len(flights))
        print(f"Visar {shown}/{len(flights)} - ({len(flights) - shown} kvar)")
        if shown < len(flights) and not show_all:
            while True:
                choice = input("[Enter] nästa sida | [a] visa alla | [q] tillbaka: ").strip().lower()
                if choice in {"", "a", "q"}:
                    break
                print("Välj Enter, a eller q.")
            if choice == "q":
                return
            show_all = choice == "a"


def auto_demo(client):
    day = parse_date("idag")
    print("\n" + client.mode)
    print("Heartbeat:", client.heartbeat())
    for direction in ("arrivals", "departures"):
        flights = client.flights("ARN", day, direction)
        print(f"\nARN {direction} {day}: {len(flights)} flyg; visar högst två.")
        print_flights_paged(flights[:2], interactive=False)
    if isinstance(client, AviationstackClient):
        print("Aviationstack-demonstrationen är klar. OData finns endast hos Swedavia.")
        return
    expression = flight_filter("ARN", day, "D")
    print("\nOData:", expression)
    flights = client.query(expression)
    print(f"OData gav {len(flights)} flyg; visar högst två.")
    print_flights_paged(flights[:2], interactive=False)
    if flights and value(flights[0], "flightId"):
        flight_id = value(flights[0], "flightId")
        print("\nSök flyg:", flight_id)
        print_flights_paged(client.query(flight_filter("ARN", day, "D", flight_id)), interactive=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="Synthetic data; no API key required.")
    mode.add_argument("--live", action="store_true", help="Use your SWEDAVIA_API_KEY.")
    mode.add_argument("--aviationstack", action="store_true", help="Use AVIATIONSTACK_API_KEY for today's flights.")
    parser.add_argument("--ask-key", action="store_true", help="Prompt privately for an Aviationstack key for this run.")
    parser.add_argument("--auto", action="store_true", help="Demonstrate all endpoints, then exit.")
    args = parser.parse_args()
    if args.ask_key and not args.aviationstack:
        parser.error("--ask-key requires --aviationstack")
    try:
        client = (AviationstackClient.with_prompt() if args.ask_key else AviationstackClient()) if args.aviationstack else DemoClient() if args.demo else LiveClient()
        print(client.mode)
        if args.aviationstack:
            print("Dagens flyg, högst 100 API-poster per sökning. Flygplatsnamn kan skilja sig från Swedavia.")
        if args.auto:
            auto_demo(client)
            return 0
        last_airport = "ARN"
        while True:
            title = "Aviationstack - Python-klient" if args.aviationstack else "Swedavia FlightInfo API v2 - Python-klient"
            print("\n" + "=" * 62 + "\n" + title + "\n" + "=" * 62)
            print("1. Ankomster (arrivals) för en flygplats och datum\n"
                  "2. Avgångar (departures) för en flygplats och datum\n"
                  "3. Sök specifikt flygnummer\n"
                  "4. OData-förfrågan (endast Swedavia/demo)\n"
                  "5. Testa API-anslutning\n"
                  "6. Demonstrera alla endpoints automatiskt\nq. Avsluta")
            choice = input("Välj [1-6] eller q: ").strip().lower()
            try:
                if choice == "q":
                    return 0
                if choice in {"1", "2"}:
                    airport = last_airport = ask_airport(last_airport)
                    day = ask_date()
                    only_upcoming = input("Visa endast kommande flyg? [j/N]: ").strip().lower() in {"j", "ja", "y", "yes"}
                    flights = client.flights(airport, day, "arrivals" if choice == "1" else "departures")
                    if only_upcoming:
                        flights = [f for f in flights if upcoming(f)]
                    print_flights_paged(flights)
                elif choice == "3":
                    airport = last_airport = ask_airport(last_airport)
                    day = ask_date()
                    direction = input("Ankomst A eller avgång D [D]: ").strip().upper() or "D"
                    flight_id = input("Flygnummer (t.ex. SK532): ").strip().upper()
                    if not flight_id:
                        raise ValueError("Ange ett flygnummer.")
                    flights = client.search(airport, day, direction, flight_id) if args.aviationstack else client.query(flight_filter(airport, day, direction, flight_id))
                    print_flights_paged(flights)
                elif choice == "4":
                    if args.aviationstack:
                        print("Aviationstack stöder inte OData. Använd menyval 1, 2 eller 3.")
                        continue
                    example = flight_filter("ARN", parse_date("idag"), "D")
                    print("Exempel:", example)
                    expression = input("OData-filter [Enter = exemplet]: ").strip() or example
                    print_flights_paged(client.query(expression))
                elif choice == "5":
                    print(client.heartbeat())
                elif choice == "6":
                    auto_demo(client)
                else:
                    print("Välj 1-6 eller q.")
            except (FlightInfoError, ValueError) as error:
                print("Fel:", error)
    except FlightInfoError as error:
        print("Fel:", error)
        return 1
    except ZoneInfoNotFoundError:
        print("Tidszonsdata saknas. Kör: python -m pip install -r requirements.txt")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nAvslutar.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
