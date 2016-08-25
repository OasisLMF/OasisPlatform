#!/bin/sh
mkfifo working/gul1
mkfifo working/il1
mkfifo working/gul1summary1
mkfifo working/gul1summary1summarycalc
mkfifo working/gul1summary1eltcalc
mkfifo working/gul1summary1aalcalc
mkfifo working/gul1summary1pltcalc
mkfifo working/il1summary1
mkfifo working/il1summary1summarycalc
mkfifo working/il1summary1eltcalc
mkfifo working/il1summary1aalcalc
mkfifo working/il1summary1pltcalc
tee < working/gul1summary1 working/gul1summary1summarycalc working/gul1summary1eltcalc work/gulsummary1/p1.bin working/gul1summary1aalcalc  > working/gul1summary1pltcalc
tee < working/il1summary1 working/il1summary1summarycalc working/il1summary1eltcalc work/ilsummary1/p1.bin working/il1summary1aalcalc  > working/il1summary1pltcalc
cat < working/gul1summary1summarycalc | summarycalctocsv > work/gul_1_summarycalc_1
eltcalc < working/gul1summary1eltcalc > work/gul_1_eltcalc_1
aalcalc < working/gul1summary1aalcalc > work/gulaalSummary1/p1.bin
pltcalc < working/gul1summary1pltcalc > work/gul_1_pltcalc_1
cat < working/il1summary1summarycalc | summarycalctocsv > work/il_1_summarycalc_1
eltcalc < working/il1summary1eltcalc > work/il_1_eltcalc_1
aalcalc < working/il1summary1aalcalc > work/ilaalSummary1/p1.bin
pltcalc < working/il1summary1pltcalc > work/il_1_pltcalc_1
summarycalc -g  -1 working/gul1summary1 < working/gul1
summarycalc -f  -1 working/il1summary1 < working/il1
eve 1 1 | getmodel | gulcalc -S100  -L100 -r -c working/gul1  -i - | fmcalc > working/il1
cat work/gul_1_summarycalc_1 > output/gul_1_summarycalc.csv
cat work/gul_1_eltcalc_1 > output/gul_1_eltcalc.csv
cat work/gul_1_pltcalc_1 > output/gul_1_pltcalc.csv
cat work/il_1_summarycalc_1 > output/il_1_summarycalc.csv
cat work/il_1_eltcalc_1 > output/il_1_eltcalc.csv
cat work/il_1_pltcalc_1 > output/il_1_pltcalc.csv
aalsummary -KgulaalSummary1 > output/gul_1_aalcalc.csv
leccalc -Kgulsummary1 -r -F output/gul_1_leccalc_full_uncertainty_aep.csv -f output/gul_1_leccalc_full_uncertainty_oep.csv -W output/gul_1_leccalc_wheatsheaf_aep.csv -w output/gul_1_leccalc_wheatsheaf_oep.csv -M output/gul_1_leccalc_wheatsheaf_mean_aep.csv -m output/gul_1_leccalc_wheatsheaf_mean_oep.csv -S output/gul_1_leccalc_sample_mean_aep.csv -s output/gul_1_leccalc_sample_mean_oep.csv 
aalsummary -KilaalSummary1 > output/il_1_aalcalc.csv
leccalc -Kilsummary1 -r -F output/il_1_leccalc_full_uncertainty_aep.csv -f output/il_1_leccalc_full_uncertainty_oep.csv -W output/il_1_leccalc_wheatsheaf_aep.csv -w output/il_1_leccalc_wheatsheaf_oep.csv -M output/il_1_leccalc_wheatsheaf_mean_aep.csv -m output/il_1_leccalc_wheatsheaf_mean_oep.csv -S output/il_1_leccalc_sample_mean_aep.csv -s output/il_1_leccalc_sample_mean_oep.csv 
