#!/bin/bash
mkfifo fifo/gul_P1

mkfifo fifo/gul_S1_summary_P1
mkfifo fifo/gul_S1_summarypltcalc_P1
mkfifo fifo/gul_S1_pltcalc_P1



# --- Do insured loss kats ---


# --- Do ground up loss kats ---

kat fifo/gul_S1_pltcalc_P1 > output/gul_S1_pltcalc.csv & pid1=$!

sleep 2

# --- Do insured loss computes ---


# --- Do ground up loss  computes ---

pltcalc < fifo/gul_S1_summarypltcalc_P1 > fifo/gul_S1_pltcalc_P1 &

tee < fifo/gul_S1_summary_P1 fifo/gul_S1_summarypltcalc_P1  > /dev/null & pid2=$!
summarycalc -g -1 fifo/gul_S1_summary_P1  < fifo/gul_P1 &

eve 1 1 | getmodel | gulcalc -S100 -L100 -r -c - > fifo/gul_P1  &

wait $pid1 $pid2 


rm fifo/gul_P1

rm fifo/gul_S1_summary_P1
rm fifo/gul_S1_summarypltcalc_P1
rm fifo/gul_S1_pltcalc_P1


