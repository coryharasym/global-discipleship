# Discipleship Bands

A persistent, mobile-first Phase 1 application for adult, same-gender groups of 3–5. Django 5.2 LTS supplies authentication, CSRF, forms, migrations, and server-rendered pages. SQLite stores accounts and membership; WhiteNoise serves local assets and Waitress runs WSGI. No external fonts, frontend build chain, or cloud database is needed.

## Development

Use the existing isolated checkout; do not create a worktree for setup. Python 3.12 is the validated runtime.

```sh
cd /workspace/global-discipleship
python3 -m venv /workspace/discipleship-venv
/workspace/discipleship-venv/bin/python -m pip install -r requirements.txt
/workspace/discipleship-venv/bin/python manage.py migrate --noinput
/workspace/discipleship-venv/bin/python manage.py collectstatic --noinput
/workspace/discipleship-venv/bin/python manage.py test bands
/workspace/discipleship-venv/bin/waitress-serve --listen=127.0.0.1:8000 --threads=4 config.wsgi:application
```

Create an adult account and complete its profile. Start a band, then use separate eligible accounts to request membership and host approval. Three approved members unlock private meeting details. The directory starts empty: no fictitious bands, testimonials, activity counts, or accounts are seeded.

The ignored `.local/` directory holds the SQLite database and a generated mode-0600 signing key. Preserve this directory between restarts and back it up consistently. Never commit databases, signing keys, environment files, or credentials. Application source belongs in Git; publishing an environment snapshot is not a substitute for pushing source.

## Implemented Phase 1 workflows

- Adult registration, password validation, username login, POST logout, persistent authentication throttling, token-based password reset, and account deletion.
- Full name/email collected privately; limited display name, gender eligibility, optional country/region/city/neighborhood, language preferences, IANA time zone, life stage, meeting format, weekly availability window, introduction, optional church, and private approximate coordinates/radius.
- Time zone detection for a new profile; browser location permission only after an explicit click. Coordinates round to two decimals in the browser. Users may enter approximate coordinates manually, disable location discovery, or participate online without a location.
- Five discovery scopes; same-gender enforcement on the server. Recommendations explain language, local city, time zone, schedule, format, and life-stage matches. Country, city, area, language (including additional languages), weekday, local time range, time zone, format, life stage, church, and remaining capacity filters work without a church account.
- Band creation and host-only editing, 3–5 capacity, public approximate area, private meeting details, recruitment closure/reopening, inactive/completed lifecycle. Host counts as an approved member.
- Join introductions; pending, accepted, declined, withdrawn, and full outcomes; host-only approvals; duplicate prevention; in-app notifications.
- Transactional membership and capacity decisions. A SQLite write lock precedes capacity reads. Withdrawal uses the same band lock as acceptance. Database constraints enforce unique memberships and requests. SQLite is intended for a single instance with persistent local disk, not multiple replicas; PostgreSQL migration needs appropriate row-locking and concurrency testing.
- Forming bands remain locked until three members. Active groups remain discoverable until capacity or host closure. Full/inactive/completed groups are excluded from join results. Exact details are never serialized into directory/detail pages. Approved-member workspace authorization runs server-side on every request.
- Leaving immediately ends access and transfers host responsibility to the earliest remaining member, or deletes an empty band. Account deletion removes personal data and performs the same host handover.
- Weekly wall-clock schedules in IANA zones, shown in each member's zone. Spring-forward nonexistent occurrences are skipped; fall-back overlap uses its first occurrence.

## Validation

`manage.py test bands` runs 21 tests for identity, adult/password validation, eligibility, private-data protection, host authorization, activation, duplicate/capacity limits, withdrawal, CSRF, profile changes, international location search, creation/edit permissions, leaving/deletion, lifecycle, displayed times and DST, throttling, recovery, and page rendering. Tests create and destroy a separate database and use in-memory email for recovery verification.

Optional `node scripts/browser-smoke.cjs` requires Playwright and Chromium (`CHROMIUM_PATH` overrides `/usr/bin/chromium`). Run the local server first; `APP_URL` overrides its address. It checks mobile/desktop layouts and real registration/profile/band/deletion flows, then removes its temporary account. Screenshots go outside the checkout. No real email is sent.

## Deployment

Deploy the WSGI application behind a trusted TLS reverse proxy with durable disk. Set `DJANGO_ALLOWED_HOSTS` to real comma-separated hostnames and provide a stable secret through `DJANGO_SECRET_KEY`, or securely preserve the generated signing key. Set `DJANGO_HTTPS=1` to enable HTTPS redirect, secure cookies, and HSTS. Set `DJANGO_TRUST_PROXY=1` only if a trusted proxy strips and replaces client forwarding headers and Waitress cannot be reached directly. `DJANGO_CSRF_TRUSTED_ORIGINS` accepts comma-separated HTTPS origins if needed.

Run migrations, collectstatic, tests, and `manage.py check --deploy`. Local HTTP intentionally lacks four HTTPS settings. With `DJANGO_HTTPS=1`, only optional HSTS subdomain/preload warnings remain; configure those policies only when all relevant domains are permanently HTTPS. Debug defaults off. Authentication throttling uses the actual peer IP, not untrusted headers: behind a proxy, configure edge rate limits to avoid all users sharing one limit.

Password recovery requires actual TLS SMTP configuration: `EMAIL_HOST`, `EMAIL_PORT` (default 587), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`. Supply credentials through your deployment secret manager, never chat or Git. Optional `DJANGO_EMAIL_BACKEND` selects another Django mail backend. No SMTP service was supplied and real delivery is unverified; an unconfigured installation explicitly reports unavailable recovery. In-memory recovery tests verify token handling, not provider delivery.

## Scope and roadmap

This implements the Phase 1 core workflows, not the full four-phase platform. Country/city names support manual Unicode input and global search; a standardized geographic catalog and automatic geocoding service remain integrations. Profile-photo uploads and richer multi-window availability are not implemented. Approximate coordinates are optional and private; no precise-member maps exist.

English is the initial interface. Django locale middleware, translation markers on core navigation/headings, language configuration, Unicode storage, and direction-aware base markup establish a translation starting point. Full message extraction/catalogs, complete translation coverage, and RTL usability validation remain work. Physical devices, actual location hardware, slow-network performance, and multi-instance concurrency have not been certified.

Phases 2–4 remain planned: interactive first-meeting guide, chat/prayer/Scripture/attendance, organization roles, reporting/blocking/moderation, support queues, audit investigations, reminder emails, maps, video, and renewal/multiplication. The Help page does not promise a staffed service that does not exist. Before accepting public users, configure SMTP/TLS, verify backups and retention procedures, complete regional safeguarding/moderation operations, and conduct an independent security review. Private spiritual disclosures are not collected by this Phase 1 release.
