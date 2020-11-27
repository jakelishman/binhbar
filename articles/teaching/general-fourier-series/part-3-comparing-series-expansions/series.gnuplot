set terminal svg enhanced size 350,210 font ",13"

load 'palette/viridis.pal'
set style line 1 lw 3 lc rgb 000000 dt (8, 8)
set style line 2 lw 2 lt palette frac 0.1
set style line 3 lw 2 lt palette frac 0.5 dt (20, 3)
set style line 4 lw 2 lt palette frac 0.9
unset colorbox

set encoding utf8
set minussign

array stems[3] = ['polynomial', 'logistic', 'lorentzian']
array _ytics[3] = [0.2, 0.5, 0.5]
array _mytics[3] = [4, 5, 5]
array orders[2] = ['low', 'high']
array series[3] = ['Taylor', 'Legendre', 'Fourier']

set lmargin 4
set tmargin 0.1
set rmargin 0.2
set bmargin 1

set xtics scale 1,0.5 offset 0,0.4
set mxtics 5


do for [i=1:3] {
    df = stems[i] . '.dat'
    # Reset yrange before stats to avoid masking data.
    unset yrange
    stats df using 2 name stems[i] nooutput
    eval('yspl = '.stems[i].'_max - '.stems[i].'_min')
    set xrange [-1 : 1]
    eval('set yrange ['.stems[i].'_min - 0.1*yspl : '.stems[i].'_max + 0.1*yspl]')
    set ytics _ytics[i] scale 1,0.5 offset 0.2,0
    set mytics _mytics[i]

    set key spacing 0.85 samplen 2
    if (i == 2) {
        set key at 0.6, 0.425
    } else {
        set key at graph 0.975, graph 0.945
    }

    do for [j=1:2] {
        set output (stems[i].'-'.orders[j].'.svg')
        plot df u 1:2 with lines ls 1 title 'Exact', \
             for [k=1:3] df using 1:(column((j-1)*3+k+2)) with lines ls (k+1) title series[k]
    }
}
