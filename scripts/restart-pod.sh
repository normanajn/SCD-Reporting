#!/usr/bin/env bash
# Restart the SCD Reporting web pod in OKD and wait for it to become ready.
#
# Usage:
#   ./scripts/restart-pod.sh [OPTIONS]
#
# Options:
#   -n NAMESPACE   OKD namespace (default: scd-reporting)
#   -t TIMEOUT     Seconds to wait for readiness (default: 120)
#   -h             Show this help message

set -euo pipefail

NAMESPACE="scd-reporting"
TIMEOUT=120

usage() {
    sed -n '/^# Usage:/,/^[^#]/{ /^#/{ s/^# \{0,2\}//; p } }' "$0"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n) NAMESPACE="$2"; shift 2 ;;
        -t) TIMEOUT="$2";   shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

echo "Restarting deployment/web in namespace '${NAMESPACE}'..."
oc rollout restart deployment/web -n "${NAMESPACE}"

echo "Waiting for pod to be ready (timeout: ${TIMEOUT}s)..."
oc rollout status deployment/web -n "${NAMESPACE}" --timeout="${TIMEOUT}s"

echo ""
oc get pods -n "${NAMESPACE}"
