#!/bin/bash
mkfifo fifo/gul_P1

mkfifo fifo/gul_S1_summary_P1
mkfifo fifo/gul_S1_summaryeltcalc_P1
mkfifo fifo/gul_S1_eltcalc_P1
mkfifo fifo/gul_S1_summarysummarycalc_P1
mkfifo fifo/gul_S1_summarycalc_P1
mkfifo fifo/gul_S1_summarypltcalc_P1
mkfifo fifo/gul_S1_pltcalc_P1
mkfifo fifo/gul_S1_summaryaalcalc_P1



# --- Do insured loss kats ---


# --- Do ground up loss kats ---

kat fifo/gul_S1_eltcalc_P1 > output/gul_S1_eltcalc.csv & pid6=$!
kat fifo/gul_S1_pltcalc_P1 > output/gul_S1_pltcalc.csv & pid7=$!
kat fifo/gul_S1_summarycalc_P1 > output/gul_S1_summarycalc.csv & pid8=$!

sleep 2

# --- Do insured loss computes ---


# --- Do ground up loss  computes ---

eltcalc < fifo/gul_S1_summaryeltcalc_P1 > fifo/gul_S1_eltcalc_P1 &
summarycalctocsv < fifo/gul_S1_summarysummarycalc_P1 > fifo/gul_S1_summarycalc_P1 &
pltcalc < fifo/gul_S1_summarypltcalc_P1 > fifo/gul_S1_pltcalc_P1 &
aalcalc < fifo/gul_S1_summaryaalcalc_P1 > work/gul_S1_aalcalc_P1 & pid1=$!

tee < fifo/gul_S1_summary_P1 fifo/gul_S1_summaryeltcalc_P1 fifo/gul_S1_summarypltcalc_P1 fifo/gul_S1_summarysummarycalc_P1 fifo/gul_S1_summaryaalcalc_P1  > /dev/null & pid10=$!
summarycalc -g -1 fifo/gul_S1_summary_P1  < fifo/gul_P1 &

eve 1 1 | getmodel | gulcalc -S0 -L0 -r -c - > fifo/gul_P1  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8 $pid9 $pid10 


aalsummary -Kgul_S1_aalcalc > output/gul_S1_aalcalc.csv & apid2=$!
wait $apid1 $apid2 

rm fifo/gul_P1

rm fifo/gul_S1_summary_P1
rm fifo/gul_S1_summaryeltcalc_P1
rm fifo/gul_S1_eltcalc_P1
rm fifo/gul_S1_summarysummarycalc_P1
rm fifo/gul_S1_summarycalc_P1
rm fifo/gul_S1_summarypltcalc_P1
rm fifo/gul_S1_pltcalc_P1
rm fifo/gul_S1_summaryaalcalc_P1


