# Reverse Engineer a Result — APL Project 2026

## Assignment
Recreate an existing application provided by Najmaddin using generative AI. Work backwards from its visible behavior to infer its inputs, data structures and processing logic, then implement a comparable application. The goal is to reconstruct functionality, not claim recovery of the original source code.

## 1. Look at the application
The supplied project documentation describes a recording of Swedavia FlightInfo API v2, a Swedish Python terminal application. Observable features include arrivals, departures, flight search, OData queries, heartbeat, automatic demonstration and paginated flight information. This description is based on the research notes included with the reconstruction; the original recording was not independently reviewed during this documentation update.

## 2. Ask questions
What data is shown? Structured flight records containing flight identifiers, airlines, airports, scheduled, estimated and actual times, gates, terminals and baggage information.
What could create this? A Python HTTP client that retrieves JSON from a flight information API, processes records and formats them for terminal output.
Is a database required? Not for the reconstructed workflow. Country information is stored in a local JSON lookup.
Generative AI helps infer possible implementations, produce code and design tests. Lovable and v0 were suggested in the assignment, but are not required for a Python CLI.

## 3. Guess the inputs
- Menu choice and airport name or IATA code.
- Date, flight direction and optional flight identifier.
- Upcoming-only selection or OData filter.
- Subscription key for authenticated live requests.
- City or country filter for destination summaries.

## 4. Guess the process
Validate input, select the provider, retrieve flight records, discard empty records, filter results, convert timestamps to Swedish local time and display pages of 50 rows. The destination tool groups records by city and looks up country names. These are inferred implementation steps, not proof of the original application's internal logic.

## 5. Sketch the steps
```python
def show_flights(airport, date, direction):
    # Validate airport and date
    # Retrieve records from the selected provider
    # Filter and format the records
    # Display results in pages of 50
    pass
```
Conceptual pseudocode only; the actual implementation separates the terminal interface from the API clients and data transformations.

## 6. Try building it
The supplied reconstruction contains airport.py, flightinfo.py, aviationstack_client.py, destinationer.py, city_country.json and two automated test modules. It supports synthetic offline demo data and authenticated live providers.

Run:
```bash
python -m pip install -r requirements.txt
python airport.py --demo
python airport.py --demo --auto
python -m unittest -v
```

## Verification and limitations
On 25 November 2026, all 33 automated tests passed in a clean extraction without the local .env file. Live API access was not retested during this documentation update. Existing project notes describe prior successful live requests on 24 November. The original full source and country dataset were not available, so exact parity cannot be claimed.

## Conclusion
The exercise demonstrates reasoning backwards from observable output, identifying input requirements, proposing algorithms and validating an independent implementation. AI-assisted code must be reviewed and understood by the student. Add personal reflections and any comparison results before submission.

## Security
Never publish .env, API keys, virtual environments or recordings containing credentials. Use your own subscription key for live requests.
