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
      * updates the Cloud Run Job definition (image reference)
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
  `main` branch, and the `production` environment (section 4.5) —
  workflow YAML conditions alone are not the trust boundary.
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
  the `production` environment (section 4.5), the GitHub
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
| Workload Identity Provider | `github-actions` (inside the pool) | global | OIDC issuer `https://token.actions.githubusercontent.com`. The attribute condition pins token exchange to ALL of: repository ID `1434453178` and owner ID `7766664` (numeric, not reusable names), repository `symbi/liuyao-learning-app`, ref `refs/heads/main`, and environment `production`. Any other workflow, branch, or environment in this repository gets no credentials. |
| Cloud Run Job | `liuyao-kb-schema` | asia-southeast1 | Runs the image with the secret mount below. Default arguments `schema check` (read-only); `schema init` is passed explicitly for an authorized schema run. |
| Secret (already exists) | `neo4j-aura-credentials` | — | **Pinned to version 4** for M3 (the version verified on 2026-11-25). Changing the pin is a deliberate config change after re-verification, never a silent `latest`. |

APIs, in two groups that must not be conflated:

* **Already enabled** (verified by the user's Cloud Shell discovery,
  2026-11-25): Secret Manager (`secretmanager.googleapis.com`),
  Cloud Run (`run.googleapis.com`), Artifact Registry
  (`artifactregistry.googleapis.com`), IAM (`iam.googleapis.com`),
  Cloud Logging (`logging.googleapis.com`).
* **Additionally required for WIF service-account impersonation, NOT
  confirmed enabled**: Security Token Service
  (`sts.googleapis.com`) and IAM Service Account Credentials
  (`iamcredentials.googleapis.com`). Google's WIF impersonation
  setup requires IAM, STS, and Service Account Credentials APIs.
  Section 4.0 checks for them and enables them if missing; that
  enablement is part of the separately authorized setup, never
  assumed to have already happened.

Cloud Build is **not** used by this design and must not be enabled
for it: GitHub Actions builds the image itself.

## 3. IAM matrix (least privilege)

| Principal | Role | Scope | Why |
|---|---|---|---|
| `liuyao-kb-deployer` | `roles/artifactregistry.writer` | repository `liuyao-kb` only | push built images |
| `liuyao-kb-deployer` | `roles/run.developer` | project | create/update/execute Cloud Run Jobs (job definitions carry no secret values, only the secret's name and pinned version) |
| `liuyao-kb-deployer` | `roles/iam.serviceAccountUser` (actAs) | the `liuyao-kb-job-runtime` SA only | a job must name its runtime SA; this is the indirect-privilege path (see section 1.1), so it is scoped to that one SA |
| WIF principal set for `attribute.repository_id/1434453178` | `roles/iam.workloadIdentityUser` | the `liuyao-kb-deployer` SA | lets tokens that pass the provider's attribute condition (repo ID + owner ID + `refs/heads/main` + `production` environment, section 4.5) impersonate the deployment SA |
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
#     the two WIF impersonation APIs if they are missing. (The other
#     APIs this design needs were verified enabled on 2026-11-25.)
gcloud services list --enabled --project $PROJECT \
  --filter="name:(sts.googleapis.com OR iamcredentials.googleapis.com)"
gcloud services enable sts.googleapis.com iamcredentials.googleapis.com \
  --project $PROJECT

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
#     to the main branch, and to the production environment. GitHub
#     only issues the `environment` claim for jobs that declare an
#     environment; only the deploy job does, so every other workflow
#     or ref fails this condition and receives no credentials.
gcloud iam workload-identity-pools create github-actions \
  --project $PROJECT --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --project $PROJECT --location global \
  --workload-identity-pool github-actions \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref,attribute.environment=assertion.environment" \
  --attribute-condition "assertion.repository_id == '1434453178' && assertion.repository_owner_id == '7766664' && assertion.repository == 'symbi/liuyao-learning-app' && assertion.ref == 'refs/heads/main' && assertion.environment == 'production'"
gcloud iam service-accounts add-iam-policy-binding \
  liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com --project $PROJECT \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository_id/1434453178" \
  --role="roles/iam.workloadIdentityUser"

# 4.6 The schema Job (secret mounted as a file, version pinned to 4;
#     only LIUYAO_KB_CONFIG_DIR is set — never any NEO4J_* env vars)
gcloud run jobs create liuyao-kb-schema \
  --project $PROJECT --region $REGION \
  --image $REGION-docker.pkg.dev/$PROJECT/liuyao-kb/liuyao-kb:<git-sha> \
  --service-account liuyao-kb-job-runtime@$PROJECT.iam.gserviceaccount.com \
  --set-env-vars LIUYAO_KB_CONFIG_DIR=/secrets \
  --set-secrets /secrets/m0.env=neo4j-aura-credentials:4 \
  --args "schema,check" \
  --max-retries 0 --task-timeout 300s
```

Run an authorized schema initialization by executing the job with an
argument override (`--args "schema,init"`), then a read-only
verification execution (`--args "schema,check"`); read the sanitized
CLI output from Cloud Logging. `schema verify-vector` runs the same
way with an explicit `--dimensions` chosen for that smoke run; its
temporary index is run-scoped and self-cleaning (see
`liuyao_kb/neo4j/schema.py`).

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
  the commit SHA, updates the `liuyao-kb-schema` job's image, and
  executes it once with the job's configured (read-only) arguments.
  Running `schema init` stays a separate, deliberate execution with
  an argument override, not part of the default deploy.

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
