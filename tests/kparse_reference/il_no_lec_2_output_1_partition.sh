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


# --- Do insured loss kats ---

kat fifo/il_S1_eltcalc_P1 > output/il_S1_eltcalc.csv & pid367=$!
kat fifo/il_S1_pltcalc_P1 > output/il_S1_pltcalc.csv & pid368=$!
kat fifo/il_S1_summarycalc_P1 > output/il_S1_summarycalc.csv & pid369=$!
kat fifo/il_S2_eltcalc_P1 > output/il_S2_eltcalc.csv & pid370=$!
kat fifo/il_S2_pltcalc_P1 > output/il_S2_pltcalc.csv & pid371=$!
kat fifo/il_S2_summarycalc_P1 > output/il_S2_summarycalc.csv & pid372=$!

# --- Do ground up loss kats ---


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

tee < fifo/il_S1_summary_P1 fifo/il_S1_summaryeltcalc_P1 fifo/il_S1_summarypltcalc_P1 fifo/il_S1_summarysummarycalc_P1 fifo/il_S1_summaryaalcalc_P1  > /dev/null & pid375=$!
tee < fifo/il_S2_summary_P1 fifo/il_S2_summaryeltcalc_P1 fifo/il_S2_summarypltcalc_P1 fifo/il_S2_summarysummarycalc_P1 fifo/il_S2_summaryaalcalc_P1  > /dev/null & pid376=$!
summarycalc -f -1 fifo/il_S1_summary_P1 -2 fifo/il_S2_summary_P1  < fifo/il_P1 &

# --- Do ground up loss  computes ---


eve 1 1 | getmodel | gulcalc -S0 -L0 -r -c fifo/gul_P1 -i - | fmcalc > fifo/il_P1  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8 $pid9 $pid10 $pid11 $pid12 $pid13 $pid14 $pid15 $pid16 $pid17 $pid18 $pid19 $pid20 $pid21 $pid22 $pid23 $pid24 $pid25 $pid26 $pid27 $pid28 $pid29 $pid30 $pid31 $pid32 $pid33 $pid34 $pid35 $pid36 $pid37 $pid38 $pid39 $pid40 $pid41 $pid42 $pid43 $pid44 $pid45 $pid46 $pid47 $pid48 $pid49 $pid50 $pid51 $pid52 $pid53 $pid54 $pid55 $pid56 $pid57 $pid58 $pid59 $pid60 $pid61 $pid62 $pid63 $pid64 $pid65 $pid66 $pid67 $pid68 $pid69 $pid70 $pid71 $pid72 $pid73 $pid74 $pid75 $pid76 $pid77 $pid78 $pid79 $pid80 $pid81 $pid82 $pid83 $pid84 $pid85 $pid86 $pid87 $pid88 $pid89 $pid90 $pid91 $pid92 $pid93 $pid94 $pid95 $pid96 $pid97 $pid98 $pid99 $pid100 $pid101 $pid102 $pid103 $pid104 $pid105 $pid106 $pid107 $pid108 $pid109 $pid110 $pid111 $pid112 $pid113 $pid114 $pid115 $pid116 $pid117 $pid118 $pid119 $pid120 $pid121 $pid122 $pid123 $pid124 $pid125 $pid126 $pid127 $pid128 $pid129 $pid130 $pid131 $pid132 $pid133 $pid134 $pid135 $pid136 $pid137 $pid138 $pid139 $pid140 $pid141 $pid142 $pid143 $pid144 $pid145 $pid146 $pid147 $pid148 $pid149 $pid150 $pid151 $pid152 $pid153 $pid154 $pid155 $pid156 $pid157 $pid158 $pid159 $pid160 $pid161 $pid162 $pid163 $pid164 $pid165 $pid166 $pid167 $pid168 $pid169 $pid170 $pid171 $pid172 $pid173 $pid174 $pid175 $pid176 $pid177 $pid178 $pid179 $pid180 $pid181 $pid182 $pid183 $pid184 $pid185 $pid186 $pid187 $pid188 $pid189 $pid190 $pid191 $pid192 $pid193 $pid194 $pid195 $pid196 $pid197 $pid198 $pid199 $pid200 $pid201 $pid202 $pid203 $pid204 $pid205 $pid206 $pid207 $pid208 $pid209 $pid210 $pid211 $pid212 $pid213 $pid214 $pid215 $pid216 $pid217 $pid218 $pid219 $pid220 $pid221 $pid222 $pid223 $pid224 $pid225 $pid226 $pid227 $pid228 $pid229 $pid230 $pid231 $pid232 $pid233 $pid234 $pid235 $pid236 $pid237 $pid238 $pid239 $pid240 $pid241 $pid242 $pid243 $pid244 $pid245 $pid246 $pid247 $pid248 $pid249 $pid250 $pid251 $pid252 $pid253 $pid254 $pid255 $pid256 $pid257 $pid258 $pid259 $pid260 $pid261 $pid262 $pid263 $pid264 $pid265 $pid266 $pid267 $pid268 $pid269 $pid270 $pid271 $pid272 $pid273 $pid274 $pid275 $pid276 $pid277 $pid278 $pid279 $pid280 $pid281 $pid282 $pid283 $pid284 $pid285 $pid286 $pid287 $pid288 $pid289 $pid290 $pid291 $pid292 $pid293 $pid294 $pid295 $pid296 $pid297 $pid298 $pid299 $pid300 $pid301 $pid302 $pid303 $pid304 $pid305 $pid306 $pid307 $pid308 $pid309 $pid310 $pid311 $pid312 $pid313 $pid314 $pid315 $pid316 $pid317 $pid318 $pid319 $pid320 $pid321 $pid322 $pid323 $pid324 $pid325 $pid326 $pid327 $pid328 $pid329 $pid330 $pid331 $pid332 $pid333 $pid334 $pid335 $pid336 $pid337 $pid338 $pid339 $pid340 $pid341 $pid342 $pid343 $pid344 $pid345 $pid346 $pid347 $pid348 $pid349 $pid350 $pid351 $pid352 $pid353 $pid354 $pid355 $pid356 $pid357 $pid358 $pid359 $pid360 $pid361 $pid362 $pid363 $pid364 $pid365 $pid366 $pid367 $pid368 $pid369 $pid370 $pid371 $pid372 $pid373 $pid374 $pid375 $pid376 


aalsummary -Kil_S1_aalcalc > output/il_S1_aalcalc.csv & apid51=$!
aalsummary -Kil_S2_aalcalc > output/il_S2_aalcalc.csv & apid52=$!
wait $apid1 $apid2 $apid3 $apid4 $apid5 $apid6 $apid7 $apid8 $apid9 $apid10 $apid11 $apid12 $apid13 $apid14 $apid15 $apid16 $apid17 $apid18 $apid19 $apid20 $apid21 $apid22 $apid23 $apid24 $apid25 $apid26 $apid27 $apid28 $apid29 $apid30 $apid31 $apid32 $apid33 $apid34 $apid35 $apid36 $apid37 $apid38 $apid39 $apid40 $apid41 $apid42 $apid43 $apid44 $apid45 $apid46 $apid47 $apid48 $apid49 $apid50 $apid51 $apid52 

wait $lpid1 $lpid2 $lpid3 $lpid4 $lpid5 $lpid6 $lpid7 $lpid8 $lpid9 $lpid10 $lpid11 $lpid12 $lpid13 $lpid14 $lpid15 $lpid16 $lpid17 $lpid18 $lpid19 $lpid20 $lpid21 $lpid22 $lpid23 $lpid24 $lpid25 $lpid26 $lpid27 $lpid28 


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

