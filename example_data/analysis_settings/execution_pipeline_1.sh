
mkdir ./work
mkdir ./outputs 

mkfifo ./work/gul
mkfifo ./work/gul_summary1
mkfifo ./work/gul_output1

eltcalc < ./work/gul_output1 > ./outputs/gul_1_elt.csv &
tee < ./work/gul_summary1 ./work/gul_output1 > /dev/null &
summarycalc -g -1 ./work/gul_summary1 < ./work/gul &
eve 1 1 | getmodel | gulcalc -S100 -R1000000 -c ./work/gul
