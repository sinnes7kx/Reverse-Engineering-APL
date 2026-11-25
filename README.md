## Swedavia setup verified on 2026-11-24

Run python airport.py to start Swedavia live mode. The supplied FlightInfo key is configured in the local, Git-ignored .env file. Verification returned HTTP 200 and 277 ARN departures. AirportInfo and WaitTime keys are not needed. The distributable ZIP excludes .env; after extraction, set SWEDAVIA_API_KEY or create a local .env containing SWEDAVIA_API_KEY=your-key.

# Swedavia FlightInfo v2 - reconstruction

A small Python terminal application reconstructed from the supplied Swedavia recording. This is new educational code, not the original source. The interface follows the Swedish terminal shown in the video; documentation is in English as required by the assignment.

## Start on Windows

Install Python 3.10 or later. Open PowerShell in this project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe airport.py --demo
```

No activation script is required. On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` instead. The only external dependency is `tzdata`, needed for Stockholm time on systems without an IANA timezone database, including typical Windows installations. HTTP, JSON and tests use Python's standard library.

## Try the reconstruction

The six menu choices reproduce the visible application: arrivals, departures, flight search, OData query, heartbeat, and automatic demonstration. Enter an airport code or name, then choose a date starting from today in Sweden. The default is now Swedavia live mode; use --demo for offline examples. Its 60 synthetic flights exercise the 50-row pagination. Try `ARN`, Enter for today, and `SK532`. Choose **N** for upcoming-only to see the entire demo list.

Choose an airport by its displayed number (1-10), IATA code or name. Partial names such as `landv` work when unambiguous; typing `Stockholm` shows Arlanda and Bromma as explicit choices. Enter accepts the displayed airport: initially ARN, then the last airport selected during this run. The app confirms the chosen airport.

The date question remains in the workflow and displays today's full Swedish date as a bracketed placeholder/default, for example:

```text
Ange datum (YYYY-MM-DD) [2026-11-23]:
```

Press Enter or `1` for today, `2` for tomorrow or `3` for yesterday. For another date, include the year: `2027-01-02`, `20270102` or `2/1/2027`. The displayed default is recalculated for each new date prompt; it is not hardcoded. Yearless inputs such as `25/11` and numeric offsets such as `+3` are rejected. The named shortcuts (`idag`, `imorgon`, `igår`) and all three complete date formats also work with `destinationer.py --date`; numbered date choices are only available in the interactive prompt. Invalid calendar dates are rejected and the selected full date is confirmed on screen.

```powershell
.\.venv\Scripts\python.exe airport.py --demo --auto
.\.venv\Scripts\python.exe destinationer.py --demo --airport GOT --date 2026-02-26
.\.venv\Scripts\python.exe destinationer.py --demo --filter Germany
.\.venv\Scripts\python.exe -m unittest -v
```

The menu supports Enter for the next page, `a` for all remaining rows, and `q` to return. Ctrl+C exits. The destination tool groups by city and searches city/country names. Its expanded country dictionary includes cities, selected airport-name variants and English/Swedish aliases; unknown places are labelled `Unknown`. Matching ignores case and accents, but does not perform fuzzy matching or merge different airport names. The lookup is not a list of current Swedavia routes. Counts represent flight records, not guaranteed unique physical aircraft movements.

## Use real flight data

### Alternative: Aviationstack

You can use an Aviationstack subscription independently of Swedavia. Start with a private key prompt (the key is kept only in memory for this run):

```powershell
.\.venv\Scripts\python.exe airport.py --aviationstack --ask-key
```

Alternatively set `AVIATIONSTACK_API_KEY` in your environment and omit `--ask-key`. The same flags work with `destinationer.py`. The app never writes your key to source files, configuration or the ZIP. Reset any key shared publicly through your account dashboard.

This adapter implements the current-flight feed only. It accepts today's Swedish date, fetches one page of at most 100 API records per search, and filters by the chosen airport's scheduled local date. Results may be incomplete; larger result sets produce a warning. A status check also uses one request; `--auto` uses three. There is no automatic polling or extra request for country information. Historical and future dates are rejected locally; they require separate functionality and may require a paid plan. OData is a Swedavia feature; use menu options 1-3 with Aviationstack.

The provider supplies airport names, which may not match the city lookup. Destination counts cover only fetched records, and unmatched airport names retain `Unknown` countries. Missing fields are displayed as placeholders. Flight times are normalized to UTC before the existing Swedish-time display. The sources and data coverage differ from Swedavia; this is an optional extension of the reconstruction.

References: [Aviationstack quickstart](https://docs.apilayer.com/aviationstack/docs/quickstart-guide), [API FAQ](https://aviationstack.com/faq), and [current plans](https://aviationstack.com/pricing). Free-plan request quotas are limited; consult your dashboard for current access and remaining usage.

Live verification on 2026-11-24: one authenticated HTTPS request for ARN departures with `limit=5` succeeded and returned five records. The first record was converted into the app's display model successfully. This verifies that the supplied account could access the feed at that time; it does not verify every airport, field or the completeness of a search. No key or raw response was saved. All 33 offline tests also passed after adding the adapter.

### Swedavia

Obtain your own FlightInfo subscription key through the [Swedavia Developer Portal](https://apideveloper.swedavia.se/). The [official FAQ](https://apideveloper.swedavia.se/faq) describes registration and the subscription header.

```powershell
$env:SWEDAVIA_API_KEY = Read-Host 'Your Swedavia subscription key' -MaskInput
.\.venv\Scripts\python.exe airport.py --live
.\.venv\Scripts\python.exe destinationer.py --live --airport ARN --date idag
```

`-MaskInput` requires PowerShell 7.1+. In older PowerShell, set the environment variable using your preferred local secret-handling method, then run the same Python commands. No key from the recording is included or used. The Swedavia client also reads a local `.env` file when the environment variable is absent. Live mode never silently substitutes demo data.

API routes and query syntax were checked against [Swedavia's FlightInfo documentation](https://apideveloperdev.swedavia.se/content/Using_the_FlightInfo_API.pdf). The date picker uses today's Swedish calendar date as its starting point. The selected date is sent unchanged to the API: arrivals/departures select a UTC calendar day, not a midnight-to-midnight Swedish time window. Times are displayed in UTC and Europe/Stockholm, including the date and CET/CEST. Query `scheduled` follows the API's separate YYMMDD convention. See the developer portal for current access and data availability. Live responses were not tested with a subscription key.

Demo queries support only `eq` conditions joined with `and`, with required `airport`, `scheduled` and `flightType`, plus optional `flightId`. Other expressions produce a clear error. Live mode sends the filter to Swedavia. Example:

```text
airport eq 'ARN' and scheduled eq '260226' and flightType eq 'D' and flightId eq 'SK532'
```

## Files

| File | Purpose |
| --- | --- |
| `airport.py` | Menu, input prompts and paginated flight display |
| `flightinfo.py` | Live/demo clients, validation, date/time conversion and filtering |
| `aviationstack_client.py` | Optional current-flight provider and private key prompt |
| `test_aviationstack.py` | Offline provider mapping, request and error tests |
| `destinationer.py` | City/country overview |
| `city_country.json` | Expanded local city/country lookup with selected name variants |
| `test_flightinfo.py` | Offline behavior and mocked HTTP tests |
| `RECONSTRUCTION.md` | Six reverse-engineering steps and project phases |
| `PRESENTATION.md` | English recording outline and GitHub instructions |

## Limitations

The recording provides partial source and UI evidence; it cannot establish the complete original behavior. The heartbeat route is based on the recording. API pagination assumes a top-level `flights` list and optional `continuationToken`; it stops on an empty batch or missing token and rejects repeated tokens. A 50-page limit prevents endless fetching. Query calls are spaced at least 2.1 seconds apart. Errors return to the menu. There is no database, GUI, automatic background polling or claim that synthetic flights match real schedules.

The original 263-city country dataset was not supplied and has not been recreated in full. The source video and any credentials visible in it are not part of this distributable project. The student's recording remains a separate submission step.
