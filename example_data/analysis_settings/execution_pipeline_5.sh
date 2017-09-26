
mkdir ./work
mkdir ./outputs 
mkdir ./work/if_summary1
mkdir ./work/if_summary2

mkfifo ./work/1/il
mkfifo ./work/1/il_summary1
mkfifo ./work/1/il_summary1_output1
mkfifo ./work/1/il_summary2
mkfifo ./work/1/il_summary2_output1

mkfifo ./work/2/il
mkfifo ./work/2/il_summary1
mkfifo ./work/2/il_summary1_output1
mkfifo ./work/2/il_summary2
mkfifo ./work/2/il_summary2_output1

mkfifo ./work/3/il
mkfifo ./work/3/il_summary1
mkfifo ./work/3/il_summary1_output1
mkfifo ./work/3/il_summary2
mkfifo ./work/3/il_summary2_output1

mkfifo ./work/4/il
mkfifo ./work/4/il_summary1
mkfifo ./work/4/il_summary1_output1
mkfifo ./work/4/il_summary2
mkfifo ./work/4/il_summary2_output1

mkfifo ./work/5/il
mkfifo ./work/5/il_summary1
mkfifo ./work/5/il_summary1_output1
mkfifo ./work/5/il_summary2
mkfifo ./work/5/il_summary2_output1

eltcalc < ./work/1/il_summary1_output1 > ./work/1/il_1_elt.csv &
eltcalc < ./work/2/il_summary1_output1 > ./work/2/il_1_elt.csv &
eltcalc < ./work/3/il_summary1_output1 > ./work/3/il_1_elt.csv &
eltcalc < ./work/4/il_summary1_output1 > ./work/4/il_1_elt.csv &
eltcalc < ./work/5/il_summary1_output1 > ./work/5/il_1_elt.csv &

eltcalc < ./work/1/il_summary2_output1 > ./work/1/il_2_elt.csv &
eltcalc < ./work/2/il_summary2_output1 > ./work/2/il_2_elt.csv &
eltcalc < ./work/3/il_summary2_output1 > ./work/3/il_2_elt.csv &
eltcalc < ./work/4/il_summary2_output1 > ./work/4/il_2_elt.csv &
eltcalc < ./work/5/il_summary2_output1 > ./work/5/il_2_elt.csv &

tee < ./work/1/il_summary1 ./work/1/il_summary1_output1  > ./work/il_summary1/p1.bin &
tee < ./work/2/il_summary1 ./work/2/il_summary1_output1  > ./work/il_summary1/p2.bin &
tee < ./work/3/il_summary1 ./work/3/il_summary1_output1  > ./work/il_summary1/p3.bin &
tee < ./work/4/il_summary1 ./work/4/il_summary1_output1  > ./work/il_summary1/p4.bin &
tee < ./work/5/il_summary1 ./work/5/il_summary1_output1  > ./work/il_summary1/p5.bin &

tee < ./work/1/il_summary2 ./work/1/il_summary2_output1  > ./work/il_summary2/p1.bin &
tee < ./work/2/il_summary2 ./work/2/il_summary2_output1  > ./work/il_summary2/p2.bin &
tee < ./work/3/il_summary2 ./work/3/il_summary2_output1  > ./work/il_summary2/p3.bin &
tee < ./work/4/il_summary2 ./work/4/il_summary2_output1  > ./work/il_summary2/p4.bin &
tee < ./work/5/il_summary2 ./work/5/il_summary2_output1  > ./work/il_summary2/p5.bin &

summarycalc -f -1 ./work/1/il_summary1 -2 ./work/1/il_summary2 < ./work/1/il &
summarycalc -f -1 ./work/2/il_summary1 -2 ./work/2/il_summary2 < ./work/2/il &
summarycalc -f -1 ./work/3/il_summary1 -2 ./work/3/il_summary2 < ./work/3/il &
summarycalc -f -1 ./work/4/il_summary1 -2 ./work/4/il_summary2 < ./work/4/il &
summarycalc -f -1 ./work/5/il_summary1 -2 ./work/5/il_summary2 < ./work/5/il &

eve 1 5 | getmodel | gulcalc -S100 -R1000000 -i - | fmcalc | ./work/1/il 
eve 2 5 | getmodel | gulcalc -S100 -R1000000 -i - | fmcalc | ./work/2/il
eve 3 5 | getmodel | gulcalc -S100 -R1000000 -i - | fmcalc | ./work/3/il
eve 4 5 | getmodel | gulcalc -S100 -R1000000 -i - | fmcalc | ./work/4/il
eve 5 5 | getmodel | gulcalc -S100 -R1000000 -i - | fmcalc | ./work/5/il

cat ./work/1/il_1_elt.csv ./work/2/il_1_elt.csv ./work/3/il_1_elt.csv ./work/4/il_1_elt.csv ./work/5/il_1_elt.csv > ./outputs/il_1_elt.csv
cat ./work/1/il_2_elt.csv ./work/2/il_2_elt.csv ./work/3/il_2_elt.csv ./work/4/il_2_elt.csv ./work/5/il_2_elt.csv > ./outputs/il_2_elt.csv

leccalc -P 1000000 -Kil_summary1 -F ./outputs/il_1_aep.csv -f ./outputs/il_1_oep.csv & 
leccalc -P 1000000 -Kil_summary2 -F ./outputs/il_2_aep.csv -f ./outputs/il_2_oep.csv & 
