# Inspecting Local Data (DB & Object Storage)

How to find and view the data the local Docker stack stores — the Postgres
database and the MinIO bucket (resume files).

## Where the data lives

Both are **Docker named volumes** on the host, managed by Docker (root-owned —
not meant to be browsed as raw files). They persist across `docker compose down`
and are only wiped by `docker compose down -v`.

| Volume | Host path | Contains |
|---|---|---|
| `applypilot_pgdata` | `/var/lib/docker/volumes/applypilot_pgdata/_data` | Postgres data files |
| `applypilot_miniodata` | `/var/lib/docker/volumes/applypilot_miniodata/_data` | MinIO objects (resumes) |

Inspect a volume's mountpoint anytime:

```bash
docker volume ls | grep applypilot
docker volume inspect applypilot_pgdata -f '{{ .Mountpoint }}'
docker volume inspect applypilot_miniodata -f '{{ .Mountpoint }}'
```

You view the data through the running services, not the raw files.

## View the database

Connection details come from `docker-compose.yml`: host port **5433**
(remapped from the container's 5432 to avoid clashing with a local Postgres),
user `applypilot`, password `applypilot`, database `applypilot`.

```bash
docker compose up -d db

# Option A — from the host (requires psql installed):
psql postgresql://applypilot:applypilot@localhost:5433/applypilot

# Option B — no local psql needed, exec into the container:
docker compose exec db psql -U applypilot -d applypilot
```

Useful psql commands once connected:

```sql
\dt                          -- list tables
SELECT * FROM users;
SELECT * FROM applications;
SELECT * FROM jobs;
\d applications              -- describe a table
```

## View the MinIO bucket (resume files)

MinIO ships a web console; the S3 API is on `:9000`, the console on `:9001`.
Credentials: `minioadmin` / `minioadmin` (from `docker-compose.yml`).

```bash
docker compose up -d minio
```

- **Console UI:** open <http://localhost:9001> → log in with
  `minioadmin` / `minioadmin` → open the `applypilot` bucket.
  Resume objects are keyed `{user_id}/{uuid}-{filename}`.
- **S3 API:** `http://localhost:9000`

CLI alternative with the MinIO client (`mc`):

```bash
docker run --rm -it --network applypilot_default minio/mc \
  alias set local http://minio:9000 minioadmin minioadmin
# then:
#   mc ls local/applypilot
#   mc cp local/applypilot/<key> ./downloaded-file
```

> **Note:** the `applypilot` bucket is created lazily on the **first resume
> upload** (`StorageService.ensure_bucket`). If no resume has been uploaded yet,
> the bucket won't exist in the console.

## Stopping / resetting

```bash
docker compose down        # stop containers, KEEP data (volumes preserved)
docker compose down -v      # stop containers and DELETE all data (volumes removed)
```
