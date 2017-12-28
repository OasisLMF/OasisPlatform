#!/bin/bash

rm -R -f output/*
rm -R -f fifo/*
rm -R -f work/*

mkdir work/kat
mkfifo fifo/gul_P1

mkfifo fifo/gul_S1_summary_P1
mkfifo fifo/gul_S1_summaryeltcalc_P1
mkfifo fifo/gul_S1_eltcalc_P1

mkfifo fifo/gul_P2

mkfifo fifo/gul_S1_summary_P2
mkfifo fifo/gul_S1_summaryeltcalc_P2
mkfifo fifo/gul_S1_eltcalc_P2



# --- Do insured loss computes ---


# --- Do ground up loss  computes ---

eltcalc < fifo/gul_S1_summaryeltcalc_P1 > work/kat/gul_S1_eltcalc_P1 & pid1=$!

eltcalc -s < fifo/gul_S1_summaryeltcalc_P2 > work/kat/gul_S1_eltcalc_P2 & pid2=$!

tee < fifo/gul_S1_summary_P1 fifo/gul_S1_summaryeltcalc_P1  > /dev/null & pid3=$!
tee < fifo/gul_S1_summary_P2 fifo/gul_S1_summaryeltcalc_P2  > /dev/null & pid4=$!
summarycalc -g -1 fifo/gul_S1_summary_P1  < fifo/gul_P1 &
summarycalc -g -1 fifo/gul_S1_summary_P2  < fifo/gul_P2 &

eve 1 2 | getmodel | gulcalc -S100 -L100 -r -c - > fifo/gul_P1  &
eve 2 2 | getmodel | gulcalc -S100 -L100 -r -c - > fifo/gul_P2  &

wait $pid1 $pid2 $pid3 $pid4 


# --- Do insured loss kats ---


# --- Do ground up loss kats ---

kat work/kat/gul_S1_eltcalc_P1 work/kat/gul_S1_eltcalc_P2 > output/gul_S1_eltcalc.csv & kpid1=$!
wait $kpid1 


rm fifo/gul_P1

rm fifo/gul_S1_summary_P1
rm fifo/gul_S1_summaryeltcalc_P1
rm fifo/gul_S1_eltcalc_P1

rm fifo/gul_P2

rm fifo/gul_S1_summary_P2
rm fifo/gul_S1_summaryeltcalc_P2
rm fifo/gul_S1_eltcalc_P2

rm -rf work/kat

