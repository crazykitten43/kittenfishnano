#!/usr/bin/env bash
# Parse the complete launcher before taking ownership of the VM.
{
set -Eeuo pipefail
cd "$(dirname "$0")/.."
project=${KF_PROJECT:-project-845b9345-31a5-43ef-8ea}
zone=${KF_ZONE:-asia-northeast3-a}
vm=kittenfishgpu
remote="kittenfishchess@$vm"
run="${1:?Pass a unique alphanumeric run name}"
[[ "$run" =~ ^[a-zA-Z0-9_-]+$ ]]
manifest="${KF_MANIFEST:-/home/kittenfishchess/kittenfishtraining-100m/data/kf100m/manifest.json}"
[[ "$manifest" =~ ^/[a-zA-Z0-9_./-]+$ ]]
cloud=(--project="$project" --zone="$zone" --quiet)
ssh=(-oConnectTimeout=8 -oServerAliveInterval=15 -oServerAliveCountMax=3)
ssh_flags=()
for flag in "${ssh[@]}"; do ssh_flags+=("--ssh-flag=$flag"); done
result="$PWD/results/nnue/$run"
work="micro-nnue/$run"
mkdir -p "$result"
armed=0
ready=0
started=0
cleanup() {
    local rc=$?
    trap - EXIT
    trap '' INT TERM HUP
    set +e
    if ((ready)); then
        archive=$(mktemp)
        if gcloud compute ssh "$remote" "${cloud[@]}" "${ssh_flags[@]}" \
            --command="LC_ALL=C timeout 120 tar -C '$work' -czf - artifacts" > "$archive"; then
            tar -C "$result" --strip-components=1 -xzf "$archive" || rc=1
        else
            echo "Artifact collection failed. VM files are under $work/artifacts." >&2
            rc=1
        fi
        rm -f "$archive"
    fi
    if ((armed)); then
        status=
        for attempt in 1 2 3; do
            gcloud compute instances stop "$vm" "${cloud[@]}"
            status=$(gcloud compute instances describe "$vm" "${cloud[@]}" --format='value(status)')
            [[ "$status" == TERMINATED ]] && break
        done
        echo "Final VM status: $status" | tee "$result/vm-status.txt"
        if ((started)); then
            echo "Elapsed wall seconds including startup and shutdown: $((SECONDS-started))" | tee -a "$result/vm-status.txt"
        fi
        [[ "$status" == TERMINATED ]] || rc=1
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
status=$(gcloud compute instances describe "$vm" "${cloud[@]}" --format='value(status)')
[[ "$status" == TERMINATED ]] || { echo "Expected stopped VM, found $status"; exit 1; }
# Enforced by Compute Engine, including if the local process or network dies.
gcloud compute instances set-scheduling "$vm" "${cloud[@]}" \
    --max-run-duration=3h --instance-termination-action=STOP
armed=1
started=$SECONDS
gcloud compute instances start "$vm" "${cloud[@]}"
for attempt in {1..15}; do
    if gcloud compute ssh "$remote" "${cloud[@]}" "${ssh_flags[@]}" \
        --command="mkdir -p '$work/source' '$work/artifacts'"; then
        ready=1
        break
    fi
    sleep 5
done
((ready))
COPYFILE_DISABLE=1 tar --no-xattrs --exclude=__pycache__ -czf - nnue include src benchmarks CMakeLists.txt Makefile | \
    gcloud compute ssh "$remote" "${cloud[@]}" "${ssh_flags[@]}" \
       --command="LC_ALL=C tar -xzf - -C '$work/source'"
gcloud compute ssh "$remote" "${cloud[@]}" "${ssh_flags[@]}" \
    --command="cd '$work' && timeout --kill-after=20 10100 bash source/nnue/remote.sh '$manifest'" \
    2>&1 | tee "$result/console.log"
}
