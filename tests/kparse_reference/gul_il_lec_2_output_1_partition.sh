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
mkfifo fifo/gul_S2_summary_P1
mkfifo fifo/gul_S2_summaryeltcalc_P1
mkfifo fifo/gul_S2_eltcalc_P1
mkfifo fifo/gul_S2_summarysummarycalc_P1
mkfifo fifo/gul_S2_summarycalc_P1
mkfifo fifo/gul_S2_summarypltcalc_P1
mkfifo fifo/gul_S2_pltcalc_P1
mkfifo fifo/gul_S2_summaryaalcalc_P1

mkdir work/gul_S1_summaryleccalc
mkdir work/gul_S2_summaryleccalc

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
mkdir work/il_S2_summaryleccalc

# --- Do insured loss kats ---

kat fifo/il_S1_eltcalc_P1 > output/il_S1_eltcalc.csv & pid127=$!
kat fifo/il_S1_pltcalc_P1 > output/il_S1_pltcalc.csv & pid128=$!
kat fifo/il_S1_summarycalc_P1 > output/il_S1_summarycalc.csv & pid129=$!
kat fifo/il_S2_eltcalc_P1 > output/il_S2_eltcalc.csv & pid130=$!
kat fifo/il_S2_pltcalc_P1 > output/il_S2_pltcalc.csv & pid131=$!
kat fifo/il_S2_summarycalc_P1 > output/il_S2_summarycalc.csv & pid132=$!

# --- Do ground up loss kats ---

kat fifo/gul_S1_eltcalc_P1 > output/gul_S1_eltcalc.csv & pid133=$!
kat fifo/gul_S1_pltcalc_P1 > output/gul_S1_pltcalc.csv & pid134=$!
kat fifo/gul_S1_summarycalc_P1 > output/gul_S1_summarycalc.csv & pid135=$!
kat fifo/gul_S2_eltcalc_P1 > output/gul_S2_eltcalc.csv & pid136=$!
kat fifo/gul_S2_pltcalc_P1 > output/gul_S2_pltcalc.csv & pid137=$!
kat fifo/gul_S2_summarycalc_P1 > output/gul_S2_summarycalc.csv & pid138=$!

sleep 2

# --- Do insured loss computes ---

eltcalc < fifo/il_S1_summaryeltcalc_P1 > fifo/il_S1_eltcalc_P1 &
summarycalctocsv < fifo/il_S1_summarysummarycalc_P1 > fifo/il_S1_summarycalc_P1 &
pltcalc < fifo/il_S1_summarypltcalc_P1 > fifo/il_S1_pltcalc_P1 &
aalcalc < fifo/il_S1_summaryaalcalc_P1 > work/il_S1_aalcalc_P1 & pid1=$!

eltcalc < fifo/il_S2_summaryeltcalc_P1 > fifo/il_S2_eltcalc_P1 &
summarycalctocsv < fifo/il_S2_summarysummarycalc_P1 > fifo/il_S2_summarycalc_P1 &
pltcalc < fifo/il_S2_summarypltcalc_P1 > fifo/il_S2_pltcalc_P1 &
aalcalc < fifo/il_S2_summaryaalcalc_P1 > work/il_S2_aalcalc_P1 & pid1=$!

tee < fifo/il_S1_summary_P1 fifo/il_S1_summaryeltcalc_P1 fifo/il_S1_summarypltcalc_P1 fifo/il_S1_summarysummarycalc_P1 fifo/il_S1_summaryaalcalc_P1 work/il_S1_summaryleccalc/P1.bin  > /dev/null & pid141=$!
tee < fifo/il_S2_summary_P1 fifo/il_S2_summaryeltcalc_P1 fifo/il_S2_summarypltcalc_P1 fifo/il_S2_summarysummarycalc_P1 fifo/il_S2_summaryaalcalc_P1 work/il_S2_summaryleccalc/P1.bin  > /dev/null & pid142=$!
summarycalc -f -1 fifo/il_S1_summary_P1 -2 fifo/il_S2_summary_P1  < fifo/il_P1 &

# --- Do ground up loss  computes ---

eltcalc < fifo/gul_S1_summaryeltcalc_P1 > fifo/gul_S1_eltcalc_P1 &
summarycalctocsv < fifo/gul_S1_summarysummarycalc_P1 > fifo/gul_S1_summarycalc_P1 &
pltcalc < fifo/gul_S1_summarypltcalc_P1 > fifo/gul_S1_pltcalc_P1 &
aalcalc < fifo/gul_S1_summaryaalcalc_P1 > work/gul_S1_aalcalc_P1 & pid1=$!

eltcalc < fifo/gul_S2_summaryeltcalc_P1 > fifo/gul_S2_eltcalc_P1 &
summarycalctocsv < fifo/gul_S2_summarysummarycalc_P1 > fifo/gul_S2_summarycalc_P1 &
pltcalc < fifo/gul_S2_summarypltcalc_P1 > fifo/gul_S2_pltcalc_P1 &
aalcalc < fifo/gul_S2_summaryaalcalc_P1 > work/gul_S2_aalcalc_P1 & pid1=$!

tee < fifo/gul_S1_summary_P1 fifo/gul_S1_summaryeltcalc_P1 fifo/gul_S1_summarypltcalc_P1 fifo/gul_S1_summarysummarycalc_P1 fifo/gul_S1_summaryaalcalc_P1 work/gul_S1_summaryleccalc/P1.bin  > /dev/null & pid145=$!
tee < fifo/gul_S2_summary_P1 fifo/gul_S2_summaryeltcalc_P1 fifo/gul_S2_summarypltcalc_P1 fifo/gul_S2_summarysummarycalc_P1 fifo/gul_S2_summaryaalcalc_P1 work/gul_S2_summaryleccalc/P1.bin  > /dev/null & pid146=$!
summarycalc -g -1 fifo/gul_S1_summary_P1 -2 fifo/gul_S2_summary_P1  < fifo/gul_P1 &

eve 1 1 | getmodel | gulcalc -S0 -L0 -r -c fifo/gul_P1 -i - | fmcalc > fifo/il_P1  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8 $pid9 $pid10 $pid11 $pid12 $pid13 $pid14 $pid15 $pid16 $pid17 $pid18 $pid19 $pid20 $pid21 $pid22 $pid23 $pid24 $pid25 $pid26 $pid27 $pid28 $pid29 $pid30 $pid31 $pid32 $pid33 $pid34 $pid35 $pid36 $pid37 $pid38 $pid39 $pid40 $pid41 $pid42 $pid43 $pid44 $pid45 $pid46 $pid47 $pid48 $pid49 $pid50 $pid51 $pid52 $pid53 $pid54 $pid55 $pid56 $pid57 $pid58 $pid59 $pid60 $pid61 $pid62 $pid63 $pid64 $pid65 $pid66 $pid67 $pid68 $pid69 $pid70 $pid71 $pid72 $pid73 $pid74 $pid75 $pid76 $pid77 $pid78 $pid79 $pid80 $pid81 $pid82 $pid83 $pid84 $pid85 $pid86 $pid87 $pid88 $pid89 $pid90 $pid91 $pid92 $pid93 $pid94 $pid95 $pid96 $pid97 $pid98 $pid99 $pid100 $pid101 $pid102 $pid103 $pid104 $pid105 $pid106 $pid107 $pid108 $pid109 $pid110 $pid111 $pid112 $pid113 $pid114 $pid115 $pid116 $pid117 $pid118 $pid119 $pid120 $pid121 $pid122 $pid123 $pid124 $pid125 $pid126 $pid127 $pid128 $pid129 $pid130 $pid131 $pid132 $pid133 $pid134 $pid135 $pid136 $pid137 $pid138 $pid139 $pid140 $pid141 $pid142 $pid143 $pid144 $pid145 $pid146 


aalsummary -Kil_S1_aalcalc > output/il_S1_aalcalc.csv & apid11=$!
leccalc -r -Kil_S1_summaryleccalc -s output/il_S1_leccalc_sample_mean_oep.csv -S output/il_S1_leccalc_sample_mean_aep.csv -f output/il_S1_leccalc_full_uncertainty_oep.csv -W output/il_S1_leccalc_wheatsheaf_aep.csv -M output/il_S1_leccalc_wheatsheaf_mean_aep.csv -F output/il_S1_leccalc_full_uncertainty_aep.csv -m output/il_S1_leccalc_wheatsheaf_mean_oep.csv -w output/il_S1_leccalc_wheatsheaf_oep.csv  &  lpid9=$!
aalsummary -Kil_S2_aalcalc > output/il_S2_aalcalc.csv & apid12=$!
leccalc -r -Kil_S2_summaryleccalc -s output/il_S2_leccalc_sample_mean_oep.csv -S output/il_S2_leccalc_sample_mean_aep.csv -f output/il_S2_leccalc_full_uncertainty_oep.csv -W output/il_S2_leccalc_wheatsheaf_aep.csv -M output/il_S2_leccalc_wheatsheaf_mean_aep.csv -F output/il_S2_leccalc_full_uncertainty_aep.csv -m output/il_S2_leccalc_wheatsheaf_mean_oep.csv -w output/il_S2_leccalc_wheatsheaf_oep.csv  &  lpid10=$!
aalsummary -Kgul_S1_aalcalc > output/gul_S1_aalcalc.csv & apid13=$!
leccalc -r -Kgul_S1_summaryleccalc -s output/gul_S1_leccalc_sample_mean_oep.csv -S output/gul_S1_leccalc_sample_mean_aep.csv -f output/gul_S1_leccalc_full_uncertainty_oep.csv -W output/gul_S1_leccalc_wheatsheaf_aep.csv -M output/gul_S1_leccalc_wheatsheaf_mean_aep.csv -F output/gul_S1_leccalc_full_uncertainty_aep.csv -m output/gul_S1_leccalc_wheatsheaf_mean_oep.csv -w output/gul_S1_leccalc_wheatsheaf_oep.csv  &  lpid11=$!
aalsummary -Kgul_S2_aalcalc > output/gul_S2_aalcalc.csv & apid14=$!
leccalc -r -Kgul_S2_summaryleccalc -s output/gul_S2_leccalc_sample_mean_oep.csv -S output/gul_S2_leccalc_sample_mean_aep.csv -f output/gul_S2_leccalc_full_uncertainty_oep.csv -W output/gul_S2_leccalc_wheatsheaf_aep.csv -M output/gul_S2_leccalc_wheatsheaf_mean_aep.csv -F output/gul_S2_leccalc_full_uncertainty_aep.csv -m output/gul_S2_leccalc_wheatsheaf_mean_oep.csv -w output/gul_S2_leccalc_wheatsheaf_oep.csv  &  lpid12=$!
wait $apid1 $apid2 $apid3 $apid4 $apid5 $apid6 $apid7 $apid8 $apid9 $apid10 $apid11 $apid12 $apid13 $apid14 

wait $lpid1 $lpid2 $lpid3 $lpid4 $lpid5 $lpid6 $lpid7 $lpid8 $lpid9 $lpid10 $lpid11 $lpid12 

rm fifo/gul_P1

rm fifo/gul_S1_summary_P1
rm fifo/gul_S1_summaryeltcalc_P1
rm fifo/gul_S1_eltcalc_P1
rm fifo/gul_S1_summarysummarycalc_P1
rm fifo/gul_S1_summarycalc_P1
rm fifo/gul_S1_summarypltcalc_P1
rm fifo/gul_S1_pltcalc_P1
rm fifo/gul_S1_summaryaalcalc_P1
rm fifo/gul_S2_summary_P1
rm fifo/gul_S2_summaryeltcalc_P1
rm fifo/gul_S2_eltcalc_P1
rm fifo/gul_S2_summarysummarycalc_P1
rm fifo/gul_S2_summarycalc_P1
rm fifo/gul_S2_summarypltcalc_P1
rm fifo/gul_S2_pltcalc_P1
rm fifo/gul_S2_summaryaalcalc_P1

rm work/gul_S1_summaryleccalc/*
rmdir work/gul_S1_summaryleccalc
rm work/gul_S2_summaryleccalc/*
rmdir work/gul_S2_summaryleccalc

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
rm work/il_S2_summaryleccalc/*
rmdir work/il_S2_summaryleccalc
