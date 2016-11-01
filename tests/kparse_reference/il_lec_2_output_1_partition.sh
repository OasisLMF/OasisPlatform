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
mkfifo fifo/il_S2_summary_P1
mkfifo fifo/il_S2_summaryeltcalc_P1
mkfifo fifo/il_S2_eltcalc_P1
mkfifo fifo/il_S2_summarysummarycalc_P1
mkfifo fifo/il_S2_summarycalc_P1
mkfifo fifo/il_S2_summarypltcalc_P1
mkfifo fifo/il_S2_pltcalc_P1
mkfifo fifo/il_S2_summaryaalcalc_P1

mkdir work/il_S1_summaryleccalc
mkdir work/il_S1_summaryaalcalc
mkdir work/il_S2_summaryleccalc
mkdir work/il_S2_summaryaalcalc

# --- Do insured loss kats ---

kat fifo/il_S1_eltcalc_P1 > output/il_S1_eltcalc.csv & pid1=$!
kat fifo/il_S1_pltcalc_P1 > output/il_S1_pltcalc.csv & pid2=$!
kat fifo/il_S1_summarycalc_P1 > output/il_S1_summarycalc.csv & pid3=$!
kat fifo/il_S2_eltcalc_P1 > output/il_S2_eltcalc.csv & pid4=$!
kat fifo/il_S2_pltcalc_P1 > output/il_S2_pltcalc.csv & pid5=$!
kat fifo/il_S2_summarycalc_P1 > output/il_S2_summarycalc.csv & pid6=$!

# --- Do ground up loss kats ---


sleep 2

# --- Do insured loss computes ---

eltcalc < fifo/il_S1_summaryeltcalc_P1 > fifo/il_S1_eltcalc_P1 &
summarycalctocsv < fifo/il_S1_summarysummarycalc_P1 > fifo/il_S1_summarycalc_P1 &
pltcalc < fifo/il_S1_summarypltcalc_P1 > fifo/il_S1_pltcalc_P1 &
aalcalc < fifo/il_S1_summaryaalcalc_P1 > work/il_S1_aalcalc/P1.bin & pid1=$!

eltcalc < fifo/il_S2_summaryeltcalc_P1 > fifo/il_S2_eltcalc_P1 &
summarycalctocsv < fifo/il_S2_summarysummarycalc_P1 > fifo/il_S2_summarycalc_P1 &
pltcalc < fifo/il_S2_summarypltcalc_P1 > fifo/il_S2_pltcalc_P1 &
aalcalc < fifo/il_S2_summaryaalcalc_P1 > work/il_S2_aalcalc/P1.bin & pid1=$!

tee < fifo/il_S1_summary_P1 fifo/il_S1_summaryeltcalc_P1 fifo/il_S1_summarypltcalc_P1 fifo/il_S1_summarysummarycalc_P1 fifo/il_S1_summaryaalcalc_P1 work/il_S1_summaryleccalc/P1.bin  > /dev/null & pid9=$!
tee < fifo/il_S2_summary_P1 fifo/il_S2_summaryeltcalc_P1 fifo/il_S2_summarypltcalc_P1 fifo/il_S2_summarysummarycalc_P1 fifo/il_S2_summaryaalcalc_P1 work/il_S2_summaryleccalc/P1.bin  > /dev/null & pid10=$!
summarycalc -f -1 fifo/il_S1_summary_P1 -2 fifo/il_S2_summary_P1  < fifo/il_P1 &

# --- Do ground up loss  computes ---


eve 1 1 | getmodel | gulcalc -S0 -L0 -r -i - | fmcalc > fifo/il_P1  &
eve 1 1 | getmodel | gulcalc -S0 -L0 -r -i - | fmcalc > fifo/il_P1  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8 $pid9 $pid10 


aalsummary -Kil_S1_aalcalc > output/il_S1_aalcalc.csv & apid1=$!
leccalc -r -Kil_S1_summaryleccalc -s output/il_S1_leccalc_sample_mean_oep.csv -S output/il_S1_leccalc_sample_mean_aep.csv -f output/il_S1_leccalc_full_uncertainty_oep.csv -W output/il_S1_leccalc_wheatsheaf_aep.csv -M output/il_S1_leccalc_wheatsheaf_mean_aep.csv -F output/il_S1_leccalc_full_uncertainty_aep.csv -m output/il_S1_leccalc_wheatsheaf_mean_oep.csv -w output/il_S1_leccalc_wheatsheaf_oep.csv  &  lpid1=$!
aalsummary -Kil_S2_aalcalc > output/il_S2_aalcalc.csv & apid2=$!
leccalc -r -Kil_S2_summaryleccalc -s output/il_S2_leccalc_sample_mean_oep.csv -S output/il_S2_leccalc_sample_mean_aep.csv -f output/il_S2_leccalc_full_uncertainty_oep.csv -W output/il_S2_leccalc_wheatsheaf_aep.csv -M output/il_S2_leccalc_wheatsheaf_mean_aep.csv -F output/il_S2_leccalc_full_uncertainty_aep.csv -m output/il_S2_leccalc_wheatsheaf_mean_oep.csv -w output/il_S2_leccalc_wheatsheaf_oep.csv  &  lpid2=$!
wait $apid1 $apid2 

wait $lpid1 $lpid2 


rm fifo/il_P1

rm fifo/il_S1_summary_P1
rm fifo/il_S1_summaryeltcalc_P1
rm fifo/il_S1_eltcalc_P1
rm fifo/il_S1_summarysummarycalc_P1
rm fifo/il_S1_summarycalc_P1
rm fifo/il_S1_summarypltcalc_P1
rm fifo/il_S1_pltcalc_P1
rm fifo/il_S1_summaryaalcalc_P1
rm fifo/il_S2_summary_P1
rm fifo/il_S2_summaryeltcalc_P1
rm fifo/il_S2_eltcalc_P1
rm fifo/il_S2_summarysummarycalc_P1
rm fifo/il_S2_summarycalc_P1
rm fifo/il_S2_summarypltcalc_P1
rm fifo/il_S2_pltcalc_P1
rm fifo/il_S2_summaryaalcalc_P1

rm work/il_S1_summaryleccalc/*
rmdir work/il_S1_summaryleccalc
rm work/il_S1_summaryaalcalc/*
rmdir work/il_S1_summaryaalcalc
rm work/il_S2_summaryleccalc/*
rmdir work/il_S2_summaryleccalc
rm work/il_S2_summaryaalcalc/*
rmdir work/il_S2_summaryaalcalc
