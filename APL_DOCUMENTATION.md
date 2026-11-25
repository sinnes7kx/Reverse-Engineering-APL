# Reverse Engineer a Result — APL Project 2026

## Assignment
Recreate an existing application provided by Najmaddin using generative AI. Work backwards from its visible behavior to infer inputs, data structures and processing logic. The goal is an independent reconstruction, not recovery of original source code.

## 1. Look at the application
The supplied reconstruction notes describe a recording of Swedavia FlightInfo API v2, a Swedish Python terminal application with arrivals, departures, flight search, OData, heartbeat, automatic demonstration and pagination. The original recording was not independently reviewed during this documentation update.

## 2. Ask questions
The data consists of structured flight records, including flight identifiers, airlines, airports, timestamps, terminals, gates and baggage. A Python HTTP client could retrieve JSON and format it for terminal display. A database is not required for the reconstructed workflow; a local JSON file maps cities to countries. Generative AI assists with inferring logic, writing code and designing tests. Lovable and v0 are suggested in the assignment but not required for a Python CLI.

## 3. Guess the inputs
Menu selection, airport name or IATA code, date, flight direction, optional flight number, upcoming-only selection, OData filter, subscription key and optional city/country filter.

## 4. Guess the process
Validate inputs, select a provider, retrieve JSON, discard empty records, filter results, convert timestamps to Swedish local time and display pages of 50 rows. Group destinations by city and look up countries. These are plausible steps rather than proof of the original internal implementation.

## 5. Sketch the steps
```python
def show_flights(airport, date, direction):
    # Validate airport and date
    # Retrieve records from the selected provider
    # Filter and format records
    # Display results in pages of 50
    pass
```
This is conceptual pseudocode, not the actual implementation.

## 6. Try building it
The reconstruction contains airport.py, flightinfo.py, aviationstack_client.py, destinationer.py, city_country.json and two test modules. It supports synthetic demo data and authenticated live providers.

```bash
python -m pip install -r requirements.txt
python airport.py --demo
python airport.py --demo --auto
python -m unittest -v
```

## Verification and limitations
All 33 automated tests passed on 25 November 2026 in a clean extraction without the local .env file. Live access was not retested; existing project notes describe successful requests on 24 November. Exact parity with the original cannot be claimed. The student should add personal reflections and comparison results before submission.

## Conclusion
The exercise demonstrates reasoning backwards from observable output, identifying inputs, proposing algorithms and validating an independent implementation. AI-assisted code must be reviewed and understood by the student.

## Security
Never publish .env, API keys, virtual environments or recordings containing credentials. Use your own subscription key for live requests.
