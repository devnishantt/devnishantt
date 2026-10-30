<p align="center">
  <img src="assets/hero.svg" width="100%" alt="Nishant, backend engineer in TypeScript, Node.js and Python. A terminal types whoami, lists my featured projects and shows how many CI pipelines are green.">
</p>

<p align="center">
  <b>I build backends that are hard to get wrong.</b><br>
  Money that never touches floating point, approvals that need a second person, audit trails you can verify,<br>
  and CI that typechecks, tests and builds on every push.
</p>

<p align="center">
  <a href="#call"><code>call the api</code></a> &nbsp;·&nbsp;
  <a href="#work"><code>projects</code></a> &nbsp;·&nbsp;
  <a href="#ci"><code>pipelines</code></a> &nbsp;·&nbsp;
  <a href="#vitals"><code>vital signs</code></a> &nbsp;·&nbsp;
  <a href="#rules"><code>how i build</code></a> &nbsp;·&nbsp;
  <a href="#tools"><code>toolbox</code></a>
</p>

<p align="center"><img src="assets/divider.svg" width="100%" alt=""></p>

<a id="call"></a>
<p align="center"><img src="assets/h-api.svg" width="100%" alt="0x01 this profile is an api: call it from the issues tab"></p>

This README is served by a backend. **Open an issue whose title is an HTTP request** and a GitHub Action answers it
with an HTTP-style response (status line, headers, JSON body) in about 10 to 20 seconds. It then closes the issue,
writes your call into the access log below, and replaces the trace further down with a span-by-span waterfall of
*your* request. No server and no keys: the transport is GitHub Issues.

<table>
  <tr>
    <th align="left">Click one, then press <i>Create</i></th>
    <th align="left">What comes back</th>
  </tr>
  <tr><td><a href="https://github.com/devnishantt/devnishantt/issues/new?title=GET%20/about&body=Just%20press%20%2A%2ACreate%2A%2A%20%E2%80%94%20this%20issue%20is%20an%20HTTP%20request.%20A%20GitHub%20Action%20answers%20it%20in%20about%2020%20seconds%2C%20closes%20it%2C%20and%20adds%20you%20to%20the%20access%20log%20on%20my%20profile.%0A%0AChange%20the%20title%20to%20call%20any%20route%3A%20GET%20/%2C%20GET%20/about%2C%20GET%20/projects%2C%20GET%20/projects/%7Bname%7D%2C%20GET%20/ci%2C%20GET%20/stack%2C%20GET%20/now%2C%20OPTIONS%20/%2C%20BREW%20/coffee"><code>GET&nbsp;/about</code></a></td><td>Who I am, as JSON</td></tr>
  <tr><td><a href="https://github.com/devnishantt/devnishantt/issues/new?title=GET%20/projects&body=Just%20press%20%2A%2ACreate%2A%2A%20%E2%80%94%20this%20issue%20is%20an%20HTTP%20request.%20A%20GitHub%20Action%20answers%20it%20in%20about%2020%20seconds%2C%20closes%20it%2C%20and%20adds%20you%20to%20the%20access%20log%20on%20my%20profile.%0A%0AChange%20the%20title%20to%20call%20any%20route%3A%20GET%20/%2C%20GET%20/about%2C%20GET%20/projects%2C%20GET%20/projects/%7Bname%7D%2C%20GET%20/ci%2C%20GET%20/stack%2C%20GET%20/now%2C%20OPTIONS%20/%2C%20BREW%20/coffee"><code>GET&nbsp;/projects</code></a></td><td>Everything I'm building</td></tr>
  <tr><td><a href="https://github.com/devnishantt/devnishantt/issues/new?title=GET%20/projects/ledgerline&body=Just%20press%20%2A%2ACreate%2A%2A%20%E2%80%94%20this%20issue%20is%20an%20HTTP%20request.%20A%20GitHub%20Action%20answers%20it%20in%20about%2020%20seconds%2C%20closes%20it%2C%20and%20adds%20you%20to%20the%20access%20log%20on%20my%20profile.%0A%0AChange%20the%20title%20to%20call%20any%20route%3A%20GET%20/%2C%20GET%20/about%2C%20GET%20/projects%2C%20GET%20/projects/%7Bname%7D%2C%20GET%20/ci%2C%20GET%20/stack%2C%20GET%20/now%2C%20OPTIONS%20/%2C%20BREW%20/coffee"><code>GET&nbsp;/projects/ledgerline</code></a></td><td>One project: the hard part, the stack and its <b>live</b> CI status</td></tr>
  <tr><td><a href="https://github.com/devnishantt/devnishantt/issues/new?title=GET%20/ci&body=Just%20press%20%2A%2ACreate%2A%2A%20%E2%80%94%20this%20issue%20is%20an%20HTTP%20request.%20A%20GitHub%20Action%20answers%20it%20in%20about%2020%20seconds%2C%20closes%20it%2C%20and%20adds%20you%20to%20the%20access%20log%20on%20my%20profile.%0A%0AChange%20the%20title%20to%20call%20any%20route%3A%20GET%20/%2C%20GET%20/about%2C%20GET%20/projects%2C%20GET%20/projects/%7Bname%7D%2C%20GET%20/ci%2C%20GET%20/stack%2C%20GET%20/now%2C%20OPTIONS%20/%2C%20BREW%20/coffee"><code>GET&nbsp;/ci</code></a></td><td>Every pipeline, read live from GitHub Actions</td></tr>
  <tr><td><a href="https://github.com/devnishantt/devnishantt/issues/new?title=GET%20/now&body=Just%20press%20%2A%2ACreate%2A%2A%20%E2%80%94%20this%20issue%20is%20an%20HTTP%20request.%20A%20GitHub%20Action%20answers%20it%20in%20about%2020%20seconds%2C%20closes%20it%2C%20and%20adds%20you%20to%20the%20access%20log%20on%20my%20profile.%0A%0AChange%20the%20title%20to%20call%20any%20route%3A%20GET%20/%2C%20GET%20/about%2C%20GET%20/projects%2C%20GET%20/projects/%7Bname%7D%2C%20GET%20/ci%2C%20GET%20/stack%2C%20GET%20/now%2C%20OPTIONS%20/%2C%20BREW%20/coffee"><code>GET&nbsp;/now</code></a></td><td>Streak and contributions, computed when you ask</td></tr>
  <tr><td><a href="https://github.com/devnishantt/devnishantt/issues/new?title=DELETE%20/&body=Just%20press%20%2A%2ACreate%2A%2A%20%E2%80%94%20this%20issue%20is%20an%20HTTP%20request.%20A%20GitHub%20Action%20answers%20it%20in%20about%2020%20seconds%2C%20closes%20it%2C%20and%20adds%20you%20to%20the%20access%20log%20on%20my%20profile.%0A%0AChange%20the%20title%20to%20call%20any%20route%3A%20GET%20/%2C%20GET%20/about%2C%20GET%20/projects%2C%20GET%20/projects/%7Bname%7D%2C%20GET%20/ci%2C%20GET%20/stack%2C%20GET%20/now%2C%20OPTIONS%20/%2C%20BREW%20/coffee"><code>DELETE&nbsp;/</code></a></td><td><code>403</code>. This profile is append-only, like a good audit log</td></tr>
  <tr><td><a href="https://github.com/devnishantt/devnishantt/issues/new?title=BREW%20/coffee&body=Just%20press%20%2A%2ACreate%2A%2A%20%E2%80%94%20this%20issue%20is%20an%20HTTP%20request.%20A%20GitHub%20Action%20answers%20it%20in%20about%2020%20seconds%2C%20closes%20it%2C%20and%20adds%20you%20to%20the%20access%20log%20on%20my%20profile.%0A%0AChange%20the%20title%20to%20call%20any%20route%3A%20GET%20/%2C%20GET%20/about%2C%20GET%20/projects%2C%20GET%20/projects/%7Bname%7D%2C%20GET%20/ci%2C%20GET%20/stack%2C%20GET%20/now%2C%20OPTIONS%20/%2C%20BREW%20/coffee"><code>BREW&nbsp;/coffee</code></a></td><td>See RFC 2324</td></tr>
</table>

<p align="center">
  <img src="assets/access-log.svg" width="100%" alt="Access log: the most recent requests made to this profile API, with caller, method, path, status code and how long the reply took.">
</p>

<p align="center">
  <img src="assets/trace.svg" width="100%" alt="Distributed trace of the most recent API request: issue event, Actions queue time, runner steps, the Python handler, each GitHub API call, and the commit that published this image.">
</p>

<p align="center"><sub>The trace is real. Queue time and runner steps are read back from the Actions API; the handler and every GitHub API call are timed in-process. The striped span is still running when the image is committed, because that commit is what publishes it.</sub></p>

<details>
<summary><b>How it works</b></summary>
<br>

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant I as GitHub Issues
    participant A as GitHub Actions
    participant R as profile_api.py
    participant G as GitHub API
    You->>I: open issue "GET /projects/ledgerline"
    I-->>A: issues.opened
    A->>R: run with the event payload
    R->>R: parse request line, match fixed route table
    R->>G: latest CI run for the repo
    G-->>R: status, commit, duration
    R->>I: comment with HTTP/1.1 200 OK + JSON, close issue
    R->>G: read this job's own step timings
    R->>A: commit access log + trace waterfall
    A-->>You: your request shows up on this README
```

- The issue title is untrusted input. It is read from the event payload (never interpolated into a shell), matched against a fixed route table, and only echoed back inside code fences.
- Concurrent requests never clobber each other: every log write re-reads `main`, appends, and retries the push.
- Unknown routes get `404`, malformed titles get `400`, and writes get `403` or `405`, with the reason in the body.
- Source: [`scripts/profile_api.py`](scripts/profile_api.py) · workflow: [`.github/workflows/profile-api.yml`](.github/workflows/profile-api.yml). Standard library only.

</details>

<p align="center"><img src="assets/divider.svg" width="100%" alt=""></p>

<a id="work"></a>
<p align="center"><img src="assets/h-work.svg" width="100%" alt="0x02 what i'm building: six backends, each with one hard problem"></p>

<table>
  <tr>
    <td width="50%"><a href="https://github.com/devnishantt/ledgerline"><img src="assets/card-ledgerline.svg" width="100%" alt="Ledgerline: financial reconciliation workspace built with React, Hono, Cloudflare D1 and Zod."></a></td>
    <td width="50%"><a href="https://github.com/devnishantt/aftermark"><img src="assets/card-aftermark.svg" width="100%" alt="Aftermark: evidence-driven incident response API built with Fastify, Bun, Zod and Cloudflare D1."></a></td>
  </tr>
  <tr>
    <td width="50%"><a href="https://github.com/devnishantt/Pactrail"><img src="assets/card-pactrail.svg" width="100%" alt="Pactrail: API contract checks, OpenAPI breaking-change detection and deterministic fixtures in TypeScript."></a></td>
    <td width="50%"><a href="https://github.com/devnishantt/tracebench"><img src="assets/card-tracebench.svg" width="100%" alt="Tracebench: local-first dataset contracts, profiling and drift reports in Python with DuckDB and Pydantic."></a></td>
  </tr>
  <tr>
    <td width="50%"><a href="https://github.com/devnishantt/bank-management-system"><img src="assets/card-bank.svg" width="100%" alt="bank-management-system: banking REST API with a double-entry ledger, row-locked transfers and idempotency keys."></a></td>
    <td width="50%"><a href="https://github.com/devnishantt/Hospital-Management"><img src="assets/card-hospital.svg" width="100%" alt="Hospital-Management: hospital management API with JWT rotation, a Redis token blacklist and rate limiting."></a></td>
  </tr>
</table>

<details>
<summary><b>The hard part of each one</b></summary>
<br>

| Project | The hard part |
|---|---|
| [**Ledgerline**](https://github.com/devnishantt/ledgerline) | Integer minor-unit money, one-to-one matching that leaves ambiguous pairs unresolved instead of guessing, a separate reviewer credential for approvals, and a hash-linked audit chain that detects a missing tail. |
| [**Aftermark**](https://github.com/devnishantt/aftermark) | An incident only closes after two non-creator principals approve the *current* SHA-256 evidence manifest. New evidence makes old approvals stale. Every write claims the next revision, so conflicting writers roll back their whole batch. |
| [**Pactrail**](https://github.com/devnishantt/Pactrail) | A deliberately conservative OpenAPI diff: anything it can't prove safe is flagged for review and blocks CI. Backed by 639 tests, most of them schema boundary cases. |
| [**Tracebench**](https://github.com/devnishantt/tracebench) | Drift checks that report "incomparable" instead of quietly saying "stable". Bounded CSV/JSONL/Parquet ingestion, exact decimal bounds and fingerprinted, offline HTML reports. |
| [**bank-management-system**](https://github.com/devnishantt/bank-management-system) | A double-entry ledger you can check against the balances, transfers that lock rows in a fixed order so they can't deadlock, and `Idempotency-Key` retries that never double-charge. |
| [**Hospital-Management**](https://github.com/devnishantt/Hospital-Management) | Access and refresh token rotation, a Redis-backed token blacklist, rate limiting, uploads and email in a layered Express service. |

</details>

<p align="center"><img src="assets/divider.svg" width="100%" alt=""></p>

<a id="ci"></a>
<p align="center"><img src="assets/h-ci.svg" width="100%" alt="0x03 pipelines: latest main-branch run, every repo"></p>

<p align="center">
  <img src="assets/pipeline.svg" width="100%" alt="The latest main-branch GitHub Actions run for each featured project, with its steps, duration and result.">
</p>

<p align="center"><sub>Read straight from the GitHub Actions API every day. If a pipeline goes red, this board goes red with it.</sub></p>

<p align="center"><img src="assets/divider.svg" width="100%" alt=""></p>

<a id="vitals"></a>
<p align="center"><img src="assets/h-vitals.svg" width="100%" alt="0x04 vital signs: contributions as a monitor trace"></p>

<p align="center">
  <img src="assets/heartbeat.svg" width="100%" alt="My daily contributions over the last four weeks drawn as an ECG trace, with the 7-day total, current streak and busiest day.">
</p>

<p align="center"><img src="assets/divider.svg" width="100%" alt=""></p>

<a id="rules"></a>
<p align="center"><img src="assets/h-rules.svg" width="100%" alt="0x05 how i build: invariants over features"></p>

<p align="center">
  <img src="assets/principles.svg" width="100%" alt="How I build, rendered as a passing test run: money as integer minor units, revision claims for concurrency, approvals by someone other than the author, append-only hash-linked history, uncertainty reported instead of guessed, and CI on every push. Each line names the repositories that enforce it.">
</p>

<p align="center"><img src="assets/divider.svg" width="100%" alt=""></p>

<a id="tools"></a>
<p align="center"><img src="assets/h-tools.svg" width="100%" alt="0x06 toolbox: what the above is made of"></p>

<p align="center">
  <img src="assets/stack.svg" width="100%" alt="Tools I use: TypeScript, JavaScript, Node.js, Python, Express, Fastify, Hono, Bun, React, Zod, Prisma, PostgreSQL, Redis, Cloudflare, DuckDB, Pydantic, Vitest, Pytest, Docker, GitHub Actions, MySQL, MongoDB, Git and GitHub, plus the language split of my public repositories.">
</p>

<p align="center">
  <img src="assets/footer.svg" width="100%" alt="exit 0. Thanks for stopping by.">
</p>

<p align="center"><sub>Nothing on this page is a third-party widget. Every graphic is a self-contained SVG rebuilt daily from the GitHub API by <a href="scripts/build_profile.py"><code>scripts/build_profile.py</code></a>, and the API above is <a href="scripts/profile_api.py"><code>scripts/profile_api.py</code></a>. Standard library only · icons from <a href="https://simpleicons.org">Simple Icons</a> (CC0)</sub></p>
