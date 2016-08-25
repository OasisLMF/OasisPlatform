#!/bin/sh
mkfifo working/gul1
mkfifo working/gul1summary1
mkfifo working/gul1summary1eltcalc
tee < working/gul1summary1  > working/gul1summary1eltcalc
eltcalc < working/gul1summary1eltcalc > work/gul_1_eltcalc_1
summarycalc -g  -1 working/gul1summary1 < working/gul1
eve 1 1 | getmodel | gulcalc -S100  -L100 -c working/gul1 
cat work/gul_1_eltcalc_1 > output/gul_1_eltcalc.csv
