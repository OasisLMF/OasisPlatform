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

mkfifo fifo/gul_P2

mkfifo fifo/gul_S1_summary_P2
mkfifo fifo/gul_S1_summaryeltcalc_P2
mkfifo fifo/gul_S1_eltcalc_P2
mkfifo fifo/gul_S1_summarysummarycalc_P2
mkfifo fifo/gul_S1_summarycalc_P2
mkfifo fifo/gul_S1_summarypltcalc_P2
mkfifo fifo/gul_S1_pltcalc_P2
mkfifo fifo/gul_S1_summaryaalcalc_P2

mkdir work/gul_S1_summaryaalcalc

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

kat fifo/gul_S1_eltcalc_P1 fifo/gul_S1_eltcalc_P2 > output/gul_S1_eltcalc.csv & pid4=$!
kat fifo/gul_S1_pltcalc_P1 fifo/gul_S1_pltcalc_P2 > output/gul_S1_pltcalc.csv & pid5=$!
kat fifo/gul_S1_summarycalc_P1 fifo/gul_S1_summarycalc_P2 > output/gul_S1_summarycalc.csv & pid6=$!

sleep 2

# --- Do insured loss computes ---

eltcalc < fifo/il_S1_summaryeltcalc_P1 > fifo/il_S1_eltcalc_P1 &
summarycalctocsv < fifo/il_S1_summarysummarycalc_P1 > fifo/il_S1_summarycalc_P1 &
pltcalc < fifo/il_S1_summarypltcalc_P1 > fifo/il_S1_pltcalc_P1 &
aalcalc < fifo/il_S1_summaryaalcalc_P1 > work/il_S1_aalcalc/P1.bin & pid1=$!

tee < fifo/il_S1_summary_P1 fifo/il_S1_summaryeltcalc_P1 fifo/il_S1_summarypltcalc_P1 fifo/il_S1_summarysummarycalc_P1 fifo/il_S1_summaryaalcalc_P1  > /dev/null & pid8=$!
summarycalc -f -1 fifo/il_S1_summary_P1  < fifo/il_P1 &
eltcalc < fifo/il_S1_summaryeltcalc_P2 > fifo/il_S1_eltcalc_P2 &
summarycalctocsv < fifo/il_S1_summarysummarycalc_P2 > fifo/il_S1_summarycalc_P2 &
pltcalc < fifo/il_S1_summarypltcalc_P2 > fifo/il_S1_pltcalc_P2 &
aalcalc < fifo/il_S1_summaryaalcalc_P2 > work/il_S1_aalcalc/P2.bin & pid2=$!

tee < fifo/il_S1_summary_P2 fifo/il_S1_summaryeltcalc_P2 fifo/il_S1_summarypltcalc_P2 fifo/il_S1_summarysummarycalc_P2 fifo/il_S1_summaryaalcalc_P2  > /dev/null & pid10=$!
summarycalc -f -1 fifo/il_S1_summary_P2  < fifo/il_P2 &

# --- Do ground up loss  computes ---

eltcalc < fifo/gul_S1_summaryeltcalc_P1 > fifo/gul_S1_eltcalc_P1 &
summarycalctocsv < fifo/gul_S1_summarysummarycalc_P1 > fifo/gul_S1_summarycalc_P1 &
pltcalc < fifo/gul_S1_summarypltcalc_P1 > fifo/gul_S1_pltcalc_P1 &
aalcalc < fifo/gul_S1_summaryaalcalc_P1 > work/gul_S1_aalcalc/P1.bin & pid1=$!

tee < fifo/gul_S1_summary_P1 fifo/gul_S1_summaryeltcalc_P1 fifo/gul_S1_summarypltcalc_P1 fifo/gul_S1_summarysummarycalc_P1 fifo/gul_S1_summaryaalcalc_P1  > /dev/null & pid12=$!
summarycalc -g -1 fifo/gul_S1_summary_P1  < fifo/gul_P1 &
eltcalc < fifo/gul_S1_summaryeltcalc_P2 > fifo/gul_S1_eltcalc_P2 &
summarycalctocsv < fifo/gul_S1_summarysummarycalc_P2 > fifo/gul_S1_summarycalc_P2 &
pltcalc < fifo/gul_S1_summarypltcalc_P2 > fifo/gul_S1_pltcalc_P2 &
aalcalc < fifo/gul_S1_summaryaalcalc_P2 > work/gul_S1_aalcalc/P2.bin & pid2=$!

tee < fifo/gul_S1_summary_P2 fifo/gul_S1_summaryeltcalc_P2 fifo/gul_S1_summarypltcalc_P2 fifo/gul_S1_summarysummarycalc_P2 fifo/gul_S1_summaryaalcalc_P2  > /dev/null & pid14=$!
summarycalc -g -1 fifo/gul_S1_summary_P2  < fifo/gul_P2 &

eve 1 2 | getmodel | gulcalc -S0 -L0 -r -c fifo/gul_P1 -i - | fmcalc > fifo/il_P1  &
eve 2 2 | getmodel | gulcalc -S0 -L0 -r -c fifo/gul_P2 -i - | fmcalc > fifo/il_P2  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8 $pid9 $pid10 $pid11 $pid12 $pid13 $pid14 


aalsummary -Kil_S1_aalcalc > output/il_S1_aalcalc.csv & apid1=$!
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

rm fifo/gul_P2

rm fifo/gul_S1_summary_P2
rm fifo/gul_S1_summaryeltcalc_P2
rm fifo/gul_S1_eltcalc_P2
rm fifo/gul_S1_summarysummarycalc_P2
rm fifo/gul_S1_summarycalc_P2
rm fifo/gul_S1_summarypltcalc_P2
rm fifo/gul_S1_pltcalc_P2
rm fifo/gul_S1_summaryaalcalc_P2

rm work/gul_S1_summaryaalcalc/*
rmdir work/gul_S1_summaryaalcalc

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
