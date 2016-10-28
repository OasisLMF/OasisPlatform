#!/bin/bash
mkfifo fifo/gul_P1

mkfifo fifo/gul_S1_summary_P1

mkdir work/gul_S1_summaryleccalc


# --- Do insured loss kats ---


# --- Do ground up loss kats ---



# --- Do insured loss computes ---


# --- Do ground up loss  computes ---

aalcalc < fifo/gul_S1_summaryaalcalc_P1 > work/gul_S1_aalcalc/P1.bin & pid1=$!

tee < fifo/gul_S1_summary_P1 work/gul_S1_summaryleccalc/P1.bin  > /dev/null & pid1=$!
summarycalc -g -1 fifo/gul_S1_summary_P1  < fifo/gul_P1 &

eve 1 1 | getmodel | gulcalc -S100 -L100 -r -c - > fifo/gul_P1  &

wait $pid1 


leccalc -r -Kgul_S1_summaryleccalc -w output/gul_S1_leccalc_wheatsheaf_oep.csv  &  lpid1=$!
wait $lpid1 

rm fifo/gul_P1

rm fifo/gul_S1_summary_P1

rm work/gul_S1_summaryleccalc/*
rmdir work/gul_S1_summaryleccalc

