# Deployment Guide — Databricks App

Deploy the PO Processing Dash app as a [Databricks App](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html),
backed by a Unity Catalog Volume for storage and AWS GovCloud Bedrock for inference.

## Prerequisites

- A Databricks workspace with the **Apps** feature enabled.
- A **Unity Catalog Volume** (`/Volumes/<catalog>/<schema>/<volume>`) that the
  app's service principal can read and write.
- **AWS GovCloud Bedrock access**:
  - Network egress from the Databricks workspace to the GovCloud Bedrock
    endpoint (and FIPS endpoints where required).
  - IAM credentials (or a role) with `bedrock:InvokeModel` on the configured
    Claude Sonnet and Haiku model ids, stored as Databricks secrets.
  - Model access granted for those Claude models in the GovCloud account.

> **Validate Bedrock connectivity first.** Before deploying the app, run the
> smoke test (below) from a notebook on the same cluster to isolate
> network/IAM issues from the Dash layer.

## 1. Seed the Volume

Copy the shipped seed data into the Volume once:

```
exemplary_data/   ->  /Volumes/<catalog>/<schema>/<volume>/exemplary_data/
data/             ->  /Volumes/<catalog>/<schema>/<volume>/data/
```

(You can do this from a notebook with `dbutils.fs.cp(..., recurse=True)` or the
Volumes UI.)

## 2. Configure `app.yaml`

Edit [`../app.yaml`](../app.yaml):

- Set `VOLUME_BASE` to your Volume path.
- Set `AWS_REGION` (e.g. `us-gov-west-1`).
- Point `BEDROCK_SONNET_MODEL_ID`, `BEDROCK_HAIKU_MODEL_ID`,
  `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` at Databricks secrets
  (`valueFrom`).

## 3. Deploy

Use the Databricks CLI or the Apps UI to deploy the repository as an app. The
entrypoint is `python app.py`, which binds `0.0.0.0` on the injected
`DATABRICKS_APP_PORT`. The Flask handle (`server = app.server`) is also available
for a custom gunicorn command if preferred.

## Bedrock smoke test (run in a notebook first)

```python
import os
os.environ["AWS_REGION"] = "us-gov-west-1"
os.environ["BEDROCK_SONNET_MODEL_ID"] = "<sonnet-model-id>"
os.environ["BEDROCK_HAIKU_MODEL_ID"] = "<haiku-model-id>"

from po_processing.core.llm_client import GenerativeModel

print(GenerativeModel(role="fast").generate_content("Reply with the word OK").text)
print(GenerativeModel(role="heavy").generate_content("Reply with the word OK").text)
```

If both print `OK`, credentials, region, endpoint, and model access are working.

## Notes

- The app is single-instance; writes to shared files (e.g. `rule_base.json`)
  are not locked.
- Large PDFs (above `BEDROCK_MAX_PDF_BYTES`) automatically fall back to
  deterministic `pdfplumber` extraction instead of Bedrock document input.
