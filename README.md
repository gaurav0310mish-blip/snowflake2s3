# Snowflake → Oracle Autonomous Data Warehouse (ADW) CI/CD Template

This repository is a **reference implementation** of a CI/CD pipeline that:

1. Exports data from **Snowflake** to **OCI Object Storage**.
2. Loads that data into **Oracle Autonomous Data Warehouse (ADW)** using `DBMS_CLOUD.COPY_DATA`.
3. Automates the flow using **GitHub Actions**.

> ⚠️ This is a template – you must adjust object names, regions, OCIDs, and secrets for your tenancy and Snowflake account.

---

## 1. Architecture

Snowflake table → Snowflake Stage (OCI Object Storage) → ADW `DBMS_CLOUD` → Target tables.

High level:

```text
Snowflake
  └─ COPY INTO @oci_stage/... (Parquet/CSV)
      ↓
OCI Object Storage (Bucket: snowflake-exports)
      ↓
ADW (DBMS_CLOUD.COPY_DATA -> MYTABLE, etc.)
      ↓
GitHub Actions pipeline orchestrates export + load
```

---

## 2. Prerequisites

### Snowflake

- Snowflake account, warehouse, database, schema.
- `ACCOUNTADMIN`/sufficient privileges to:
  - Create storage integration.
  - Create stages.
  - Run `COPY INTO`.

### Oracle Cloud Infrastructure (OCI)

- OCI tenancy with:
  - **Object Storage** bucket for Snowflake exports.
  - **Autonomous Data Warehouse (ADW)** instance.
- IAM user with:
  - API signing key (for `DBMS_CLOUD.CREATE_CREDENTIAL`).
  - Access to the Object Storage bucket.

### GitHub

- A GitHub repository using this template.
- GitHub Actions enabled.
- Repo **Secrets** configured (see section 4).

---

## 3. Directory Structure

```text
.
├── README.md
├── config
│   ├── adw_cloud_config_sample.toml
│   └── env.sample
├── scripts
│   ├── export_snowflake.sh
│   └── run_ingestion.sh
├── sql
│   ├── 00_create_schema.sql
│   ├── 10_create_tables.sql
│   ├── 20_load_mytable.sql
│   └── 99_load_all.sql
└── .github
    └── workflows
        └── adw_ingest.yml
```

---

## 4. GitHub Secrets to Configure

In your GitHub repo, go to: **Settings → Secrets and variables → Actions → New repository secret** and create:

### Snowflake

- `SNOW_ACCOUNT` – e.g. `xy12345.eu-central-1`
- `SNOW_USER` – Snowflake user.
- `SNOW_PASSWORD` – Snowflake password.
- `SNOW_WAREHOUSE` – Warehouse to use for COPY.
- `SNOW_ROLE` – Role to use.
- `SNOW_DB` – Database.
- `SNOW_SCHEMA` – Schema.

### ADW / OCI

- `ADW_CONNECT_STRING` – full EZCONNECT string or TNS alias (e.g. `myadb_tp`).
- `ADW_USERNAME` – schema owner in ADW.
- `ADW_PASSWORD` – password for ADW user.
- `ADW_WALLET_BASE64` – base64-encoded contents of the ADW wallet zip (optional; if you use wallet-based connect).
- `OCI_USER_OCID` – OCID of the user whose key is used by `DBMS_CLOUD.CREATE_CREDENTIAL`.
- `OCI_KEY_FINGERPRINT` – fingerprint of the API key.
- `OCI_TENANCY_OCID` – tenancy OCID.
- `OCI_REGION` – region identifier (e.g., `eu-frankfurt-1`).
- `OCI_OBJECT_NAMESPACE` – Object Storage namespace.
- `OCI_BUCKET_NAME` – name of the object storage bucket (e.g., `snowflake-exports`).

> You may not need all of these depending on how you choose to connect (`sqlcl` vs. wallet vs. JDBC). The workflow is written to use a simple `sqlcl` connection string.

---

## 5. Snowflake Setup (Manual)

In Snowflake, run (adapt to your environment):

```sql
-- Example: create a storage integration mapped to the OCI Object Storage S3-compatible endpoint
CREATE OR REPLACE STORAGE INTEGRATION OCI_INT
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = S3
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = '<AWS_COMPATIBLE_IAM_ROLE_OR_KEY>'
  STORAGE_ALLOWED_LOCATIONS = ('s3://<bucket-name>/snowflake_exports/');

SHOW STORAGE INTEGRATIONS LIKE 'OCI_INT';

-- Create stage that points to OCI bucket via integration
CREATE OR REPLACE STAGE OCI_STAGE
  STORAGE_INTEGRATION = OCI_INT
  URL = 's3://<bucket-name>/snowflake_exports/';
```

Export a table:

```sql
COPY INTO @OCI_STAGE/mytable/
FROM mydb.public.mytable
FILE_FORMAT = (TYPE = PARQUET)
OVERWRITE = TRUE;
```

In CI/CD we’ll automate that using `snowsql` (see `scripts/export_snowflake.sh`).

---

## 6. ADW Setup (Run Once)

Connect to ADW as a privileged user (or target schema owner) and:

1. Create credential to access Object Storage:

```sql
BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'OCI_OS_CRED',
    username        => '<OCI_USER_OCID>',
    password        => '<PRIVATE_KEY_PEM_OR_PASSWORD>'
  );
END;
/
```

2. Create schema + tables (or allow CI pipeline to run `sql/00_create_schema.sql` and `sql/10_create_tables.sql`).

3. Adjust `sql/20_load_mytable.sql` with your own bucket, namespace, and object path.

---

## 7. How the CI/CD Pipeline Works

The GitHub Action (`.github/workflows/adw_ingest.yml`) performs:

1. Checkout repository.
2. Install SnowSQL and SQLcl.
3. Use `snowsql` to:
   - Run `COPY INTO @OCI_STAGE/mytable/` (export from Snowflake).
4. Use `sql` (SQLcl) to connect to ADW:
   - Run `sql/00_create_schema.sql` and `sql/10_create_tables.sql` (if needed).
   - Run `sql/99_load_all.sql` which internally calls `DBMS_CLOUD.COPY_DATA`.

You can trigger the workflow:
- on each `push` to `main` branch.
- manually from GitHub Actions tab.

---

## 8. Usage

1. **Fork/clone** this repo.
2. Update:
   - SQL files in `sql/`.
   - Bucket names, regions, object paths in `sql/20_load_mytable.sql`.
3. Create GitHub secrets as described.
4. Push to `main`.
5. Watch GitHub Actions → `ADW Ingestion Pipeline`.

---

## 9. Notes & Customization

- Add more tables:
  - Create new `sql/2x_load_<tablename>.sql` files.
  - Include them in `sql/99_load_all.sql`.
- Change file format:
  - Modify the `format` JSON in `DBMS_CLOUD.COPY_DATA` calls to use CSV instead of PARQUET.
- Scheduling:
  - Use GitHub Actions `on.schedule` (CRON) to run ingestion at regular intervals (e.g., hourly/daily).

This template is intentionally simple so you can plug it into your **Snowflake → ADW migration / sync** use cases quickly.
