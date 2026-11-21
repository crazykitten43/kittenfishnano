#!/usr/bin/env bash
set -Eeuo pipefail
begin=$SECONDS
exec > >(tee -a "$PWD/artifacts/run.log") 2>&1
manifest=$1
test -r "$manifest"
nvidia-smi > artifacts/gpu.txt
lscpu > artifacts/cpu.txt
cp "$manifest" artifacts/dataset-manifest.json
has_cuda() {
    "$1" -c 'import numpy,torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()' >/dev/null 2>&1
}
python_bin=
for candidate in "$(command -v python3)" $(find "$HOME" -maxdepth 6 -path '*/bin/python' -print); do
    if has_cuda "$candidate"; then python_bin=$candidate; break; fi
done
[[ -n "$python_bin" ]] || { echo "No existing Python with CUDA PyTorch and NumPy"; exit 1; }
"$python_bin" -c 'import numpy, torch; print(torch.__version__, torch.version.cuda, numpy.__version__, torch.cuda.get_device_name())' | tee artifacts/runtime.txt
for stage in screen medium; do
    "$python_bin" -u source/nnue/train.py "$manifest" artifacts --stage "$stage"
    if [[ "$stage" == screen ]]; then
        "$python_bin" source/nnue/estimate.py artifacts screen | tee artifacts/screen-estimate.txt
    else
        "$python_bin" source/nnue/estimate.py artifacts medium "$((9700 - (SECONDS - begin)))" | tee artifacts/medium-estimate.txt
    fi
done
limit=$(tail -n 1 artifacts/medium-estimate.txt)
"$python_bin" -u source/nnue/train.py "$manifest" artifacts --stage large --positions "$limit"
