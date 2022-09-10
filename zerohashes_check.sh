#!/bin/bash
echo "Generating cairo zerohashes"
echo "Compiling zerohashes_check..."
cairo-compile zerohashes_check.cairo --output zerohashes_check.compiled.json
echo "Running zerohashes_check..."
cairo-run --program=zerohashes_check.compiled.json --layout=all --print_output > cairo_zerohashes.txt
echo "Verifying zerohashes match between cairo and etherum"
python zerohashes_check.py
rm cairo_zerohashes.txt