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
* The Deployment identity has **no** Secret Manager access. Only the
  Job Runtime identity can read the one secret, and only that secret
  (a secret-level binding, never a project-level one).
* No long-lived service-account JSON keys anywhere. GitHub gets
  short-lived OIDC credentials via WIF, restricted to this repository.
* The three identities (deployment / job runtime / future API
  runtime) are separate service accounts. M3 creates the first two
  only; the M7 API runtime account is **not** created by M3.
* The default Compute Engine service account is not used and is not
  modified.

## 2. Resource inventory (all in project `liuyao-learning`)

| Resource | Name | Region | Notes |
|---|---|---|---|
| Artifact Registry repository | `liuyao-kb` | asia-southeast1 | Docker format. Formal repository for all Phase 1 job images (M3/M4/M5). Old images are pruned manually; no automatic cleanup policy is set by M3. |
| Container image | `asia-southeast1-docker.pkg.dev/liuyao-learning/liuyao-kb/liuyao-kb:<git-sha>` | — | Built from `tools/liuyao-kb/Dockerfile`; tagged with the commit SHA, never only `latest`. |
| Deployment service account | `liuyao-kb-deployer@liuyao-learning.iam.gserviceaccount.com` | — | GitHub Actions deployment identity (via WIF). |
| Job runtime service account | `liuyao-kb-job-runtime@liuyao-learning.iam.gserviceaccount.com` | — | Stable M3+ job runtime identity (schema job now; importer jobs later milestones may reuse it only after their own review). |
| Workload Identity Pool | `github-actions` | global | One pool for this project's GitHub Actions. |
| Workload Identity Provider | `github-actions` (inside the pool) | global | OIDC issuer `https://token.actions.githubusercontent.com`; attribute condition restricts tokens to `repo:symbi/liuyao-learning-app`. |
| Cloud Run Job | `liuyao-kb-schema` | asia-southeast1 | Runs the image with the secret mount below. Default arguments `schema check` (read-only); `schema init` is passed explicitly for an authorized schema run. |
| Secret (already exists) | `neo4j-aura-credentials` | — | **Pinned to version 4** for M3 (the version verified on 2026-11-25). Changing the pin is a deliberate config change after re-verification, never a silent `latest`. |

APIs required (all already enabled as of 2026-11-25, per the user's
Cloud Shell discovery): Secret Manager, Cloud Run, Artifact Registry,
IAM, Cloud Logging. Cloud Build is **not** used by this design and
must not be enabled for it: GitHub Actions builds the image itself.

## 3. IAM matrix (least privilege)

| Principal | Role | Scope | Why |
|---|---|---|---|
| `liuyao-kb-deployer` | `roles/artifactregistry.writer` | repository `liuyao-kb` only | push built images |
| `liuyao-kb-deployer` | `roles/run.developer` | project | create/update/execute Cloud Run Jobs (job definitions carry no secret values, only the secret's name and pinned version) |
| `liuyao-kb-deployer` | `roles/iam.serviceAccountUser` (actAs) | the `liuyao-kb-job-runtime` SA only | a job must name its runtime SA; this is the indirect-privilege path, so it is scoped to that one SA |
| WIF principal set for `attribute.repository/symbi/liuyao-learning-app` | `roles/iam.workloadIdentityUser` | the `liuyao-kb-deployer` SA | lets this repo's Actions workflows impersonate the deployment SA |
| `liuyao-kb-job-runtime` | `roles/secretmanager.secretAccessor` | secret `neo4j-aura-credentials` only | read the mounted credentials file at job runtime |

Explicitly **not** granted: any `secretmanager` role to the deployer;
any project-level secret access to the runtime SA; `roles/owner` or
`roles/editor` to anyone as a shortcut; any role at all to the
default Compute Engine SA (untouched); any access for pull-request
workflows (the deploy job is `workflow_dispatch`-only and restricted
to `refs/heads/main`, see section 5).

## 4. Setup commands — DO NOT RUN without separate user authorization

Placeholders: `PROJECT=liuyao-learning`, `PROJECT_NUMBER=169252699444`,
`REGION=asia-southeast1`.

```bash
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

# 4.5 Workload Identity Federation for GitHub Actions
gcloud iam workload-identity-pools create github-actions \
  --project $PROJECT --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --project $PROJECT --location global \
  --workload-identity-pool github-actions \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition "assertion.repository == 'symbi/liuyao-learning-app'"
gcloud iam service-accounts add-iam-policy-binding \
  liuyao-kb-deployer@$PROJECT.iam.gserviceaccount.com --project $PROJECT \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository/symbi/liuyao-learning-app" \
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
  behind the `production` GitHub Environment: authenticates via WIF
  as `liuyao-kb-deployer`, builds and pushes the image tagged with
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
