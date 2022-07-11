#!/bin/bash
echo "Generating input"
python generate_input.py -c 10 -a eth -v eth
echo "Compiling cairo program..."
cairo-compile balance_sum_prover.cairo --proof_mode --output balance_sum_prover.compiled.json
echo "Running cairo program..."
cairo-run --program=balance_sum_prover.compiled.json --layout=all --print_output --print_info --program_input balance_sum_prover.json --profile_output profile.pb.gz