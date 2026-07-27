# Gatewatch — Flight Frequency Tracker

**A serverless flight-monitoring system on Azure that tracks how often flights operate on specific routes, alerts on change, and manages itself through a live web dashboard.**

Built end-to-end on Azure: two independently deployed Function Apps, schemaless data storage, transactional email, a live third-party API integration with deliberate quota isolation, and a hand-designed frontend.

## Why this project

Most flight trackers are read-only — they show you a schedule. GateWatch is a small piece of *infrastructure*: it watches routes over time, reacts to change, manages its own data lifecycle (expiring and removing stale routes automatically), and exposes that control to a real UI instead of a config file. It was built to solve an actual personal problem (tracking flight frequency ahead of travel dates) and shaped by real production concerns along the way.

## Architecture

```
Website ──▶ HTTP Function App ──▶ Table Storage ◀── Timer Function App ──▶ SerpAPI
                                                            │
                                                            ▼
                                              Azure Communication Services (email)
```

- **Timer-triggered Function App** — runs on a daily schedule, checks every tracked route's live flight frequency, and emails an alert when frequency changes, when a route's date has passed (auto-removing it), or when the upstream API call itself fails.
- **HTTP-triggered Function App** — a small REST-style API (list / add / delete) backing the frontend. Adding a route resolves its frequency live, on a *separate* API key from the timer job, so interactive usage can never eat into the background job's monthly quota.
- **Azure Table Storage** — a schemaless store for tracked routes, chosen deliberately over a relational database for a workload this size: no migrations, minimal cost, and a natural fit for the composite-key duplicate protection the app relies on.
- **Static frontend** — a self-contained HTML/CSS/JS dashboard, styled after an airport split-flap departure board, with modal-based add/delete flows gated behind a shared access code and a flight-path success animation on completion.

## Engineering decisions worth calling out

- **Quota isolation by design.** The interactive "add route" path and the background daily check use two separate API keys against the same third-party service, so a burst of manual testing or usage can't silently starve the automated alerting the app exists to provide.
- **Failure paths are handled, not assumed away.** The daily check distinguishes between "the API call failed" and "the route legitimately has zero flights" — collapsing those two cases was an early bug that would have quietly corrupted stored data and sent false alerts; the fix required reordering validation *before* parsing the response, not after.
- **Cost-aware by default.** Expired routes are detected and skipped *before* an API call is made, not after, so no quota is spent checking a route that's about to be deleted anyway.
- **Security trade-offs made consciously, not by accident.** A single shared access code is a deliberate, documented choice appropriate for a single-user personal tool — sent as a request header rather than a URL query parameter specifically to keep it out of server logs, with the trade-off (not real multi-user auth) called out rather than left implicit.
- **Two independently deployable services.** The interactive API and the background job are split into separate Function Apps on purpose, so the stable, "done" alerting logic can never be affected by active iteration on the website side.

## Repo structure

```
.
├── http-function/       # HTTP-triggered Function App (list / add / delete routes)
├── timer-function/       # Timer-triggered Function App (daily frequency check + alerts)
└── frontend/             # Static site (index.html) — deployable to Azure Static Web Apps
```

## Tech stack

**Backend:** Python, Azure Functions (HTTP + Timer triggers), Azure Table Storage, Azure Communication Services (email), SerpAPI (Google Flights data)
**Frontend:** HTML, CSS, vanilla JavaScript
**Infrastructure:** Azure Static Web Apps, GitHub-driven deployment

## Prerequisites

- An Azure subscription
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- Python 3.x (matching a version supported by Azure Functions)
- A [SerpAPI](https://serpapi.com/) account with **two** API keys (see below)
- An Azure Communication Services resource with Email enabled, plus a verified sender domain

## Azure resources needed

| Resource | Purpose |
|---|---|
| Storage account (General-purpose v2, Standard, LRS) | Backs both Function Apps and holds the `MasterTable` table |
| Function App #1 (Python, Consumption plan) | Hosts the timer trigger |
| Function App #2 (Python, Consumption plan) | Hosts the HTTP endpoints |
| Azure Communication Services + Email | Sends alert and confirmation emails |
| Static Web App | Hosts the frontend, connected to this repo |

## Environment variables

Set these in each Function App's **Configuration → Application settings** in the Portal (not just `local.settings.json`, which is local-only).

### Timer-triggered Function App

| Variable | Description |
|---|---|
| `AzureWebJobsStorage` | Storage account connection string |
| `SERPAPI_KEY` | SerpAPI key used for the daily frequency check |
| `ACS_EMAIL_KEY` | Azure Communication Services access key |
| `ACS_ENDPOINT` | Azure Communication Services endpoint URL |

### HTTP-triggered Function App

| Variable | Description |
|---|---|
| `AzureWebJobsStorage` | Same storage account connection string |
| `ACCESS_CODE` | Shared secret required to add or delete routes |
| `Serp_API2` | A **separate** SerpAPI key, used only when a route is added |
| `ACS_EMAIL_KEY` | Azure Communication Services access key |
| `ACS_ENDPOINT` | Azure Communication Services endpoint URL |

## API endpoints

All endpoints live on the HTTP-triggered Function App. `POST` and `DELETE` require the access code sent as an `x-api-key` header.

| Method | Route | Body / params | Description |
|---|---|---|---|
| `GET` | `/api/http_get` | — | Lists all tracked routes |
| `POST` | `/api/http_post` | `{ "DEP": "DEL", "ARR": "BOM", "DATE": "2026-08-15" }` | Adds a route; resolves frequency live before saving |
| `DELETE` | `/api/http_del` | `?PartitionKey=Route&RowKey=DEL-BOM-2026-08-15` | Removes a route |

## Deployment

1. **Create the storage account and both Function Apps** in the Portal, linking each Function App to the same storage account.
2. **Create the `MasterTable` table** in the storage account (Data storage → Tables → + Table).
3. **Set the environment variables** above on each Function App.
4. **Deploy each backend folder:**
   ```
   cd http-function
   func azure functionapp publish <your-http-function-app-name>

   cd ../timer-function
   func azure functionapp publish <your-timer-function-app-name>
   ```
5. **Enable CORS** on the HTTP Function App (Portal → CORS) for your Static Web App's domain.
6. **Create the Static Web App**, connect it to this repo with `frontend/` as the app location, and let it auto-deploy.
7. Open the deployed site, enter your access code, and add your first route.

