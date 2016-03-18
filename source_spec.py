#!/usr/bin/env python
# -*- coding: utf-8 -*-
# source_spec.py
#
# Main function for source_spec
# (c) 2012 Claudio Satriano <satriano@ipgp.fr>
# (c) 2013-2014 Claudio Satriano <satriano@ipgp.fr>,
#               Emanuela Matrullo <matrullo@geologie.ens.fr>,
#               Agnes Chounet <chounet@ipgp.fr>
# (c) 2015-2016 Claudio Satriano <satriano@ipgp.fr>
from source_spec.ssp_setup import configure, setup_logging,\
        init_plotting, ssp_exit
from source_spec.ssp_read_traces import read_traces
from source_spec.ssp_process_traces import process_traces
from source_spec.ssp_build_spectra import build_spectra
from source_spec.ssp_local_magnitude import local_magnitude
from source_spec.ssp_inversion import spectral_inversion
from source_spec.ssp_output import write_output
from source_spec.ssp_residuals import spectral_residuals
from source_spec.ssp_plot_spectra import plot_spectra
from source_spec.ssp_plot_traces import plot_traces


def main():
    # Setup stage
    config = configure()
    setup_logging(config)
    plot_pool = init_plotting()
    # comment the following line to do
    # serial plotting (useful for debug)
    apply = plot_pool.apply_async

    st = read_traces(config)

    # Now that we (hopefully) have the evid
    # we rename the logfile to use the evid
    #TODO: improve this:
    evid = st.traces[0].stats.hypo.evid
    setup_logging(config, evid)

    # Deconvolve, filter, cut traces:
    proc_st = process_traces(config, st)

    # Build spectra (amplitude in magnitude units)
    spec_st, specnoise_st, weight_st =\
        build_spectra(config, proc_st, noise_weight=True)

    apply(plot_traces, (config, proc_st, 2))

    Ml = local_magnitude(config, st, deconvolve=True)

    # Spectral inversion
    sourcepar = spectral_inversion(config, spec_st, weight_st, Ml)

    # Save output
    sourcepar_mean = write_output(config, evid, sourcepar)

    # Save residuals
    spectral_residuals(config, spec_st, evid, sourcepar_mean)

    # Plotting
    apply(plot_spectra,
          (config, spec_st),
          {'specnoise_st': specnoise_st,
           'plottype': 'regular'})
    apply(plot_spectra,
          (config, specnoise_st),
          {'plottype': 'noise'})
    apply(plot_spectra,
          (config, weight_st),
          {'plottype': 'weight'})

    ssp_exit()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        ssp_exit(1)
