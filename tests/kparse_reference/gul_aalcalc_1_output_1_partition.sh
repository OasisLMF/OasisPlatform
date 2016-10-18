#!/bin/bash
mkfifo fifo/gul_P1

mkfifo fifo/gul_S1_summary_P1
mkfifo fifo/gul_S1_summaryaalcalc_P1



# --- Do insured loss kats ---


# --- Do ground up loss kats ---



# --- Do insured loss computes ---


# --- Do ground up loss  computes ---

aalcalc < fifo/gul_S1_summaryaalcalc_P1 > work/gul_S1_aalcalc_P1 & pid1=$!

tee < fifo/gul_S1_summary_P1 fifo/gul_S1_summaryaalcalc_P1  > /dev/null & pid2=$!
summarycalc -g -1 fifo/gul_S1_summary_P1  < fifo/gul_P1 &

eve 1 1 | getmodel | gulcalc -S100 -L100 -r -c - > fifo/gul_P1  &

wait $pid1 $pid2 


aalsummary -Kgul_S1_aalcalc > output/gul_S1_aalcalc.csv & apid1=$!
wait $apid1 

rm fifo/gul_P1

rm fifo/gul_S1_summary_P1
rm fifo/gul_S1_summaryaalcalc_P1


