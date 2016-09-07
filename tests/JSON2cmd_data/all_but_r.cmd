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
tee < working/gul1summary1 working/gul1summary1summarycalc working/gul1summary1eltcalc working/gulsummary1/p1.bin working/gul1summary1aalcalc  > working/gul1summary1pltcalc
tee < working/il1summary1 working/il1summary1summarycalc working/il1summary1eltcalc working/ilsummary1/p1.bin working/il1summary1aalcalc  > working/il1summary1pltcalc
summarycalctocsv < working/gul1summary1summarycalc > working/gul_1_summarycalc_1
eltcalc < working/gul1summary1eltcalc > working/gul_1_eltcalc_1
aalcalc < working/gul1summary1aalcalc > working/gulaalSummary1/p1.bin
pltcalc < working/gul1summary1pltcalc > working/gul_1_pltcalc_1
summarycalctocsv < working/il1summary1summarycalc > working/il_1_summarycalc_1
eltcalc < working/il1summary1eltcalc > working/il_1_eltcalc_1
aalcalc < working/il1summary1aalcalc > working/ilaalSummary1/p1.bin
pltcalc < working/il1summary1pltcalc > working/il_1_pltcalc_1
summarycalc -g  -1 working/gul1summary1 < working/gul1
summarycalc -f  -1 working/il1summary1 < working/il1
eve 1 1 | getmodel | gulcalc -S100  -L100 -r -c working/gul1  -i - | fmcalc > working/il1
kat working/gul_1_summarycalc_1 > output/gul_1_summarycalc.csv
kat working/gul_1_eltcalc_1 > output/gul_1_eltcalc.csv
kat working/gul_1_pltcalc_1 > output/gul_1_pltcalc.csv
kat working/il_1_summarycalc_1 > output/il_1_summarycalc.csv
kat working/il_1_eltcalc_1 > output/il_1_eltcalc.csv
kat working/il_1_pltcalc_1 > output/il_1_pltcalc.csv
aalsummary -KgulaalSummary1 > output/gul_1_aalcalc.csv
