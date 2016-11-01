#!/bin/bash

mkfifo fifo/il_P1

mkfifo fifo/il_S1_summary_P1
mkfifo fifo/il_S1_summaryeltcalc_P1
mkfifo fifo/il_S1_eltcalc_P1
mkfifo fifo/il_S1_summarysummarycalc_P1
mkfifo fifo/il_S1_summarycalc_P1
mkfifo fifo/il_S1_summarypltcalc_P1
mkfifo fifo/il_S1_pltcalc_P1
mkfifo fifo/il_S1_summaryaalcalc_P1

mkfifo fifo/il_P2

mkfifo fifo/il_S1_summary_P2
mkfifo fifo/il_S1_summaryeltcalc_P2
mkfifo fifo/il_S1_eltcalc_P2
mkfifo fifo/il_S1_summarysummarycalc_P2
mkfifo fifo/il_S1_summarycalc_P2
mkfifo fifo/il_S1_summarypltcalc_P2
mkfifo fifo/il_S1_pltcalc_P2
mkfifo fifo/il_S1_summaryaalcalc_P2

mkdir work/il_S1_summaryaalcalc

# --- Do insured loss kats ---

kat fifo/il_S1_eltcalc_P1 fifo/il_S1_eltcalc_P2 > output/il_S1_eltcalc.csv & pid1=$!
kat fifo/il_S1_pltcalc_P1 fifo/il_S1_pltcalc_P2 > output/il_S1_pltcalc.csv & pid2=$!
kat fifo/il_S1_summarycalc_P1 fifo/il_S1_summarycalc_P2 > output/il_S1_summarycalc.csv & pid3=$!

# --- Do ground up loss kats ---


sleep 2

# --- Do insured loss computes ---

eltcalc < fifo/il_S1_summaryeltcalc_P1 > fifo/il_S1_eltcalc_P1 &
summarycalctocsv < fifo/il_S1_summarysummarycalc_P1 > fifo/il_S1_summarycalc_P1 &
pltcalc < fifo/il_S1_summarypltcalc_P1 > fifo/il_S1_pltcalc_P1 &
aalcalc < fifo/il_S1_summaryaalcalc_P1 > work/il_S1_aalcalc/P1.bin & pid1=$!

tee < fifo/il_S1_summary_P1 fifo/il_S1_summaryeltcalc_P1 fifo/il_S1_summarypltcalc_P1 fifo/il_S1_summarysummarycalc_P1 fifo/il_S1_summaryaalcalc_P1  > /dev/null & pid5=$!
summarycalc -f -1 fifo/il_S1_summary_P1  < fifo/il_P1 &
eltcalc < fifo/il_S1_summaryeltcalc_P2 > fifo/il_S1_eltcalc_P2 &
summarycalctocsv < fifo/il_S1_summarysummarycalc_P2 > fifo/il_S1_summarycalc_P2 &
pltcalc < fifo/il_S1_summarypltcalc_P2 > fifo/il_S1_pltcalc_P2 &
aalcalc < fifo/il_S1_summaryaalcalc_P2 > work/il_S1_aalcalc/P2.bin & pid2=$!

tee < fifo/il_S1_summary_P2 fifo/il_S1_summaryeltcalc_P2 fifo/il_S1_summarypltcalc_P2 fifo/il_S1_summarysummarycalc_P2 fifo/il_S1_summaryaalcalc_P2  > /dev/null & pid7=$!
summarycalc -f -1 fifo/il_S1_summary_P2  < fifo/il_P2 &

# --- Do ground up loss  computes ---


eve 1 2 | getmodel | gulcalc -S0 -L0 -r -c fifo/gul_P1 -i - | fmcalc > fifo/il_P1  &
eve 2 2 | getmodel | gulcalc -S0 -L0 -r -c fifo/gul_P2 -i - | fmcalc > fifo/il_P2  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 


aalsummary -Kil_S1_aalcalc > output/il_S1_aalcalc.csv & apid1=$!
wait $apid1 


rm fifo/il_P1

rm fifo/il_S1_summary_P1
rm fifo/il_S1_summaryeltcalc_P1
rm fifo/il_S1_eltcalc_P1
rm fifo/il_S1_summarysummarycalc_P1
rm fifo/il_S1_summarycalc_P1
rm fifo/il_S1_summarypltcalc_P1
rm fifo/il_S1_pltcalc_P1
rm fifo/il_S1_summaryaalcalc_P1

rm fifo/il_P2

rm fifo/il_S1_summary_P2
rm fifo/il_S1_summaryeltcalc_P2
rm fifo/il_S1_eltcalc_P2
rm fifo/il_S1_summarysummarycalc_P2
rm fifo/il_S1_summarycalc_P2
rm fifo/il_S1_summarypltcalc_P2
rm fifo/il_S1_pltcalc_P2
rm fifo/il_S1_summaryaalcalc_P2

rm work/il_S1_summaryaalcalc/*
rmdir work/il_S1_summaryaalcalc
