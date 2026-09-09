# Small manual UX checklist

Run `python app.py` and open http://127.0.0.1:5000. These checks are **not yet marked as completed human UX tests**. Record date, tester, browser, and observations when someone performs them. Automated implementation checks do not establish usability with real users.

| # | Manual test | Expected result | Result / notes |
| --- | --- | --- | --- |
| 1 | Open the page; navigate with Tab; try a narrow phone-sized window. | Clear heading and five labeled selectors; visible keyboard focus; controls fit and wide tables scroll. | Not run |
| 2 | Try to choose a weight outside 1–5; optionally alter a form value in browser developer tools and submit. | Selectors offer only 1–5; server rejects missing, fractional, nonnumeric, or out-of-range weights. | Not run |
| 3 | Set weights to 2, 2, 5, 5, 3 and generate a recommendation. | Five ranked rows and a clearly identified top recommendation appear; selected weights remain. | Not run |
| 4 | Check ordering and open source scores/calculation. | ConnectSuite is first at 8.06, followed by 7.88, 7.41, 7.35, 5.82; winning calculation is 137/17. | Not run |
| 5 | Check monthly costs in the result table. | All costs use USD with two decimals; ConnectSuite is $149.00/month. | Not run |
| 6 | Generate once without an API key, then with a valid key after restarting. | No-key state says AI is unavailable; with a key, prose covers four requested points. Rankings are identical; check factual claims against scores. | Not run |
| 7 | Click Approve Recommendation, inspect SQLite using the README command, then refresh. | Confirmation appears; one `approved` row for the top vendor has a UTC timestamp; refresh adds no duplicate. | Not run |
| 8 | Generate again, click Reject / Needs Review, and inspect SQLite. Restart the app and inspect again. | A `needs_review` row and confirmation appear; both decisions survive restart. | Not run |

Tester: __________  Date: __________  Browser/device: __________

Observations and improvements: __________________________________________

Implementation checks are documented separately in README.md. No real-user study or live Claude call has been claimed.

## Implementation check record — September 9, 2026

Agent-run checks passed for all 3,125 weight combinations, invalid inputs, Flask rendering, missing-key behavior, mocked Claude responses, and SQLite approve/reject persistence. A running-app browser check confirmed the demo weights, ranking, costs, and desktop layout. These are implementation checks, not a human usability study. Narrow-screen and keyboard walkthroughs and a live Claude explanation remain optional manual checks; the checklist above intentionally remains unclaimed.
