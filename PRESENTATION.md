# English recording outline and submission checklist

This is an outline to adapt after running and understanding the project, not a claim that a presentation has been recorded. The supplied PDF requires an English screen recording lasting at least four minutes. Aim for about five minutes and verify the actual recording duration.

## Suggested recording flow

| Time | Show | Explain in your own words |
| --- | --- | --- |
| 00:00-00:35 | Project directory and README | The task was to reconstruct an existing application's behavior. This version recreates a Python terminal flight-information tool. |
| 00:35-01:15 | RECONSTRUCTION steps 1-3 | Describe observed fields, menu options, inferred inputs and the distinction between evidence and assumptions. |
| 01:15-02:15 | `airport.py --demo`, arrivals | Choose ARN and a date, display all flights, then demonstrate next-page and return. Point out that data is synthetic. |
| 02:15-02:55 | Search and destination tool | Search SK532; filter destinations by Germany. Explain grouping and incomplete country lookup. |
| 02:55-03:40 | `flightinfo.py` | Explain request/response flow, the environment key, validation and UTC/CET/CEST conversion. Do not display a real key. |
| 03:40-04:25 | `python -m unittest -v` | Discuss tests, missing values, invalid dates and pagination. Distinguish offline tests from live verification. |
| 04:25-05:00 | Conclusion | Explain what you personally learned, what you changed and what remains to verify or improve. |

Use a readable terminal font and clear audio. Demonstrate commands slowly. Rehearse first and check the final file's length, screen readability and sound. Do not claim that a live integration works until you have actually tested it.

## Publish your code to GitHub

These are manual submission instructions; this project has not been published automatically. Create an empty repository in your own account, then run the following inside the `Swedavia` directory. Replace the example owner and repository before adding the remote.

```powershell
git init
git add .
git status
git commit -m "Reconstruct Swedavia FlightInfo terminal application"
git branch -M main
git remote add origin https://github.com/sinnes7kx/Reverse-Engineering-APL.git
git push -u origin main
```

Review staged files before committing. Include source, tests and documentation; exclude virtual environments, credentials and the source recording. The provided `.gitignore` excludes common local environment files. GitHub authentication is required for pushing.

Before submission, update the documentation with your own research notes, actual live-test results if available, changes and personal conclusions. Submit the repository and recording according to your course instructions.
