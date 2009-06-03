# (C) Copyright 2008 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Render chart using gnuplot >= 4.2

$Id$
"""

import os
import re
from commands import getstatusoutput
from ReportRenderRst import rst_title
from ReportRenderHtmlBase import RenderHtmlBase
from datetime import datetime


def gnuplot(script_path):
    """Execute a gnuplot script."""
    path = os.path.dirname(os.path.abspath(script_path))
    cmd = 'cd ' + path + '; gnuplot ' + os.path.abspath(script_path)
    ret, output = getstatusoutput(cmd)
    if ret != 0:
        raise RuntimeError("Failed to run gnuplot cmd: " + cmd +
                           "\n" + str(output))

class RenderHtmlGnuPlot(RenderHtmlBase):
    """Render stats in html using gnuplot

    Simply render stuff in ReST than ask docutils to build an html doc.
    """
    chart_size = (480, 480)
    #big_chart_size = (640, 480)
    ticpattern = re.compile('(\:\d+)\ ')

    def getChartSizeTmp(self, cvus):
        """Override for gnuplot format"""
        size = RenderHtmlBase.getChartSize(self, cvus)
        return str(size[0]) + ',' + str(size[1])

    def getXRange(self):
        """Return the max CVUs range."""
        maxCycle = self.config['cycles'].split(',')[-1]
        maxCycle = str(maxCycle[:-1].strip())
        if maxCycle.startswith("["):
            maxCycle = maxCycle[1:]
        return "[0:" + maxCycle + "]"

    def useXTicLabels(self):
        """Guess if we need to use labels for x axis or number."""
        cycles = self.config['cycles'][1:-1].split(',')
        if len(cycles) <= 1:
            # single cycle
            return True
        if len(cycles) != len(set(cycles)):
            # duplicates cycles
            return True
        cycles = [int(i) for i in cycles]
        for i, v in enumerate(cycles[1:]):
            # unordered cycles
            if cycles[i] > v:
                return True
        return False

    def fixXLabels(self, lines):
        """Fix gnuplot script if CUs are not ordered."""
        if not self.useXTicLabels():
            return lines
        # remove xrange line
        out = lines.replace('set xrange', '#set xrange')
        # rewrite plot using xticlabels
        out = out.replace(' 1:', ' :')
        out = self.ticpattern.sub(r'\1:xticlabels(1) ', out)
        return out

    def createTestChart(self):
        """Create the test chart."""
        image_path = str(os.path.join(self.report_dir, 'tests.png'))
        gplot_path = str(os.path.join(self.report_dir, 'tests.gplot'))
        data_path = str(os.path.join(self.report_dir, 'tests.data'))
        stats = self.stats
        # data
        lines = ["CUs STPS ERROR"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle].has_key('test'):
                continue
            values = []
            test = stats[cycle]['test']
            values.append(str(test.cvus))
            cvus.append(str(test.cvus))
            values.append(str(test.tps))
            error = test.error_percent
            if error:
                has_error = True
            values.append(str(error))
            lines.append(' '.join(values))
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = ['set output "' + image_path +'"']
        lines.append('set title "Successful Tests Per Second"')
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        lines.append('set xlabel "Concurrent Users"')
        lines.append('set ylabel "Test/s"')
        lines.append('set grid back')
        lines.append('set xrange ' + self.getXRange())

        if not has_error:
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "STPS"' % data_path)
        else:
            lines.append('set format x ""')
            lines.append('set multiplot')
            lines.append('unset title')
            lines.append('unset xlabel')
            lines.append('set size 1, 0.7')
            lines.append('set origin 0, 0.3')
            lines.append('set lmargin 5')
            lines.append('set bmargin 0')
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "STPS"' % data_path)
            lines.append('set format x "% g"')
            lines.append('set bmargin 3')
            lines.append('set autoscale y')
            lines.append('set style fill solid .25')
            lines.append('set size 1.0, 0.3')
            lines.append('set ytics 20')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set ylabel "% errors"')
            lines.append('set origin 0.0, 0.0')
            lines.append('set yrange [0:100]')
            lines.append('plot "%s" u 1:3 w linespoints lt 1 lw 2 t "%% Errors"' % data_path)
            lines.append('unset multiplot')
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)
        return

    def appendDelays(self, delay, delay_low, delay_high, stats):
        """ Show percentiles or min, avg and max in chart. """
        if self.options.with_percentiles:
            delay.append(stats.percentiles.perc50)
            delay_low.append(stats.percentiles.perc10)
            delay_high.append(stats.percentiles.perc90)
        else:
            delay.append(stats.avg)
            delay_low.append(stats.min)
            delay_high.append(stats.max)


    def createPageChart(self):
        """Create the page chart."""
        image_path = str(os.path.join(self.report_dir, 'pages_spps.png'))
        image2_path = str(os.path.join(self.report_dir, 'pages.png'))
        gplot_path = str(os.path.join(self.report_dir, 'pages.gplot'))
        data_path = str(os.path.join(self.report_dir, 'pages.data'))
        stats = self.stats
        # data
        lines = ["CUs SPPS ERROR MIN AVG MAX P10 P50 P90 P95"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle].has_key('page'):
                continue
            values = []
            page = stats[cycle]['page']
            values.append(str(page.cvus))
            cvus.append(str(page.cvus))
            values.append(str(page.rps))
            error = page.error_percent
            if error:
                has_error = True
            values.append(str(error))
            values.append(str(page.min))
            values.append(str(page.avg))
            values.append(str(page.max))
            values.append(str(page.percentiles.perc10))
            values.append(str(page.percentiles.perc50))
            values.append(str(page.percentiles.perc90))
            values.append(str(page.percentiles.perc95))
            lines.append(' '.join(values))
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = ['set output "' + image_path +'"']
        lines.append('set title "Successful Pages Per Second"')
        lines.append('set xlabel "Concurrent Users"')
        lines.append('set ylabel "Pages Per Second"')
        lines.append('set grid back')
        lines.append('set xrange ' + self.getXRange())
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        if not has_error:
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "SPPS"' % data_path)
        else:
            lines.append('set format x ""')
            lines.append('set multiplot')
            lines.append('unset title')
            lines.append('unset xlabel')
            lines.append('set size 1, 0.7')
            lines.append('set origin 0, 0.3')
            lines.append('set lmargin 5')
            lines.append('set bmargin 0')
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "SPPS"' % data_path)
            lines.append('set format x "% g"')
            lines.append('set bmargin 3')
            lines.append('set autoscale y')
            lines.append('set style fill solid .25')
            lines.append('set size 1.0, 0.3')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set ylabel "% errors"')
            lines.append('set origin 0.0, 0.0')
            #lines.append('set yrange [0:100]')
            #lines.append('set ytics 20')
            lines.append('plot "%s" u 1:3 w linespoints lt 1 lw 2 t "%% Errors"' % data_path)
            lines.append('unset multiplot')
            lines.append('set size 1.0, 1.0')
        lines.append('set output "%s"' % image2_path)
        lines.append('set title "Pages Response time"')
        lines.append('set ylabel "Duration (s)"')
        lines.append('set bars 5.0')
        lines.append('set style fill solid .25')
        lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)

    def createAllResponseChart(self):
        """Create global responses chart."""
        image_path = str(os.path.join(self.report_dir, 'requests_rps.png'))
        image2_path = str(os.path.join(self.report_dir, 'requests.png'))
        gplot_path = str(os.path.join(self.report_dir, 'requests.gplot'))
        data_path = str(os.path.join(self.report_dir, 'requests.data'))
        stats = self.stats
        # data
        lines = ["CUs RPS ERROR MIN AVG MAX P10 P50 P90 P95"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle].has_key('response'):
                continue
            values = []
            resp = stats[cycle]['response']
            values.append(str(resp.cvus))
            cvus.append(str(resp.cvus))
            values.append(str(resp.rps))
            error = resp.error_percent
            if error:
                has_error = True
            values.append(str(error))
            values.append(str(resp.min))
            values.append(str(resp.avg))
            values.append(str(resp.max))
            values.append(str(resp.percentiles.perc10))
            values.append(str(resp.percentiles.perc50))
            values.append(str(resp.percentiles.perc90))
            values.append(str(resp.percentiles.perc95))
            lines.append(' '.join(values))
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = ['set output "' + image_path +'"']
        lines.append('set title "Requests Per Second"')
        lines.append('set xlabel "Concurrent Users"')
        lines.append('set ylabel "Requests Per Second"')
        lines.append('set grid')
        lines.append('set xrange ' + self.getXRange())
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        if not has_error:
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "RPS"' % data_path)
        else:
            lines.append('set format x ""')
            lines.append('set multiplot')
            lines.append('unset title')
            lines.append('unset xlabel')
            lines.append('set size 1, 0.7')
            lines.append('set origin 0, 0.3')
            lines.append('set lmargin 5')
            lines.append('set bmargin 0')
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "RPS"' % data_path)
            lines.append('set format x "% g"')
            lines.append('set bmargin 3')
            lines.append('set autoscale y')
            lines.append('set style fill solid .25')
            lines.append('set size 1.0, 0.3')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set ylabel "% errors"')
            lines.append('set origin 0.0, 0.0')
            #lines.append('set yrange [0:100]')
            #lines.append('set ytics 20')
            lines.append('plot "%s" u 1:3 w linespoints lt 1 lw 2 t "%% Errors"' % data_path)
            lines.append('unset multiplot')
            lines.append('set size 1.0, 1.0')
        lines.append('set output "%s"' % image2_path)
        lines.append('set title "Requests Response time"')
        lines.append('set ylabel "Duration (s)"')
        lines.append('set bars 5.0')
        lines.append('set grid back')
        lines.append('set style fill solid .25')
        lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)

        return


    def createResponseChart(self, step):
        """Create responses chart."""
        image_path = str(os.path.join(self.report_dir,
                                      'request_%s.png' % step))
        gplot_path = str(os.path.join(self.report_dir, 'request_%s.gplot' % step))
        data_path = str(os.path.join(self.report_dir, 'request_%s.data' % step))
        stats = self.stats
        # data
        lines = ["CUs STEP ERROR MIN AVG MAX P10 P50 P90 P95"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle]['response_step'].has_key(step):
                continue
            values = []
            resp = stats[cycle]['response_step'].get(step)
            values.append(str(resp.cvus))
            cvus.append(str(resp.cvus))
            values.append(str(step))
            error = resp.error_percent
            if error:
                has_error = True
            values.append(str(error))
            values.append(str(resp.min))
            values.append(str(resp.avg))
            values.append(str(resp.max))
            values.append(str(resp.percentiles.perc10))
            values.append(str(resp.percentiles.perc50))
            values.append(str(resp.percentiles.perc90))
            values.append(str(resp.percentiles.perc95))
            lines.append(' '.join(values))
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = []
        lines.append('set output "%s"' % image_path)
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        lines.append('set grid')
        lines.append('set bars 5.0')
        lines.append('set title "Request %s Response time"' % step)
        lines.append('set xlabel "Concurrent Users"')
        lines.append('set ylabel "Duration (s)"')
        lines.append('set grid back')
        lines.append('set style fill solid .25')
        lines.append('set xrange ' + self.getXRange())
        if not has_error:
            lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
        else:
            lines.append('set format x ""')
            lines.append('set multiplot')
            lines.append('unset title')
            lines.append('unset xlabel')
            lines.append('set size 1, 0.7')
            lines.append('set origin 0, 0.3')
            lines.append('set lmargin 5')
            lines.append('set bmargin 0')
            lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
            lines.append('set format x "% g"')
            lines.append('set bmargin 3')
            lines.append('set autoscale y')
            lines.append('set style fill solid .25')
            lines.append('set size 1.0, 0.3')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set ylabel "% errors"')
            lines.append('set origin 0.0, 0.0')
            #lines.append('set yrange [0:100]')
            #lines.append('set ytics 20')
            lines.append('plot "%s" u 1:3 w linespoints lt 1 lw 2 t "%% Errors"' % data_path)
            lines.append('unset multiplot')
            lines.append('set size 1.0, 1.0')
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)
        return


    # monitoring charts
    def renderMonitor(self, host):
        """Render a monitored host."""
        description = self.config.get(host, '')
        self.append(rst_title("%s: %s" % (host, description), 3))
        self.append(".. image:: %s_monitor.png\n" % host)


    def createMonitorCharts(self):
        """Create all montirored server charts."""
        if not self.monitor or not self.with_chart:
            return
        self.append(rst_title("Monitored hosts", 2))
        for host in self.monitor.keys():
            self.createMonitorChart(host)


    def createMonitorChart(self, host):
        """Create monitrored server charts."""
        stats = self.monitor[host]
        times = []
        cvus_list = []
        for stat in stats:
            test, cycle, cvus = stat.key.split(':')
            date = datetime.fromtimestamp(float(stat.time))
            times.append(date.strftime("%H:%M:%S"))
            #times.append(int(float(stat.time))) # - time_start))
            cvus_list.append(cvus)

        mem_total = int(stats[0].memTotal)
        mem_used = [mem_total - int(x.memFree) for x in stats]
        mem_used_start = mem_used[0]
        mem_used = [x - mem_used_start for x in mem_used]

        swap_total = int(stats[0].swapTotal)
        swap_used = [swap_total - int(x.swapFree) for x in stats]
        swap_used_start = swap_used[0]
        swap_used = [x - swap_used_start for x in swap_used]

        load_avg_1 = [float(x.loadAvg1min) for x in stats]
        load_avg_5 = [float(x.loadAvg5min) for x in stats]
        load_avg_15 = [float(x.loadAvg15min) for x in stats]

        net_in = [None]
        net_out = [None]
        cpu_usage = [0]
        for i in range(1, len(stats)):
            if not (hasattr(stats[i], 'CPUTotalJiffies') and
                    hasattr(stats[i-1], 'CPUTotalJiffies')):
                cpu_usage.append(None)
            else:
                dt = ((long(stats[i].IDLTotalJiffies) +
                       long(stats[i].CPUTotalJiffies)) -
                      (long(stats[i-1].IDLTotalJiffies) +
                       long(stats[i-1].CPUTotalJiffies)))
                if dt:
                    ttl = (float(long(stats[i].CPUTotalJiffies) -
                                 long(stats[i-1].CPUTotalJiffies)) /
                           dt)
                else:
                    ttl = None
                cpu_usage.append(ttl)
            if not (hasattr(stats[i], 'receiveBytes') and
                    hasattr(stats[i-1], 'receiveBytes')):
                net_in.append(None)
            else:
                net_in.append((int(stats[i].receiveBytes) -
                               int(stats[i-1].receiveBytes)) /
                              (1024 * (float(stats[i].time) -
                                       float(stats[i-1].time))))

            if not (hasattr(stats[i], 'transmitBytes') and
                    hasattr(stats[i-1], 'transmitBytes')):
                net_out.append(None)
            else:
                net_out.append((int(stats[i].transmitBytes) -
                                int(stats[i-1].transmitBytes))/
                              (1024 * (float(stats[i].time) -
                                       float(stats[i-1].time))))

        image_path = str(os.path.join(self.report_dir,
                                      '%s_monitor.png' % host))
        data_path = str(os.path.join(self.report_dir,
                                     '%s_monitor.data' % host))
        gplot_path = str(os.path.join(self.report_dir,
                                      '%s_monitor.gplot' % host))

        data = [times, cvus_list, cpu_usage, load_avg_1, load_avg_5,
                load_avg_15, mem_used, swap_used, net_in, net_out ]
        data = zip(*data)
        f = open(data_path, 'w')
        f.write("TIME CUs CPU LOAD1 LOAD5 LOAD15 MEM SWAP NETIN NETOUT\n")
        for line in data:
            f.write(' '.join([str(item) for item in line]) + '\n')
        f.close()


        lines = []
        lines.append('set output "%s"' % image_path)
        lines.append('set terminal png size 640,768')
        lines.append('set multiplot layout 4, 1 title "Monitoring %s"' % host)
        lines.append('set grid back')
        lines.append('set xdata time')
        lines.append('set timefmt "%H:%M:%S"')
        lines.append('set format x "%H:%M"')

        lines.append('set title "Concurrent Users" offset 0, -2')
        lines.append('set ylabel "CUs"')
        lines.append('plot "%s" u 1:2 notitle with impulse lw 2 lt 3' % data_path)

        lines.append('set title "Load average"')
        lines.append('set ylabel "loadavg"')
        lines.append('plot "%s" u 1:3 t "CPU 1=100%%" w impulse lw 2 lt 1, "" u 1:4 t "Load 1min" w lines lw 2 lt 3, "" u 1:5 t "Load 5min" w lines lw 2 lt 4, "" u 1:6 t "Load 15min" w lines lw 2 lt 5' % data_path)

        lines.append('set title "Network traffic"')
        lines.append('set ylabel "kB/s"')
        lines.append('plot "%s" u 1:8 t "In" w lines lw 2 lt 2, "" u 1:9 t "Out" w lines lw 1 lt 1' % data_path)

        lines.append('set title "Memory usage"')
        lines.append('set ylabel "kB"')
        lines.append('plot "%s" u 1:7 t "Memory" w lines lw 2 lt 2, "" u 1:8 t "Swap" w lines lw 2 lt 1' % data_path)

        lines.append('unset multiplot')
        f = open(gplot_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        gnuplot(gplot_path)
        return
