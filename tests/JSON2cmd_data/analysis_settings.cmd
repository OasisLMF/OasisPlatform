#!/bin/sh
mkfifo working/gul1
mkfifo working/il1
mkfifo working/gul1summary1
mkfifo working/gul1summary1eltcalc
mkfifo working/il1summary1
mkfifo working/il1summary1eltcalc
tee < working/gul1summary1  > working/gul1summary1eltcalc
tee < working/il1summary1  > working/il1summary1eltcalc
eltcalc < working/gul1summary1eltcalc > working/gul_1_eltcalc_1
eltcalc < working/il1summary1eltcalc > working/il_1_eltcalc_1
summarycalc -g  -1 working/gul1summary1 < working/gul1
summarycalc -f  -1 working/il1summary1 < working/il1
eve 1 1 | getmodel | gulcalc -S100  -L100 -r -c working/gul1  -i - | fmcalc > working/il1
cat working/gul_1_eltcalc_1 > output/gul_1_eltcalc.csv
cat working/il_1_eltcalc_1 > output/il_1_eltcalc.csv
