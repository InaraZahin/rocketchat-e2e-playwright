# Rocket.Chat E2E Regression Suite

[![E2E](../../actions/workflows/e2e.yml/badge.svg)](../../actions/workflows/e2e.yml)

End-to-end regression tests for [Rocket.Chat](https://rocket.chat), written in **Python** with
**Playwright** and **pytest**. The suite starts its own disposable Rocket.Chat server in Docker,
so it runs the same way on a laptop and in CI.

## What it covers

40 tests: 33 through the browser and 7 against the REST API.

| Area | Tests | Highlights |
|---|---|---|
| Authentication | 5 | Valid login, wrong password, unknown user, logout survives reload |
| Messaging | 7 | Public and private channels, edit, delete, reactions, threads, quotes |
| Rooms | 8 | Create public/private channels, channel with members, DMs, favorite, hide, mark unread/read, leave and rejoin |
| Teams | 3 | Create team, add existing channel, create channel inside team |
| Search & directory | 5 | Sidebar search, permission scoping, directory for channels, users and teams |
| Administration | 2 | Admin creates a user; regular user is denied access |
| Display preferences | 3 | Extended, medium and condensed views persist across reloads |
| REST API | 7 | Health, authentication, authorization, message round-trip |

Every test is tagged either `smoke` (12 critical-path tests) or `regression` (28). The REST
tests also carry `api`. Select with `-m`, for example `pytest -m smoke`.

## Quick start

Requirements: Python 3.10+, Docker.

```bash
python -m venv .venv && source .venv/bin/activate
```

```bash
make install   # pip install -e ".[dev]" and the Chromium browser
```

```bash
make up        # start Rocket.Chat 9.0.0 + MongoDB, wait until healthy
```

```bash
make test      # run everything in parallel
```

```bash
make down      # stop the server and delete its data
```

Other entry points: `make smoke`, `make api`, `make headed` (watch the browser),
or plain `pytest` with any of its options, for example `pytest -k thread --headed`.

> **Rocket.Chat needs outbound internet access.** Since 7.x, an unlicensed workspace stays
> read-only until it has reported to `collector.rocket.chat`. The suite checks for this at
> startup and stops with a clear message instead of failing every messaging test.

## Configuration

All settings come from environment variables with an `RC_` prefix or a local `.env` file
(see [`.env.example`](.env.example)). The defaults match `docker-compose.yml`, so a local run
needs no configuration. To test another server:

```bash
RC_BASE_URL=https://chat.example.com RC_ADMIN_USERNAME=... RC_ADMIN_PASSWORD=... pytest
```

To test another Rocket.Chat release, set `RC_VERSION` before `make up`
(or use the *Run workflow* button in GitHub Actions).

## How the suite is designed

**Every test is independent.** Each test gets a brand-new user, plus fresh rooms and teams when
it needs them, all with unique names. No test depends on another test, on execution order,
or on data left behind by a previous run. That is what makes `pytest -n auto` safe.

**Arrange through the API, act through the UI, assert on both.** Setup goes through the REST
API because it is fast and deterministic. The behaviour under test is driven through the
browser. Assertions check what the user sees *and* what the server stored, so a test cannot
pass on an optimistic UI update that never reached the backend.

**No UI login except in the login tests.** Other tests start already signed in: an API token
is injected into the browser's storage. Only `test_auth.py` drives the real login form.

**Guaranteed cleanup.** Everything a test creates is registered for deletion as it is created,
and is removed afterwards even when the test fails. A failed cleanup becomes a warning and
never hides the real result.

**Locators a user would recognise.** Elements are found by ARIA role and accessible name
(`get_by_role("button", name="Create new")`), never by absolute XPath, `nth-child` or generated
CSS classes. Those break with every UI release.

**No sleeps.** Playwright waits for elements to be actionable, and web-first assertions
(`expect(...).to_be_visible()`) retry until a timeout. Server-side checks go through a small
`eventually()` helper that retries an assertion instead of sleeping a fixed time.

**Assertions only in tests.** Page objects describe what a user can do. Whether the result is
correct is decided in the test, where it is visible.

**Evidence only for failures.** For a failed test, Playwright keeps a trace (open it with
`playwright show-trace`), a screenshot and a video in `test-results/`. Passing tests leave
nothing behind, and nothing is written into the source tree.

## Project structure

```
framework/
  config.py          typed settings from env vars / .env (pydantic-settings)
  data.py            unique names, password generator, User/Room/Team models
  wait.py            eventually(): retry an assertion against server state
  api/client.py      REST client used for setup, cleanup and verification
pages/
  base_page.py       BasePage / AuthenticatedPage (app shell)
  components/        NavBar, Sidebar, modal dialogs
  login_page.py  home_page.py  room_page.py  team_page.py
  directory_page.py  admin_users_page.py
tests/
  conftest.py        fixtures: API clients, fresh users/rooms/teams, signed-in pages, cleanup
  ui/                browser tests, one module per feature area
  api/               REST-level tests
docker-compose.yml   disposable Rocket.Chat + MongoDB (pinned versions)
.github/workflows/   lint, then the full suite against a fresh server, with reports
```

## Continuous integration

`.github/workflows/e2e.yml` runs on every push and pull request, nightly, and on demand:

1. Lint and format check with Ruff.
2. Start Rocket.Chat with Docker Compose and wait for its health check.
3. Run the suite on 4 workers and produce JUnit XML and a self-contained HTML report.
4. Upload the report and any failure traces, screenshots and videos as a build artifact.
   On failure, also print the Rocket.Chat server logs.

## Adding a test

1. Use the fixtures you need: `user_page` (signed-in browser), `user_api`, `channel`,
   `private_channel`, `team`, `admin_page`, `admin_api`, `cleanup`.
2. Interact through page objects. If an element is missing, add a role-based locator to the page.
3. Assert with `expect(...)` for the UI and `eventually(...)` for server state.
4. If the test creates something itself, register its deletion with `cleanup(...)` *before*
   the action that creates it.
5. Tag it `@pytest.mark.smoke` or `@pytest.mark.regression`.
