#!/bin/bash
# Repeatedly runs ingest.py until it succeeds. The free-tier Gemini embedding
# quota has been observed staying exhausted for much longer than its documented
# per-minute window, so this just keeps trying with a cooldown between attempts.
# Safe to interrupt or rerun any time - ingest.py checkpoints progress per batch.

MAX_ATTEMPTS=200
COOLDOWN_SECONDS=300

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    echo "=== Attempt $attempt/$MAX_ATTEMPTS: $(date) ==="
    python ingest.py
    status=$?

    if [ $status -eq 0 ]; then
        echo "=== ingest.py finished successfully on attempt $attempt ==="
        exit 0
    fi

    echo "=== Attempt $attempt failed (exit $status), waiting ${COOLDOWN_SECONDS}s before retry ==="
    attempt=$((attempt + 1))
    sleep "$COOLDOWN_SECONDS"
done

echo "=== Gave up after $MAX_ATTEMPTS attempts - quota likely needs manual attention (billing, or check the Google AI Studio dashboard) ==="
exit 1
