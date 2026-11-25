# Reverse Engineer a Result: Swedavia

## Step 1 - Look at the application

The supplied `Buster Swedavia FlightInfo API v2 .mov` is approximately 4 minutes 37 seconds long. Screenshots sampled throughout the recording show a Python terminal application in VS Code. The visible files include `airport.py`, `destinationer.py` and `city_country.json`.

Evidence from approximate sections of the recording:

- 00:00-00:50: flight details, 50-row pagination and a city-to-country JSON lookup.
- 01:20-01:50: six menu options and airport/date prompts.
- 02:00-03:10: arrival records and next/all/quit pagination controls.
- 03:20-04:10: UTC-to-Stockholm conversion, filtering of empty records, and a heartbeat route described in the on-screen explanation.
- Final section: a departure record and explanation of grouping destinations with country names.

These are visual observations from sampled frames, not an audio transcription. The sidebar's description of 263 cities and 59 countries is a claim in the recording; the original dataset was not provided.

## Step 2 - Ask questions

**What data is shown?** Flight identifiers, airlines, departure/arrival locations, scheduled/estimated/actual times, terminal, gate, baggage, remarks and a domestic/international indicator.

**What could create it?** An authenticated HTTP client receiving JSON from Swedavia, with a formatter that turns nested records into terminal text.

**What is uncertain?** Complete original source, exact query response envelopes, full lookup data, all date shortcuts and error behavior. The reconstruction uses explicit assumptions and documents the untested live boundary.

**Is a database necessary?** No visible feature requires one. The country lookup is a local JSON file. The implementation uses Python and its standard library plus `tzdata`. GenAI was used to inspect evidence, infer structure, write this reconstruction and prepare tests; the student should review and understand the generated code.

## Step 3 - Guess the inputs

Inputs are the menu choice, airport name/IATA code, date, optional upcoming-only choice, flight number, direction, OData filter and a subscription key for live access. The destination program additionally takes a city/country filter.

Synthetic data is selected explicitly by mode and labelled on screen. A missing live key is an error, not permission to use another person's credentials. Airport matching rejects ambiguous names such as `Stockholm` because both ARN and BMA are present.

## Step 4 - Guess the process

The probable flow is: read input, validate, select endpoint, request JSON, reject empty records, filter if requested, format times, then print pages. A separate destination flow counts each remote city and attaches a country from a local lookup. These are plausible internal steps consistent with the visible output, rather than proof of the original implementation.

The reconstruction separates terminal interaction from transport and transformation. `LiveClient` performs authenticated GET requests. `DemoClient` generates deterministic example records for any selected airport/date. Display code handles missing nested objects and does not expose the subscription key in errors.

## Step 5 - Sketch the steps

```text
function show_flights(direction):
    airport = ask_and_validate_airport()
    day = ask_and_validate_date()
    records = selected_client.fetch(airport, day, direction)
    records = discard_empty_records(records)
    if user_requests_upcoming:
        records = exclude_completed_cancelled_and_past_flights(records)
    for each page of 50 records:
        print_flight_details_with_UTC_and_Swedish_time(page)
        ask_next_all_or_return()

function destination_overview(records):
    count_records_by_remote_city()
    lookup_country_or_mark_unknown()
    filter_by_city_or_country()
    print_counts()
```

## Step 6 - Try building it

Run the commands in README.md. Compare the demo's fields, menu and pagination with the video. Test arrivals, departures, `SK532`, a missing flight number, country filtering, invalid input and returning from a page. Then obtain your own key to validate the live integration separately.

## Phase 1 - Research

Read the supplied exercise SH file as text (it is an assignment, not a shell program), extracted all six PDF pages, visually inspected them, and inspected sampled video frames. Consulted Swedavia's official [FlightInfo reference](https://apideveloperdev.swedavia.se/content/Using_the_FlightInfo_API.pdf) and [access FAQ](https://apideveloper.swedavia.se/faq). The original application is a terminal tool, so a web framework would add an unsupported design change.

## Phase 2 - Implementation

Built the shared client and transformations first, then the terminal menu and destination overview. Added a synthetic data source so the user can run the result without account setup. Retained recognizable filenames. Documentation is English and the terminal interface is Swedish, matching the assignment and recording respectively.

## Phase 3 - Completion and verification

Offline tests cover airport ambiguity, date rollover, Swedish daylight saving time, empty/malformed payloads, upcoming filtering, flight lookup, country aggregation, terminal pagination, menu recovery, query continuation, HTTP errors and URL encoding. Run `python -m unittest -v` to reproduce them. The automatic demo exercises all menu features without network access. Passing mocked tests does not prove compatibility with a live subscription or every production payload.

## Phase 4 - Problems and solutions

| Problem | Solution and remaining limit |
| --- | --- |
| Only a recording and partial source are available | Rebuild observed behavior and identify assumptions explicitly |
| No user-provided API key | Include labelled offline data; leave live validation for the user's key |
| Windows may lack timezone data | Declare `tzdata`; use Europe/Stockholm rather than a fixed one-hour offset |
| Flight records may lack gate, baggage or timestamps | Display a placeholder; reject completely empty records |
| Large flight lists | Separate terminal pages from API continuation handling |
| Infinite or repeated continuation | Stop on empty batches, reject repeated tokens, enforce a page limit |
| The original country lookup is unavailable | Supply an expanded editable lookup with selected name variants and label missing entries Unknown; it is not the original dataset or a current route list |
| Some OData syntax is complex | Restrict offline syntax explicitly; pass live expressions to the API |

## Conclusion

### Optional Aviationstack extension (2026-11-24)

After the reconstruction, an independent Aviationstack provider was added because the user could not access Swedavia's portal. The original Swedavia and demo modes remain available. Aviationstack data is normalized into the same display model, using HTTPS and an environment key or a hidden prompt. The adapter currently supports today's feed only, one page per search with an explicit truncation warning, and no OData. Country lookup coverage can differ because this provider returns airport names. One authenticated five-record ARN departure request and sample-record normalization succeeded; the broader behavior is covered by mocked tests. This extension is not evidence of how the original application was implemented.

The result is a runnable reconstruction of the observed terminal workflow with a deterministic demo and an optional live client. It demonstrates how to infer inputs, transformations and presentation from visible output. It is not recovered original source. Further work includes authenticating live requests, checking actual query envelopes, expanding the country lookup and comparing edge cases against the original application. The student should add personal observations, changes and learning outcomes before submission.
