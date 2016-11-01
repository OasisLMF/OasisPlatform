#!/bin/bash

mkfifo fifo/il_P1

mkfifo fifo/il_S1_summary_P1
mkfifo fifo/il_S1_summaryeltcalc_P1
mkfifo fifo/il_S1_eltcalc_P1

mkfifo fifo/il_P2

mkfifo fifo/il_S1_summary_P2
mkfifo fifo/il_S1_summaryeltcalc_P2
mkfifo fifo/il_S1_eltcalc_P2

mkfifo fifo/il_P3

mkfifo fifo/il_S1_summary_P3
mkfifo fifo/il_S1_summaryeltcalc_P3
mkfifo fifo/il_S1_eltcalc_P3

mkfifo fifo/il_P4

mkfifo fifo/il_S1_summary_P4
mkfifo fifo/il_S1_summaryeltcalc_P4
mkfifo fifo/il_S1_eltcalc_P4

mkfifo fifo/il_P5

mkfifo fifo/il_S1_summary_P5
mkfifo fifo/il_S1_summaryeltcalc_P5
mkfifo fifo/il_S1_eltcalc_P5

mkfifo fifo/il_P6

mkfifo fifo/il_S1_summary_P6
mkfifo fifo/il_S1_summaryeltcalc_P6
mkfifo fifo/il_S1_eltcalc_P6

mkfifo fifo/il_P7

mkfifo fifo/il_S1_summary_P7
mkfifo fifo/il_S1_summaryeltcalc_P7
mkfifo fifo/il_S1_eltcalc_P7

mkfifo fifo/il_P8

mkfifo fifo/il_S1_summary_P8
mkfifo fifo/il_S1_summaryeltcalc_P8
mkfifo fifo/il_S1_eltcalc_P8

mkfifo fifo/il_P9

mkfifo fifo/il_S1_summary_P9
mkfifo fifo/il_S1_summaryeltcalc_P9
mkfifo fifo/il_S1_eltcalc_P9

mkfifo fifo/il_P10

mkfifo fifo/il_S1_summary_P10
mkfifo fifo/il_S1_summaryeltcalc_P10
mkfifo fifo/il_S1_eltcalc_P10

mkfifo fifo/il_P11

mkfifo fifo/il_S1_summary_P11
mkfifo fifo/il_S1_summaryeltcalc_P11
mkfifo fifo/il_S1_eltcalc_P11

mkfifo fifo/il_P12

mkfifo fifo/il_S1_summary_P12
mkfifo fifo/il_S1_summaryeltcalc_P12
mkfifo fifo/il_S1_eltcalc_P12

mkfifo fifo/il_P13

mkfifo fifo/il_S1_summary_P13
mkfifo fifo/il_S1_summaryeltcalc_P13
mkfifo fifo/il_S1_eltcalc_P13

mkfifo fifo/il_P14

mkfifo fifo/il_S1_summary_P14
mkfifo fifo/il_S1_summaryeltcalc_P14
mkfifo fifo/il_S1_eltcalc_P14

mkfifo fifo/il_P15

mkfifo fifo/il_S1_summary_P15
mkfifo fifo/il_S1_summaryeltcalc_P15
mkfifo fifo/il_S1_eltcalc_P15

mkfifo fifo/il_P16

mkfifo fifo/il_S1_summary_P16
mkfifo fifo/il_S1_summaryeltcalc_P16
mkfifo fifo/il_S1_eltcalc_P16

mkfifo fifo/il_P17

mkfifo fifo/il_S1_summary_P17
mkfifo fifo/il_S1_summaryeltcalc_P17
mkfifo fifo/il_S1_eltcalc_P17

mkfifo fifo/il_P18

mkfifo fifo/il_S1_summary_P18
mkfifo fifo/il_S1_summaryeltcalc_P18
mkfifo fifo/il_S1_eltcalc_P18

mkfifo fifo/il_P19

mkfifo fifo/il_S1_summary_P19
mkfifo fifo/il_S1_summaryeltcalc_P19
mkfifo fifo/il_S1_eltcalc_P19

mkfifo fifo/il_P20

mkfifo fifo/il_S1_summary_P20
mkfifo fifo/il_S1_summaryeltcalc_P20
mkfifo fifo/il_S1_eltcalc_P20


# --- Do insured loss kats ---

kat fifo/il_S1_eltcalc_P1 fifo/il_S1_eltcalc_P2 fifo/il_S1_eltcalc_P3 fifo/il_S1_eltcalc_P4 fifo/il_S1_eltcalc_P5 fifo/il_S1_eltcalc_P6 fifo/il_S1_eltcalc_P7 fifo/il_S1_eltcalc_P8 fifo/il_S1_eltcalc_P9 fifo/il_S1_eltcalc_P10 fifo/il_S1_eltcalc_P11 fifo/il_S1_eltcalc_P12 fifo/il_S1_eltcalc_P13 fifo/il_S1_eltcalc_P14 fifo/il_S1_eltcalc_P15 fifo/il_S1_eltcalc_P16 fifo/il_S1_eltcalc_P17 fifo/il_S1_eltcalc_P18 fifo/il_S1_eltcalc_P19 fifo/il_S1_eltcalc_P20 > output/il_S1_eltcalc.csv & pid1=$!

# --- Do ground up loss kats ---


sleep 2

# --- Do insured loss computes ---

eltcalc < fifo/il_S1_summaryeltcalc_P1 > fifo/il_S1_eltcalc_P1 &

tee < fifo/il_S1_summary_P1 fifo/il_S1_summaryeltcalc_P1  > /dev/null & pid2=$!
summarycalc -f -1 fifo/il_S1_summary_P1  < fifo/il_P1 &
eltcalc < fifo/il_S1_summaryeltcalc_P2 > fifo/il_S1_eltcalc_P2 &

tee < fifo/il_S1_summary_P2 fifo/il_S1_summaryeltcalc_P2  > /dev/null & pid3=$!
summarycalc -f -1 fifo/il_S1_summary_P2  < fifo/il_P2 &
eltcalc < fifo/il_S1_summaryeltcalc_P3 > fifo/il_S1_eltcalc_P3 &

tee < fifo/il_S1_summary_P3 fifo/il_S1_summaryeltcalc_P3  > /dev/null & pid4=$!
summarycalc -f -1 fifo/il_S1_summary_P3  < fifo/il_P3 &
eltcalc < fifo/il_S1_summaryeltcalc_P4 > fifo/il_S1_eltcalc_P4 &

tee < fifo/il_S1_summary_P4 fifo/il_S1_summaryeltcalc_P4  > /dev/null & pid5=$!
summarycalc -f -1 fifo/il_S1_summary_P4  < fifo/il_P4 &
eltcalc < fifo/il_S1_summaryeltcalc_P5 > fifo/il_S1_eltcalc_P5 &

tee < fifo/il_S1_summary_P5 fifo/il_S1_summaryeltcalc_P5  > /dev/null & pid6=$!
summarycalc -f -1 fifo/il_S1_summary_P5  < fifo/il_P5 &
eltcalc < fifo/il_S1_summaryeltcalc_P6 > fifo/il_S1_eltcalc_P6 &

tee < fifo/il_S1_summary_P6 fifo/il_S1_summaryeltcalc_P6  > /dev/null & pid7=$!
summarycalc -f -1 fifo/il_S1_summary_P6  < fifo/il_P6 &
eltcalc < fifo/il_S1_summaryeltcalc_P7 > fifo/il_S1_eltcalc_P7 &

tee < fifo/il_S1_summary_P7 fifo/il_S1_summaryeltcalc_P7  > /dev/null & pid8=$!
summarycalc -f -1 fifo/il_S1_summary_P7  < fifo/il_P7 &
eltcalc < fifo/il_S1_summaryeltcalc_P8 > fifo/il_S1_eltcalc_P8 &

tee < fifo/il_S1_summary_P8 fifo/il_S1_summaryeltcalc_P8  > /dev/null & pid9=$!
summarycalc -f -1 fifo/il_S1_summary_P8  < fifo/il_P8 &
eltcalc < fifo/il_S1_summaryeltcalc_P9 > fifo/il_S1_eltcalc_P9 &

tee < fifo/il_S1_summary_P9 fifo/il_S1_summaryeltcalc_P9  > /dev/null & pid10=$!
summarycalc -f -1 fifo/il_S1_summary_P9  < fifo/il_P9 &
eltcalc < fifo/il_S1_summaryeltcalc_P10 > fifo/il_S1_eltcalc_P10 &

tee < fifo/il_S1_summary_P10 fifo/il_S1_summaryeltcalc_P10  > /dev/null & pid11=$!
summarycalc -f -1 fifo/il_S1_summary_P10  < fifo/il_P10 &
eltcalc < fifo/il_S1_summaryeltcalc_P11 > fifo/il_S1_eltcalc_P11 &

tee < fifo/il_S1_summary_P11 fifo/il_S1_summaryeltcalc_P11  > /dev/null & pid12=$!
summarycalc -f -1 fifo/il_S1_summary_P11  < fifo/il_P11 &
eltcalc < fifo/il_S1_summaryeltcalc_P12 > fifo/il_S1_eltcalc_P12 &

tee < fifo/il_S1_summary_P12 fifo/il_S1_summaryeltcalc_P12  > /dev/null & pid13=$!
summarycalc -f -1 fifo/il_S1_summary_P12  < fifo/il_P12 &
eltcalc < fifo/il_S1_summaryeltcalc_P13 > fifo/il_S1_eltcalc_P13 &

tee < fifo/il_S1_summary_P13 fifo/il_S1_summaryeltcalc_P13  > /dev/null & pid14=$!
summarycalc -f -1 fifo/il_S1_summary_P13  < fifo/il_P13 &
eltcalc < fifo/il_S1_summaryeltcalc_P14 > fifo/il_S1_eltcalc_P14 &

tee < fifo/il_S1_summary_P14 fifo/il_S1_summaryeltcalc_P14  > /dev/null & pid15=$!
summarycalc -f -1 fifo/il_S1_summary_P14  < fifo/il_P14 &
eltcalc < fifo/il_S1_summaryeltcalc_P15 > fifo/il_S1_eltcalc_P15 &

tee < fifo/il_S1_summary_P15 fifo/il_S1_summaryeltcalc_P15  > /dev/null & pid16=$!
summarycalc -f -1 fifo/il_S1_summary_P15  < fifo/il_P15 &
eltcalc < fifo/il_S1_summaryeltcalc_P16 > fifo/il_S1_eltcalc_P16 &

tee < fifo/il_S1_summary_P16 fifo/il_S1_summaryeltcalc_P16  > /dev/null & pid17=$!
summarycalc -f -1 fifo/il_S1_summary_P16  < fifo/il_P16 &
eltcalc < fifo/il_S1_summaryeltcalc_P17 > fifo/il_S1_eltcalc_P17 &

tee < fifo/il_S1_summary_P17 fifo/il_S1_summaryeltcalc_P17  > /dev/null & pid18=$!
summarycalc -f -1 fifo/il_S1_summary_P17  < fifo/il_P17 &
eltcalc < fifo/il_S1_summaryeltcalc_P18 > fifo/il_S1_eltcalc_P18 &

tee < fifo/il_S1_summary_P18 fifo/il_S1_summaryeltcalc_P18  > /dev/null & pid19=$!
summarycalc -f -1 fifo/il_S1_summary_P18  < fifo/il_P18 &
eltcalc < fifo/il_S1_summaryeltcalc_P19 > fifo/il_S1_eltcalc_P19 &

tee < fifo/il_S1_summary_P19 fifo/il_S1_summaryeltcalc_P19  > /dev/null & pid20=$!
summarycalc -f -1 fifo/il_S1_summary_P19  < fifo/il_P19 &
eltcalc < fifo/il_S1_summaryeltcalc_P20 > fifo/il_S1_eltcalc_P20 &

tee < fifo/il_S1_summary_P20 fifo/il_S1_summaryeltcalc_P20  > /dev/null & pid21=$!
summarycalc -f -1 fifo/il_S1_summary_P20  < fifo/il_P20 &

# --- Do ground up loss  computes ---


eve 1 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P1  &
eve 2 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P2  &
eve 3 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P3  &
eve 4 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P4  &
eve 5 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P5  &
eve 6 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P6  &
eve 7 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P7  &
eve 8 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P8  &
eve 9 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P9  &
eve 10 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P10  &
eve 11 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P11  &
eve 12 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P12  &
eve 13 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P13  &
eve 14 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P14  &
eve 15 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P15  &
eve 16 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P16  &
eve 17 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P17  &
eve 18 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P18  &
eve 19 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P19  &
eve 20 20 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P20  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8 $pid9 $pid10 $pid11 $pid12 $pid13 $pid14 $pid15 $pid16 $pid17 $pid18 $pid19 $pid20 $pid21 



rm fifo/il_P1

rm fifo/il_S1_summary_P1
rm fifo/il_S1_summaryeltcalc_P1
rm fifo/il_S1_eltcalc_P1

rm fifo/il_P2

rm fifo/il_S1_summary_P2
rm fifo/il_S1_summaryeltcalc_P2
rm fifo/il_S1_eltcalc_P2

rm fifo/il_P3

rm fifo/il_S1_summary_P3
rm fifo/il_S1_summaryeltcalc_P3
rm fifo/il_S1_eltcalc_P3

rm fifo/il_P4

rm fifo/il_S1_summary_P4
rm fifo/il_S1_summaryeltcalc_P4
rm fifo/il_S1_eltcalc_P4

rm fifo/il_P5

rm fifo/il_S1_summary_P5
rm fifo/il_S1_summaryeltcalc_P5
rm fifo/il_S1_eltcalc_P5

rm fifo/il_P6

rm fifo/il_S1_summary_P6
rm fifo/il_S1_summaryeltcalc_P6
rm fifo/il_S1_eltcalc_P6

rm fifo/il_P7

rm fifo/il_S1_summary_P7
rm fifo/il_S1_summaryeltcalc_P7
rm fifo/il_S1_eltcalc_P7

rm fifo/il_P8

rm fifo/il_S1_summary_P8
rm fifo/il_S1_summaryeltcalc_P8
rm fifo/il_S1_eltcalc_P8

rm fifo/il_P9

rm fifo/il_S1_summary_P9
rm fifo/il_S1_summaryeltcalc_P9
rm fifo/il_S1_eltcalc_P9

rm fifo/il_P10

rm fifo/il_S1_summary_P10
rm fifo/il_S1_summaryeltcalc_P10
rm fifo/il_S1_eltcalc_P10

rm fifo/il_P11

rm fifo/il_S1_summary_P11
rm fifo/il_S1_summaryeltcalc_P11
rm fifo/il_S1_eltcalc_P11

rm fifo/il_P12

rm fifo/il_S1_summary_P12
rm fifo/il_S1_summaryeltcalc_P12
rm fifo/il_S1_eltcalc_P12

rm fifo/il_P13

rm fifo/il_S1_summary_P13
rm fifo/il_S1_summaryeltcalc_P13
rm fifo/il_S1_eltcalc_P13

rm fifo/il_P14

rm fifo/il_S1_summary_P14
rm fifo/il_S1_summaryeltcalc_P14
rm fifo/il_S1_eltcalc_P14

rm fifo/il_P15

rm fifo/il_S1_summary_P15
rm fifo/il_S1_summaryeltcalc_P15
rm fifo/il_S1_eltcalc_P15

rm fifo/il_P16

rm fifo/il_S1_summary_P16
rm fifo/il_S1_summaryeltcalc_P16
rm fifo/il_S1_eltcalc_P16

rm fifo/il_P17

rm fifo/il_S1_summary_P17
rm fifo/il_S1_summaryeltcalc_P17
rm fifo/il_S1_eltcalc_P17

rm fifo/il_P18

rm fifo/il_S1_summary_P18
rm fifo/il_S1_summaryeltcalc_P18
rm fifo/il_S1_eltcalc_P18

rm fifo/il_P19

rm fifo/il_S1_summary_P19
rm fifo/il_S1_summaryeltcalc_P19
rm fifo/il_S1_eltcalc_P19

rm fifo/il_P20

rm fifo/il_S1_summary_P20
rm fifo/il_S1_summaryeltcalc_P20
rm fifo/il_S1_eltcalc_P20

