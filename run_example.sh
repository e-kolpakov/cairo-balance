#!/bin/bash
echo "Generating input"
python main.py -s stub
echo "Compiling cairo program..."
cairo-compile tlv_prover.cairo --proof_mode --output tlv_prover.compiled.json
echo "Running cairo program..."
cairo-run --program=tlv_prover.compiled.json --layout=all --print_output --print_info --program_input tlv_prover.input.json --profile_output profile.pb.gz
echo "Cleaning up"
rm tlv_prover.compiled.json