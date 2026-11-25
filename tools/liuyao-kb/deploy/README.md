# M3 cloud deployment design — Schema Job, Secret Manager, WIF

Status: **design and configuration only (2026-11-25).** This document
and the files under `deploy/` were delivered with the M3 code in a
Draft PR. **No GCP resource in this document has been created, no IAM
binding has been changed, and no Cloud Run Job has been deployed by
that PR.** Every numbered step below requires the user's separate,
explicit authorization before it is executed. The earlier one-time
connectivity verification (2026-11-25) used temporary resources that
have all been deleted; nothing from that test is reused here.

## 1. What runs where

```text
GitHub Actions (this repo)
  -- OIDC token --> Workload Identity Federation (pool: github-actions)
  -- short-lived credentials --> Deployment SA (liuyao-kb-deployer)
      * builds the liuyao-kb image and pushes it to Artifact Registry
      * deploys the Cloud Run Job (create or update, full configuration)
Cloud Run Job: liuyao-kb-schema (asia-southeast1)
  -- runs as --> Job Runtime SA (liuyao-kb-job-runtime)
      * Secret Manager mounts neo4j-aura-credentials (pinned version)
        as the file /secrets/m0.env
      * the container sets only LIUYAO_KB_CONFIG_DIR=/secrets
      * liuyao_kb.config.load_config() reads /secrets/m0.env
      * liuyao-kb schema init / check / verify-vector talk to AuraDB
Neo4j AuraDB instance 97d17d42 (Singapore) — the only graph database
```

Security invariants (from the M3 task book; they outrank convenience):

* The Neo4j password exists only in Secret Manager and in the Cloud
  Run runtime's mounted file. It is never in GitHub (code, Actions
  secrets, logs), never in the image, never in a local `.env` that
  gets committed, and never shown to any AI conversation.
* The Deployment identity has **no direct** Secret Manager access:
  no `secretmanager` role is granted to it, and it cannot read the
  secret's payload through the Secret Manager API. Only the Job
  Runtime identity holds `secretAccessor`, on the one secret only
  (a secret-level binding, never a project-level one). Section 1.1
  states the deployer's *indirect* capability precisely; do not read
  this bullet as complete isolation.
* No long-lived service-account JSON keys anywhere. GitHub gets
  short-lived OIDC credentials via WIF, and the provider's attribute
  condition pins the exchange to this repository's numeric IDs, the
  `main` branch, the `production` environment, the single named
  deploy workflow file, and the `workflow_dispatch` event
  (section 4.5) — workflow YAML conditions alone are not the trust
  boundary.
* The three identities (deployment / job runtime / future API
  runtime) are separate service accounts. M3 creates the first two
  only; the M7 API runtime account is **not** created by M3.
* The default Compute Engine service account is not used and is not
  modified.

### 1.1 The deployment identity's effective permission boundary

This boundary must be recorded accurately, because it is easy to
overstate:

* **Direct access: none.** The Deployment SA has no
  `roles/secretmanager.secretAccessor` (or any other secret role),
  so it cannot call the Secret Manager API to read the Neo4j
  password, and no step in the deploy path prints or copies the
  secret anywhere.
* **Indirect capability: real.** The same SA holds
  `roles/run.developer` on the project and
  `roles/iam.serviceAccountUser` (actAs) on the Job Runtime SA. That
  combination lets it create/update and execute Cloud Run Jobs that
  run *as* the Job Runtime identity — i.e., it can cause arbitrary
  code of its choosing to run with the runtime identity's
  permissions, and such code could read the mounted credentials file
  inside the job. In effective-permission terms, the Deployment
  identity can therefore reach the database credentials indirectly,
  through code it deploys.
* **What actually guards the boundary, then:** the controls on who
  can make the Deployment identity act — the WIF attribute condition
  pinned to this repository's numeric IDs + `refs/heads/main` +
  the `production` environment + the single named deploy workflow
  file + the `workflow_dispatch` event (section 4.5), the GitHub
  `production` Environment's required-reviewers approval and
  main-only deployment branches (section 4.7), and the repository's
  own write-access control. Those gates are the key safeguard; the
  separation in this design limits *direct* access and keeps the
  password out of GitHub, images and logs, but it is not a claim
  that the deployment path is incapable of touching the secret.

## 2. Resource inventory (all in project `liuyao-learning`)

| Resource | Name | Region | Notes |
|---|---|---|---|
| Artifact Registry repository | `liuyao-kb` | asia-southeast1 | Docker format. Formal repository for all Phase 1 job images (M3/M4/M5). Old images are pruned manually; no automatic cleanup policy is set by M3. |
| Container image | `asia-southeast1-docker.pkg.dev/liuyao-learning/liuyao-kb/liuyao-kb:<git-sha>` | — | Built from `tools/liuyao-kb/Dockerfile`; tagged with the commit SHA, never only `latest`. |
| Deployment service account | `liuyao-kb-deployer@liuyao-learning.iam.gserviceaccount.com` | — | GitHub Actions deployment identity (via WIF). |
| Job runtime service account | `liuyao-kb-job-runtime@liuyao-learning.iam.gserviceaccount.com` | — | Stable M3+ job runtime identity (schema job now; importer jobs later milestones may reuse it only after their own review). |
| Workload Identity Pool | `github-actions` | global | One pool for this project's GitHub Actions. |
| Workload Identity Provider | `github-actions` (inside the pool) | global | OIDC issuer `https://token.actions.githubusercontent.com`. The attribute condition pins token exchange to ALL of: repository ID `1434453178` and owner ID `7766664` (numeric, not reusable names), repository `symbi/liuyao-learning-app`, ref `refs/heads/main`, environment `production`, the single workflow file `.github/workflows/deploy-schema-job.yml` on main (`assertion.workflow_ref`), and the `workflow_dispatch` event. Any other workflow, branch, environment, or trigger in this repository gets no credentials. |
| Cloud Run Job | `liuyao-kb-schema` | asia-southeast1 | Created or updated by the deploy workflow's `gcloud run jobs deploy` step with the full configuration (section 5); there is no manual creation step. Default arguments `schema check` (read-only); `schema init` is passed explicitly for an authorized schema run. |
| Secret (already exists) | `neo4j-aura-credentials` | — | **Pinned to version 4** for M3 (the version verified on 2026-11-25). Changing the pin is a deliberate config change after re-verification, never a silent `latest`. |

APIs, in two groups that must not be conflated:

* **Already enabled** (verified by the user's Cloud Shell discovery,
  2026-11-25): Secret Manager (`secretmanager.googleapis.com`),
  Cloud Run (`run.googleapis.com`), Artifact Registry
  (`artifactregistry.googleapis.com`), IAM (`iam.googleapis.com`),
  Cloud Logging (`logging.googleapis.com`).
* **Additionally required by Google's WIF deployment guidance —
  now enabled**: Security Token Service (`sts.googleapis.com`),
  IAM Service Account Credentials (`iamcredentials.googleapis.com`),
  and Cloud Resource Manager (`cloudresourcemanager.googleapis.com`).
  Google's WIF impersonation setup requires IAM, STS, and Service
  Account Credentials APIs, and its deployment guidance also lists
  Resource Manager. The user enabled all three on 2026-11-25 and
  read back their enabled state in Cloud Shell, so in this project
  the step is complete. Section 4.0 keeps the check (and a fallback
  enable command) so a future environment can re-verify instead of
  assuming.

Cloud Build is **not** used by this design and must not be enabled
for it: GitHub Actions builds the image itself.

## 3. IAM matrix (least privilege)

| Principal | Role | Scope | Why |
|---|---|---|---|
| `liuyao-kb-deployer` | `roles/artifactregistry.writer` | repository `liuyao-kb` only | push built images |
| `liuyao-kb-deployer` | `roles/run.developer` | project | create/update/execute Cloud Run Jobs (job definitions carry no secret values, only the secret's name and pinned version). Verified against Google's role reference: this role includes `run.jobs.runWithOverrides`, so executing a job with `--args` overrides needs no additional role |
| `liuyao-kb-deployer` | `roles/iam.serviceAccountUser` (actAs) | the `liuyao-kb-job-runtime` SA only | a job must name its runtime SA; this is the indirect-privilege path (see section 1.1), so it is scoped to that one SA |
| WIF principal set for `attribute.repository_id/1434453178` | `roles/iam.workloadIdentityUser` | the `liuyao-kb-deployer` SA | lets tokens that pass the provider's attribute condition (repo ID + owner ID + `refs/heads/main` + `production` environment + the one named deploy workflow file + `workflow_dispatch` event, section 4.5) impersonate the deployment SA |
| `liuyao-kb-job-runtime` | `roles/secretmanager.secretAccessor` | secret `neo4j-aura-credentials` only | read the mounted credentials file at job runtime |

Explicitly **not** granted: any `secretmanager` role to the deployer
(its indirect capability via Job execution is a different thing and
is recorded in section 1.1, not hidden by this list); any
project-level secret access to the runtime SA; `roles/owner` or
`roles/editor` to anyone as a shortcut; any role at all to the
default Compute Engine SA (untouched); any access for pull-request
workflows (the deploy job is `workflow_dispatch`-only and restricted
to `refs/heads/main`, see section 5, and the WIF condition itself
rejects non-main, non-production tokens regardless of workflow
YAML).

## 4. Setup commands — DO NOT RUN without separate user authorization

Placeholders: `PROJECT=liuyao-learning`, `PROJECT_NUMBER=169252699444`,
`REGION=asia-southeast1`.

```bash
# 4.0 API prerequisites: verify what is actually enabled, and enable
#     the WIF-related APIs if any are missing (STS, Service Account
#     Credentials, Resource Manager — COMPLETED in this project: the
#     user enabled all three on 2026-11-25 and read back their
#     enabled state; the commands below remain as a re-check /
#     fallback for a future environment. The other APIs this design
#     needs were verified enabled on 2026-11-25).
gcloud services list --enabled --project $PROJECT \
  --format="value(config.name)" | grep -E "^(sts|iamcredentials|cloudresourcemanager)\.googleapis\.com$"
gcloud services enable sts.googleapis.com iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com --project $PROJECT

# 4.1 Artifact Registry repository
gcloud artifacts repositories create liuyao-kb \
  --repository-format=docker --location=$REGION --project $PROJECT

# 4.2 The two service accounts
gcloud iam service-accounts create liuyao-kb-deployer --project $PROJECT \
  --display-name "GitHub Actions deployment identity (Phase 1)"
gcloud iam service-accounts create liuyao-kb-job-runtime --project $PROJECT \
  --display-name "Cloud Run Job runtime identity (Phase 1)"

# 4.3 Deployer bindings (no secret access, ever)
gcloud artifacts repositories add-iam-policy-binding liuyao-kb \
  --location=$REGION --project $PROJECT \
  --member="serviceAccount:liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/run.developer"
gcloud iam service-accounts add-iam-policy-binding \
  liuyao-kb-job-runtime@$PROJECT.iam.gserviceaccount.com --project $PROJECT \
  --member="serviceAccount:liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# 4.4 Runtime binding: the one secret, secret-level only
gcloud secrets add-iam-policy-binding neo4j-aura-credentials --project $PROJECT \
  --member="serviceAccount:liuyao-kb-job-runtime@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 4.5 Workload Identity Federation for GitHub Actions.
#     The attribute condition is the trust boundary (a workflow's own
#     `if:` in YAML is not): it pins the exchange to this repository's
#     numeric IDs (repository 1434453178, owner 7766664 — IDs cannot
#     be re-registered by someone else if the names are ever reused),
#     to the main branch, to the production environment, to ONE named
#     workflow file (assertion.workflow_ref), and to the
#     workflow_dispatch event. GitHub only issues the `environment`
#     claim for jobs that declare an environment; only the deploy job
#     does. A different workflow added on main that also used the
#     production environment would still fail the workflow_ref and
#     event_name conditions, so it receives no credentials.
gcloud iam workload-identity-pools create github-actions \
  --project $PROJECT --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --project $PROJECT --location global \
  --workload-identity-pool github-actions \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref,attribute.environment=assertion.environment,attribute.workflow_ref=assertion.workflow_ref,attribute.event_name=assertion.event_name" \
  --attribute-condition "assertion.repository_id == '1434453178' && assertion.repository_owner_id == '7766664' && assertion.repository == 'symbi/liuyao-learning-app' && assertion.ref == 'refs/heads/main' && assertion.environment == 'production' && assertion.workflow_ref == 'symbi/liuyao-learning-app/.github/workflows/deploy-schema-job.yml@refs/heads/main' && assertion.event_name == 'workflow_dispatch'"
gcloud iam service-accounts add-iam-policy-binding \
  liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com --project $PROJECT \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository_id/1434453178" \
  --role="roles/iam.workloadIdentityUser"

# 4.6 The schema Job is NOT created by hand, and there is no
#     bootstrap step with a placeholder image tag. The deploy
#     workflow creates or updates it via `gcloud run jobs deploy`
#     with the full configuration — the just-built image, the job
#     runtime SA, the secret mounted as the file /secrets/m0.env
#     pinned to version 4, only LIUYAO_KB_CONFIG_DIR=/secrets set
#     (never any NEO4J_* env vars), default args "schema,check",
#     --max-retries 0, --task-timeout 300s — because the image is
#     built and pushed first, it always exists by deploy time
#     (section 5).
```

Manual executions, when separately authorized, are run by the user
from Cloud Shell **under the user's own Google identity** — not the
GitHub Actions deployment identity; the two are authorized and
audited separately. Always pass `--wait`, so the command returns
only when the execution has finished, and read the sanitized CLI
output from Cloud Logging. Set the variables first in every new
Cloud Shell session (the placeholders in the section 4 preamble are
prose, not shell state):

```bash
PROJECT=liuyao-learning
REGION=asia-southeast1

# 1. Schema initialization (write; needs its own authorization)
gcloud run jobs execute liuyao-kb-schema --project $PROJECT --region $REGION \
  --args "schema,init" --wait
# 2. Read-only verification (expected to exit 0 after step 1)
gcloud run jobs execute liuyao-kb-schema --project $PROJECT --region $REGION \
  --args "schema,check" --wait
# 3. Optional vector smoke (explicit dimension for this run only)
gcloud run jobs execute liuyao-kb-schema --project $PROJECT --region $REGION \
  --args "schema,verify-vector,--dimensions,128" --wait
```

`schema verify-vector`'s temporary index is run-scoped and
self-cleaning (see `liuyao_kb/neo4j/schema.py`). Never add `--wait`
to `gcloud run jobs deploy` itself: there it implies
`--execute-now` and would run the job inside the deploy step.

### 4.7 GitHub-side prerequisite: the `production` Environment

A repository setting, done by the user in the GitHub web interface
(Settings → Environments); it is part of the trust boundary in
section 1.1, not an optional convenience:

* Create the environment named exactly `production`.
* **Required reviewers**: the user (so every deploy run waits for a
  human approval before the deploy job starts).
* **Deployment branches**: restrict to `main` only.

Without this environment the workflow's `environment: production`
reference fails, and without the WIF condition in 4.5 requiring the
`production` environment claim, an approval here would be the only
gate — the design requires both.

### 4.8 Read-only verification commands (Phase 0)

Run by the user in Cloud Shell. All of these are read-only; the
Secret commands return metadata and IAM bindings only, never
payload content. Set the variables first in every new Cloud Shell
session (the placeholders in the section 4 preamble are prose, not
shell state):

```bash
PROJECT=liuyao-learning
PROJECT_NUMBER=169252699444
REGION=asia-southeast1
```

**Phase 0A — pre-deployment baseline.** Only what should already
exist, plus existence lists for everything else. Run this before
any setup phase:

```bash
# Project and APIs (all enabled services, one per line)
gcloud config get-value project
gcloud services list --enabled --project $PROJECT --format="value(config.name)"

# Existence lists: repositories, service accounts, WIF pools, jobs
# (empty results are the expected baseline, not an error)
gcloud artifacts repositories list --location=$REGION --project $PROJECT
gcloud iam service-accounts list --project $PROJECT
gcloud iam workload-identity-pools list --location=global --project $PROJECT
gcloud run jobs list --region=$REGION --project $PROJECT

# Secret metadata and bindings (no payload access)
gcloud secrets versions list neo4j-aura-credentials --project $PROJECT
gcloud secrets get-iam-policy neo4j-aura-credentials --project $PROJECT

# Project-level bindings
gcloud projects get-iam-policy $PROJECT
```

**Phase 0B — post-creation readback.** Run each command after its
resource has been created, to read back the bindings and
configuration actually in effect. Before creation these commands
return NOT FOUND by design — that is expected, not a failure:

```bash
gcloud artifacts repositories get-iam-policy liuyao-kb \
  --location=$REGION --project $PROJECT
gcloud iam service-accounts get-iam-policy \
  liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com --project $PROJECT
gcloud iam service-accounts get-iam-policy \
  liuyao-kb-job-runtime@$PROJECT.iam.gserviceaccount.com --project $PROJECT
gcloud iam workload-identity-pools providers describe github-actions \
  --location=global --workload-identity-pool=github-actions --project $PROJECT
gcloud run jobs describe liuyao-kb-schema --region=$REGION --project $PROJECT
```

The provider `describe` output is the readback for section 4.5:
check its attribute mapping and attribute condition against the
seven pinned conditions before trusting the first deploy.

## 5. GitHub Actions workflow

`deploy/github-actions/deploy-schema-job.yml` in this repo is the
workflow source. It must be placed at
`.github/workflows/deploy-schema-job.yml` **through the GitHub web
interface by the user**: Muse's GitHub connector cannot push
`.github/workflows/` files (missing `workflow` scope), so the file is
delivered here, ready to copy, instead of pretending it is active.

Workflow behavior:

* `test` job — on pull requests and manual dispatch: pytest, Ruff,
  Mypy. It has **no** GCP credentials and cannot deploy anything.
* `deploy` job — `workflow_dispatch` only, only on `refs/heads/main`,
  behind the `production` GitHub Environment (which must be
  configured with required reviewers and main-only deployment
  branches, section 4.7): authenticates via WIF as
  `liuyao-kb-deployer`, builds and pushes the image tagged with
  the commit SHA, then deploys the `liuyao-kb-schema` Job with
  `gcloud run jobs deploy` — creating it on the first run and
  updating it afterwards, always with the full configuration of
  section 4.6 (no `--wait` on the deploy step: there it would imply
  `--execute-now`) — and finally executes it once with
  `--args "schema,check" --wait`. Because `--set-env-vars` and
  `--set-secrets` are replace-style, this Job's environment-variable
  and secret configuration is fully managed by this workflow; manual
  edits to it are overwritten by the next deploy. Running
  `schema init` stays a separate, deliberate execution with an
  argument override, not part of the default deploy.

**First-run expectation (read before the first deploy):** the
workflow's built-in execution runs `schema check`. Against the
current AuraDB instance, where `schema init` has never run, all
five unique constraints are missing, and the CLI exits non-zero
for an incomplete schema — so on the first deploy run the final
execution step is *expected to fail*, even though the image
build/push and the Job deploy (which creates the Job on that run)
before it succeeded. That specific failure is the pre-init state
reporting itself, not a deployment fault. The authorized order
is: (1) deploy the Job via the workflow, (2) execute it once with
`--args "schema,init"` under the separate cloud-execution
authorization, (3) execute `schema check` again — only then is a
zero exit expected — and (4) optionally run
`schema verify-vector` with an explicit dimension.

## 6. Costs

Expected near zero at M3 scale, not guaranteed free: Artifact
Registry storage beyond the 0.5 GB free tier is billed per GB-month
(the image is a few hundred MB); Cloud Run Job executions bill
per vCPU/memory-second with a monthly free tier (a schema run takes
seconds); WIF and service accounts are free; Secret Manager access
operations are billed per 10k operations (negligible here). The
project has billing enabled; a budget alert is recommended but is a
separate user action in the Billing console.

## 7. Rollback / cleanup (only the resources of section 2)

```bash
gcloud run jobs delete liuyao-kb-schema --project $PROJECT --region $REGION
gcloud artifacts repositories delete liuyao-kb --location=$REGION --project $PROJECT
gcloud secrets remove-iam-policy-binding neo4j-aura-credentials --project $PROJECT \
  --member="serviceAccount:liuyao-kb-job-runtime@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud iam service-accounts delete liuyao-kb-job-runtime@$PROJECT.iam.gserviceaccount.com --project $PROJECT
gcloud iam service-accounts delete liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com --project $PROJECT
gcloud iam workload-identity-pools providers delete github-actions \
  --project $PROJECT --location global --workload-identity-pool github-actions
gcloud iam workload-identity-pools delete github-actions --project $PROJECT --location global
```

Never deleted by this design: the secret `neo4j-aura-credentials`
itself or any of its versions, and the AuraDB instance.
