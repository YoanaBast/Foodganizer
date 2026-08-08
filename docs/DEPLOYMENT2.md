# Foodganizer - Render Deployment Documentation

## Architecture Changes from AWS

### No `docker-compose.yml` on Render
Ignored by Render, but I didn't remove it. Just letting it be ignored. `render.yaml` is the new blueprint. 

### Switched static file serving from nginx to Whitenoise
On AWS, nginx terminated HTTPS (via Certbot), reverse-proxied requests to gunicorn, and served static files directly from disk. 

Render terminates TLS automatically (managed certificates, auto-renewed, no Certbot) and proxies requests straight to the container. 

Static handled by Whitenoise now.

### Removed Redis / Celery worker / Celery beat as always-on services
This is a cost/complexity tradeoff rather than a hard technical requirement. On Render's free tier, each service draws from the account's monthly free-hours pool separately. 

cleanup_expired_sessions.py now wraps the existing Celery task so it can run as a plain Django management command via Render's Cron Job, instead of requiring a permanent Celery worker + beat process.


---

## Project Setup
```bash
git clone https://github.com/YoanaBast/Foodganizer.git
cd Foodganizer
```

## `start.sh` — Container Startup Script
Created to avoid quoting/escaping issues with Render's "Docker Command" dashboard field:
```bash
#!/bin/sh
set -e
python manage.py migrate
python manage.py collectstatic --noinput
exec gunicorn meals_manager.wsgi:application --bind 0.0.0.0:$PORT --workers 1
```

## Dockerfile Additions
Normalizes line endings and marks the script executable at build time, regardless of how it was edited/saved locally:
```dockerfile
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh
```



## Errors Encountered & Fixes

### Error 1 — `Application exited early` (silent, no logs)
**Symptom:** Build succeeded, deploy started, then exited with zero output.

**Root cause:** The web service's **Docker Command field in the Render dashboard was empty**, so it spinned up a container with no command and no Dockerfile `CMD` that had nothing to run.

**Fix:** Set the Docker Command explicitly in Settings, and add `PYTHONUNBUFFERED=1` so Python output isn't buffered/lost before a crash.

### Error 2 — `sh: 1: ...: not found` (exit 127)
**Symptom:** After setting the Docker Command as an inline multi-command string with quotes:
```
sh -c "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn ..."
```
Render's dashboard field mishandled the quoting, so `sh` tried to execute the entire string as a single command name.
**Fix:** Moved the startup logic into `start.sh` and set the Docker Command to just `./start.sh` — no quotes or chaining.

### Error 3 — `Exited with status 128` (still silent)
**Symptom:** `./start.sh` produced no output and failed immediately.

**Root cause:** The script was created via GitHub's web file editor and likely had CRLF line endings, breaking the `#!/bin/sh` shebang; the Dockerfile also didn't `chmod +x` the script.

**Fix:** Added `RUN sed -i 's/\r$//' start.sh && chmod +x start.sh` to the Dockerfile to normalize line endings and set exec permissions at build time, regardless of how the file was edited.

### Error 4 — `SyntaxError: ':' expected after dictionary key` (×3 occurrences)
**Symptom:** Django crashed on import with a syntax error partway through `settings.py`.

**Root cause:** I was tired and frustrated from multiple failed deployments and kept misplacing things in the settings file. 

**Fix:** Found and fixed the errors, I had placed the string "settings" at random places. 

### Error 5 — `whitenoise.storage.MissingFileError`
**Symptom:**
```
The JS file 'vendor/bootstrap/js/bootstrap.bundle.min.js' references a file which could not be found:
  vendor/bootstrap/js/bootstrap.bundle.min.js.map
```
**Root cause:** `CompressedManifestStaticFilesStorage` fails `collectstatic` if any referenced asset (like a source map) is missing. The missing file ships bundled with `django-jazzmin`, not this repo, so it can't be added directly.

**Fix:** Switched to `whitenoise.storage.CompressedStaticFilesStorage` — still compresses static files, just skips the reference-scanning step. Tradeoff: no cache-busted filenames, fine for this project's size.


---

## DNS Records (Cloudflare)
Tweaked as shown in Render prompt, removed the old elastic IPs for AWS. This is for the custom domain. 
