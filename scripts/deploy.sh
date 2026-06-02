#!/usr/bin/env bash
# Build, push, and deploy SCD Reporting to the OKD cluster.
#
# Usage:
#   ./scripts/deploy.sh [OPTIONS]
#
# Options:
#   -f FILE          Path to Helm values file with secrets
#                    (default: $SCD_VALUES_FILE, or ~/scd-reporting-values.yaml)
#   -t TAG           Docker image tag / git release tag (default: latest)
#   -n NAMESPACE     OKD namespace (default: scd-reporting)
#   --skip-push      Skip git push
#   --skip-build     Skip Docker build and push (Helm + restart only)
#   --skip-helm      Skip Helm upgrade (build + restart only)
#   --no-cache       Pass --no-cache to docker buildx build
#   --dry-run        Print commands without executing them
#   -h               Show this help message
#
# Environment variables:
#   SCD_VALUES_FILE  Default path to the Helm values file

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
NAMESPACE="scd-reporting"
RELEASE="scd-reporting"
CHART="${REPO_ROOT}/helm/simple"
TAG=""
SKIP_PUSH=false
SKIP_BUILD=false
SKIP_HELM=false
NO_CACHE=false
DRY_RUN=false

# Locate the values file: flag > env var > well-known paths
VALUES_FILE="${SCD_VALUES_FILE:-}"
CANDIDATE_PATHS=(
    "${HOME}/scd-reporting-values.yaml"
    "${HOME}/Credentials/scd-reporting/values.yaml"
    "${REPO_ROOT}/../scd-reporting-values.yaml"
)

# ── Helpers ───────────────────────────────────────────────────────────────────
step() { echo; echo "── $* ──────────────────────────────────────────────────────" | head -c 64; echo; }
info() { echo "   $*"; }
ok()   { echo "   ✓ $*"; }
die()  { echo; echo "ERROR: $*" >&2; exit 1; }

run() {
    if [[ "${DRY_RUN}" == true ]]; then
        echo "   [dry-run] $*"
    else
        "$@"
    fi
}

usage() {
    sed -n '/^# Usage:/,/^[^#]/{ /^#/{ s/^# \{0,2\}//; p } }' "$0"
    exit 0
}

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f)           VALUES_FILE="$2"; shift 2 ;;
        -t)           TAG="$2";         shift 2 ;;
        -n)           NAMESPACE="$2";   shift 2 ;;
        --skip-push)  SKIP_PUSH=true;   shift ;;
        --skip-build) SKIP_BUILD=true;  shift ;;
        --skip-helm)  SKIP_HELM=true;   shift ;;
        --no-cache)   NO_CACHE=true;    shift ;;
        --dry-run)    DRY_RUN=true;     shift ;;
        -h|--help)    usage ;;
        *) die "Unknown option: $1" ;;
    esac
done

# ── Resolve values file ───────────────────────────────────────────────────────
if [[ -z "${VALUES_FILE}" ]]; then
    for path in "${CANDIDATE_PATHS[@]}"; do
        if [[ -f "${path}" ]]; then
            VALUES_FILE="${path}"
            break
        fi
    done
fi

if [[ "${SKIP_HELM}" == false && -z "${VALUES_FILE}" ]]; then
    die "Helm values file not found. Set SCD_VALUES_FILE, use -f FILE, or place it at:
       ${CANDIDATE_PATHS[0]}"
fi

if [[ -n "${VALUES_FILE}" && ! -f "${VALUES_FILE}" ]]; then
    die "Values file not found: ${VALUES_FILE}"
fi

# ── Resolve tag ───────────────────────────────────────────────────────────────
if [[ -z "${TAG}" ]]; then
    GIT_TAG="$(git -C "${REPO_ROOT}" describe --tags --exact-match 2>/dev/null || true)"
    TAG="${GIT_TAG:-latest}"
fi

# ── Pre-flight summary ────────────────────────────────────────────────────────
echo
echo "╔══════════════════════════════════════════════╗"
echo "║      SCD Reporting — Deploy                  ║"
echo "╚══════════════════════════════════════════════╝"
echo
info "Namespace   : ${NAMESPACE}"
info "Tag         : ${TAG}"
[[ -n "${VALUES_FILE}" ]] && info "Values file : ${VALUES_FILE}"
info "Skip push   : ${SKIP_PUSH}"
info "Skip build  : ${SKIP_BUILD}"
info "Skip helm   : ${SKIP_HELM}"
[[ "${DRY_RUN}" == true ]] && info "Mode        : DRY RUN — no changes will be made"
echo

# ── Step 1: git push ──────────────────────────────────────────────────────────
if [[ "${SKIP_PUSH}" == false ]]; then
    step "1 — Pushing to GitHub"
    run git -C "${REPO_ROOT}" push fnal main
    ok "Pushed to fnal/main"
else
    info "Skipping git push"
fi

# ── Step 2: Docker build & push ───────────────────────────────────────────────
if [[ "${SKIP_BUILD}" == false ]]; then
    step "2 — Building and pushing Docker image"
    BUILD_ARGS=("--push")
    [[ "${TAG}" != "latest" ]] && BUILD_ARGS+=("-t" "${TAG}")
    [[ "${NO_CACHE}" == true ]] && BUILD_ARGS+=("--no-cache")
    run "${SCRIPT_DIR}/build-docker.sh" "${BUILD_ARGS[@]}"
    ok "Image pushed"
else
    info "Skipping Docker build"
fi

# ── Step 3: Helm upgrade ──────────────────────────────────────────────────────
if [[ "${SKIP_HELM}" == false ]]; then
    step "3 — Running Helm upgrade"
    run helm upgrade "${RELEASE}" "${CHART}" \
        -n "${NAMESPACE}" \
        -f "${VALUES_FILE}"
    ok "Helm release upgraded"
else
    info "Skipping Helm upgrade"
fi

# ── Step 4: Rollout restart ───────────────────────────────────────────────────
step "4 — Restarting pod and waiting for readiness"
run oc rollout restart deployment/web -n "${NAMESPACE}"
run oc rollout status  deployment/web -n "${NAMESPACE}" --timeout=120s
echo
run oc get pods -n "${NAMESPACE}"

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo "╔══════════════════════════════════════════════╗"
echo "║      Deploy complete                         ║"
echo "╚══════════════════════════════════════════════╝"
echo
