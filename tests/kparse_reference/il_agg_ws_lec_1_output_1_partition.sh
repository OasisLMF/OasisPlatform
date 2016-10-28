#!/bin/bash

mkfifo fifo/il_P1

mkfifo fifo/il_S1_summary_P1

mkdir work/il_S1_summaryleccalc

# --- Do insured loss kats ---


# --- Do ground up loss kats ---



# --- Do insured loss computes ---

aalcalc < fifo/il_S1_summaryaalcalc_P1 > work/il_S1_aalcalc/P1.bin & pid1=$!

tee < fifo/il_S1_summary_P1 work/il_S1_summaryleccalc/P1.bin  > /dev/null & pid1=$!
summarycalc -f -1 fifo/il_S1_summary_P1  < fifo/il_P1 &

# --- Do ground up loss  computes ---


eve 1 1 | getmodel | gulcalc -S100 -L100 -r -i - | fmcalc > fifo/il_P1  &

wait $pid1 


leccalc -r -Kil_S1_summaryleccalc -W output/il_S1_leccalc_wheatsheaf_aep.csv  &  lpid1=$!
wait $lpid1 


rm fifo/il_P1

rm fifo/il_S1_summary_P1

rm work/il_S1_summaryleccalc/*
rmdir work/il_S1_summaryleccalc
