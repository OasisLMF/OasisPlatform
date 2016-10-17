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

mkdir work/gul_S1_summaryleccalc

mkfifo fifo/il_P1

mkfifo fifo/il_S1_summary_P1
mkfifo fifo/il_S1_summaryeltcalc_P1
mkfifo fifo/il_S1_eltcalc_P1
mkfifo fifo/il_S1_summarysummarycalc_P1
mkfifo fifo/il_S1_summarycalc_P1
mkfifo fifo/il_S1_summarypltcalc_P1
mkfifo fifo/il_S1_pltcalc_P1
mkfifo fifo/il_S1_summaryaalcalc_P1

mkdir work/il_S1_summaryleccalc

# --- Do insured loss kats ---

kat fifo/il_S1_eltcalc_P1 > output/il_S1_eltcalc.csv & pid11=$!
kat fifo/il_S1_pltcalc_P1 > output/il_S1_pltcalc.csv & pid12=$!
kat fifo/il_S1_summarycalc_P1 > output/il_S1_summarycalc.csv & pid13=$!

# --- Do ground up loss kats ---

kat fifo/gul_S1_eltcalc_P1 > output/gul_S1_eltcalc.csv & pid14=$!
kat fifo/gul_S1_pltcalc_P1 > output/gul_S1_pltcalc.csv & pid15=$!
kat fifo/gul_S1_summarycalc_P1 > output/gul_S1_summarycalc.csv & pid16=$!

sleep 2

# --- Do insured loss computes ---

eltcalc < fifo/il_S1_summaryeltcalc_P1 > fifo/il_S1_eltcalc_P1 &
summarycalctocsv < fifo/il_S1_summarysummarycalc_P1 > fifo/il_S1_summarycalc_P1 &
pltcalc < fifo/il_S1_summarypltcalc_P1 > fifo/il_S1_pltcalc_P1 &
aalcalc < fifo/il_S1_summaryaalcalc_P1 > work/il_S1_aalcalc_P1 & pid1=$!

tee < fifo/il_S1_summary_P1 fifo/il_S1_summaryeltcalc_P1 fifo/il_S1_summarypltcalc_P1 fifo/il_S1_summarysummarycalc_P1 fifo/il_S1_summaryaalcalc_P1 work/il_S1_summaryleccalc/P1.bin  > /dev/null & pid18=$!
summarycalc -f -1 fifo/il_S1_summary_P1  < fifo/il_P1 &

# --- Do ground up loss  computes ---

eltcalc < fifo/gul_S1_summaryeltcalc_P1 > fifo/gul_S1_eltcalc_P1 &
summarycalctocsv < fifo/gul_S1_summarysummarycalc_P1 > fifo/gul_S1_summarycalc_P1 &
pltcalc < fifo/gul_S1_summarypltcalc_P1 > fifo/gul_S1_pltcalc_P1 &
aalcalc < fifo/gul_S1_summaryaalcalc_P1 > work/gul_S1_aalcalc_P1 & pid1=$!

tee < fifo/gul_S1_summary_P1 fifo/gul_S1_summaryeltcalc_P1 fifo/gul_S1_summarypltcalc_P1 fifo/gul_S1_summarysummarycalc_P1 fifo/gul_S1_summaryaalcalc_P1 work/gul_S1_summaryleccalc/P1.bin  > /dev/null & pid20=$!
summarycalc -g -1 fifo/gul_S1_summary_P1  < fifo/gul_P1 &

eve 1 1 | getmodel | gulcalc -S0 -L0 -r -c fifo/gul_P1 -i - | fmcalc > fifo/il_P1  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8 $pid9 $pid10 $pid11 $pid12 $pid13 $pid14 $pid15 $pid16 $pid17 $pid18 $pid19 $pid20 


aalsummary -Kil_S1_aalcalc > output/il_S1_aalcalc.csv & apid3=$!
leccalc -r -Kil_S1_summaryleccalc
 -s output/il_S1_leccalc_sample_mean_oep.csv
 -S output/il_S1_leccalc_sample_mean_aep.csv
 -f output/il_S1_leccalc_full_uncertainty_oep.csv
 -W output/il_S1_leccalc_wheatsheaf_aep.csv
 -M output/il_S1_leccalc_wheatsheaf_mean_aep.csv
 -F output/il_S1_leccalc_full_uncertainty_aep.csv
 -m output/il_S1_leccalc_wheatsheaf_mean_oep.csv
 -w output/il_S1_leccalc_wheatsheaf_oep.csv
  &  lpid1=$!
aalsummary -Kgul_S1_aalcalc > output/gul_S1_aalcalc.csv & apid4=$!
leccalc -r -Kgul_S1_summaryleccalc
 -s output/gul_S1_leccalc_sample_mean_oep.csv
 -S output/gul_S1_leccalc_sample_mean_aep.csv
 -f output/gul_S1_leccalc_full_uncertainty_oep.csv
 -W output/gul_S1_leccalc_wheatsheaf_aep.csv
 -M output/gul_S1_leccalc_wheatsheaf_mean_aep.csv
 -F output/gul_S1_leccalc_full_uncertainty_aep.csv
 -m output/gul_S1_leccalc_wheatsheaf_mean_oep.csv
 -w output/gul_S1_leccalc_wheatsheaf_oep.csv
  &  lpid2=$!
wait $apid1 $apid2 $apid3 $apid4 

wait $lpid1 $lpid2 

rm fifo/gul_P1

rm fifo/gul_S1_summary_P1
rm fifo/gul_S1_summaryeltcalc_P1
rm fifo/gul_S1_eltcalc_P1
rm fifo/gul_S1_summarysummarycalc_P1
rm fifo/gul_S1_summarycalc_P1
rm fifo/gul_S1_summarypltcalc_P1
rm fifo/gul_S1_pltcalc_P1
rm fifo/gul_S1_summaryaalcalc_P1

rm work/gul_S1_summaryleccalc/*
rmdir work/gul_S1_summaryleccalc

rm fifo/il_P1

rm fifo/il_S1_summary_P1
rm fifo/il_S1_summaryeltcalc_P1
rm fifo/il_S1_eltcalc_P1
rm fifo/il_S1_summarysummarycalc_P1
rm fifo/il_S1_summarycalc_P1
rm fifo/il_S1_summarypltcalc_P1
rm fifo/il_S1_pltcalc_P1
rm fifo/il_S1_summaryaalcalc_P1

rm work/il_S1_summaryleccalc/*
rmdir work/il_S1_summaryleccalc
