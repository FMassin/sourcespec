# -*- coding: utf-8 -*-
# ssp_plot_traces.py
#
# (c) 2015-2016 Claudio Satriano <satriano@ipgp.fr>
"""Trace plotting routine."""
from __future__ import division
import os
import math
import logging

phase_label_pos = {'P': 0.9, 'S': 0.93}
phase_label_color = {'P': 'black', 'S': 'black'}


def plot_traces(config, st, ncols=4, block=True, async_plotter=None):
    """
    Plot displacement traces.

    Display to screen and/or save to file.
    """
    # Check config, if we need to plot at all
    if not config.PLOT_SHOW and not config.PLOT_SAVE:
        return
    import matplotlib
    matplotlib.rcParams['pdf.fonttype'] = 42  # to edit text in Illustrator
    if config.PLOT_SHOW:
        import matplotlib.pyplot as plt
    else:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
    import matplotlib.transforms as transforms
    import matplotlib.patches as patches

    # Determine the number of plots and axes min and max:
    nplots = 0
    for station in set(x.stats.station for x in st.traces):
        st_sel = st.select(station=station)
        # 'code' is band+instrument code
        for code in set(x.stats.channel[0:2] for x in st_sel):
            nplots += 1
    nlines = int(math.ceil(nplots/ncols))
    if nplots < ncols:
        ncols = 1

    # OK, now we can plot!
    if nlines <= 3:
        figsize = (16, 9)
    else:
        figsize = (16, 18)
    if config.PLOT_SHOW:
        fig = plt.figure(figsize=figsize)
    else:
        fig = Figure(figsize=figsize)
    fig.subplots_adjust(hspace=.1, wspace=.15)

    # Plot!
    axes = []
    plotn = 0
    for station in sorted(set(x.stats.station for x in st.traces)):
        st_sel = st.select(station=station)
        # 'code' is band+instrument code
        for code in set(x.stats.channel[0:2] for x in st_sel):
            plotn += 1
            ax_text = False

            if plotn == 1:
                ax = fig.add_subplot(nlines, ncols, plotn)
            else:
                ax = fig.add_subplot(nlines, ncols, plotn, sharex=axes[0])
            ax.grid(True, which='both', linestyle='solid', color='#DDDDDD',
                    zorder=0)
            ax.set_axisbelow(True)
            [t.set_visible(False) for t in ax.get_xticklabels()]
            [t.set_visible(True) for t in ax.get_yticklabels()]
            ax.tick_params(width=2)  # FIXME: ticks are below grid lines!
            ax.ticklabel_format(style='scientific', axis='y',
                                scilimits=(-1, 1))
            axes.append(ax)
            instrtype = [t.stats.instrtype for t in st_sel.traces
                         if t.stats.channel[0:2] == code][0]
            if instrtype == 'acc':
                ax.set_ylabel(u'Acceleration (m/s²)')
            elif instrtype == 'shortp' or instrtype == 'broadb':
                ax.set_ylabel('Velocity (m/s)')
            # Custom transformation for plotting phase labels:
            # x coords are data, y coords are axes
            trans = transforms.blended_transform_factory(ax.transData,
                                                         ax.transAxes)
            trans2 = transforms.blended_transform_factory(ax.transAxes,
                                                          ax.transData)
            trans3 = transforms.offset_copy(trans2, fig=fig, x=0, y=0.1)

            maxes = [abs(t.max()) for t in st_sel.traces
                     if t.stats.channel[0:2] == code]
            ntraces = len(maxes)
            tmax = max(maxes)
            for trace in st_sel.traces:
                if trace.stats.channel[0:2] != code:
                    continue
                starttime = trace.stats.starttime
                t1 = (starttime + trace.stats.arrivals['P'][1] -
                      config.pre_p_time)
                t2 = (starttime + trace.stats.arrivals['S'][1] +
                      3 * config.s_win_length)
                trace.trim(starttime=t1, endtime=t2, pad=True, fill_value=0)
                delta_stime = trace.stats.starttime - starttime
                orientation = trace.stats.channel[-1]
                if orientation in ['Z', '1']:
                    color = 'purple'
                if orientation in ['N', '2']:
                    color = 'green'
                    if ntraces > 1:
                        trace.data = (trace.data / tmax - 1) * tmax
                if orientation in ['E', '3']:
                    color = 'blue'
                    if ntraces > 1:
                        trace.data = (trace.data / tmax + 1) * tmax
                ax.plot(trace.times(), trace, color=color, zorder=20)
                ax.text(0.05, trace.data.mean(), trace.stats.channel,
                        color=color, transform=trans3, zorder=22)
                for phase in 'P', 'S':
                    arrival = trace.stats.arrivals[phase][1] - delta_stime
                    text = trace.stats.arrivals[phase][0]
                    ax.axvline(arrival, linestyle='--',
                               color=phase_label_color[phase], zorder=21)
                    ax.text(arrival, phase_label_pos[phase],
                            text, transform=trans,
                            zorder=22)
                # Noise window
                try:
                    N1 = trace.stats.arrivals['N1'][1] - delta_stime
                    N2 = trace.stats.arrivals['N2'][1] - delta_stime
                    rect = patches.Rectangle((N1, 0), width=N2-N1, height=1,
                                             transform=trans, color='#eeeeee',
                                             alpha=0.5, zorder=-1)
                    ax.add_patch(rect)
                except KeyError:
                    pass
                # S-wave window
                S1 = trace.stats.arrivals['S1'][1] - delta_stime
                S2 = trace.stats.arrivals['S2'][1] - delta_stime
                rect = patches.Rectangle((S1, 0), width=S2-S1, height=1,
                                         transform=trans, color='yellow',
                                         alpha=0.5, zorder=-1)
                ax.add_patch(rect)

                if not ax_text:
                    text_y = 0.1
                    color = 'black'
                    ax.text(0.05, text_y, '%s %s' %
                            (trace.stats.station, trace.stats.instrtype),
                            horizontalalignment='left',
                            verticalalignment='bottom',
                            color=color,
                            #backgroundcolor=(1, 1, 1, 0.7),
                            transform=ax.transAxes,
                            zorder=50)
                    ax_text = True

    # Show the x-labels only for the last row
    for ax in axes[-ncols:]:
        [t.set_visible(True) for t in ax.get_xticklabels()]
        ax.set_xlabel('Time (s)')

    if config.PLOT_SHOW:
        plt.show(block=block)
    if config.PLOT_SAVE:
        #TODO: improve this:
        evid = st.traces[0].stats.hypo.evid
        figurefile = os.path.join(config.options.outdir, evid +
                                  '.traces.' + config.PLOT_SAVE_FORMAT)
        if config.PLOT_SHOW:
            fig.savefig(figurefile, bbox_inches='tight')
        else:
            canvas = FigureCanvasAgg(fig)
            if async_plotter is not None:
                async_plotter.save(canvas, figurefile, bbox_inches='tight')
            else:
                canvas.print_figure(figurefile, bbox_inches='tight')
        logging.info('Trace plots saved to: ' + figurefile)
    fig.clf()