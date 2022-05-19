# -*- coding: utf8 -*-
# SPDX-License-Identifier: CECILL-2.1
"""
Classes for spectral inversion routines.

:copyright:
    2017-2022 Claudio Satriano <satriano@ipgp.fr>
:license:
    CeCILL Free Software License Agreement v2.1
    (http://www.cecill.info/licences.en.html)
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import numpy as np
logger = logging.getLogger(__name__.split('.')[-1])


class InitialValues():
    """Initial values for spectral inversion."""

    def __init__(self, Mw_0=None, fc_0=None, t_star_0=None):
        self.Mw_0 = Mw_0
        self.fc_0 = fc_0
        self.t_star_0 = t_star_0

    def __str__(self):
        """String representation."""
        s = 'Mw_0: %s; ' % round(self.Mw_0, 4)
        s += 'fc_0: %s; ' % round(self.fc_0, 4)
        s += 't_star_0: %s' % round(self.t_star_0, 4)
        return s

    def get_params0(self):
        return (self.Mw_0, self.fc_0, self.t_star_0)


class Bounds(object):
    """Bounds for bounded spectral inversion."""

    def __init__(self, config, spec, initial_values):
        self.config = config
        self.spec = spec
        self.hd = spec.stats.hypo_dist
        self.ini_values = initial_values
        self.Mw_min = self.Mw_max = None
        self._set_fc_min_max(config)
        if config.Qo_min_max is None:
            self.t_star_min, self.t_star_max =\
                self._check_minmax(config.t_star_min_max)
        else:
            self.t_star_min, self.t_star_max = self._Qo_to_t_star()
        self._fix_initial_values_t_star()

    def __str__(self):
        """String representation."""
        s = 'Mw: {}, {}; '.format(
            *[round(x, 4) if x is not None else x for x in self.bounds[0]])
        s += 'fc: {}, {}; '.format(
            *[round(x, 4) if x is not None else x for x in self.bounds[1]])
        s += 't_star: {}, {}'.format(
            *[round(x, 4) if x is not None else x for x in self.bounds[2]])
        return s

    def _set_fc_min_max(self, config):
        fc_0 = self.ini_values.fc_0
        if config.fc_min_max is None:
            # If no bound is given, set it to fc_0 +/- a decade
            scale = 10.  # a decade
            self.fc_min = fc_0/scale
            self.fc_max = fc_0*scale
        else:
            self.fc_min, self.fc_max = config.fc_min_max
        if self.fc_min > fc_0:
            logger.warning(
                '{} {}: fc_min ({}) larger than fc_0 ({}). '
                'Using fc_0 instead.'.format(
                    self.spec.id, self.spec.stats.instrtype,
                    self.fc_min, round(fc_0, 4))
            )
            self.fc_min = fc_0
        if self.fc_max < fc_0:
            logger.warning(
                '{} {}: fc_max ({}) smaller than fc_0 ({}). '
                'Using fc_0 instead.'.format(
                    self.spec.id, self.spec.stats.instrtype,
                    self.fc_max, round(fc_0, 4))
            )
            self.fc_max = fc_0

    def _check_minmax(self, minmax):
        if minmax is None:
            return (None, None)
        else:
            return minmax

    def _Qo_to_t_star(self):
        # See if there is a travel-time vs defined
        vs = self.config.vs_tt
        if vs is None:
            vs = self.config.hypo.vs
        t_star_bounds =\
            self.hd/(vs*np.array(self.config.Qo_min_max))
        return sorted(t_star_bounds)

    def _fix_initial_values_t_star(self):
        if self.ini_values.t_star_0 is not None:
            return
        if None in self.bounds[2]:
            return
        if self.t_star_min < self.ini_values.t_star_0 < self.t_star_max:
            return
        t_star_0 = (self.t_star_max + self.t_star_min) / 2.
        logger.warning(
            '{} {}: initial t_star value ({}) outside '
            'bounds. Using bound average ({})'.format(
                self.spec.id, self.spec.stats.instrtype,
                self.ini_values.t_star_0, round(t_star_0, 4))
        )
        self.ini_values.t_star_0 = t_star_0

    def __call__(self, **kwargs):
        """Interface for basin-hopping."""
        params = kwargs['x_new']
        params_min = np.array(
            (self.Mw_min, self.fc_min, self.t_star_min)).astype(float)
        params_max = np.array(
            (self.Mw_max, self.fc_max, self.t_star_max)).astype(float)
        params_min[np.isnan(params_min)] = 1e-99
        params_max[np.isnan(params_min)] = 1e+99
        tmin = bool(np.all(params >= params_min))
        tmax = bool(np.all(params <= params_max))
        return tmin and tmax

    @property
    def bounds(self):
        """Get bounds for minimize() as sequence of (min, max) pairs."""
        self._bounds = ((self.Mw_min, self.Mw_max),
                        (self.fc_min, self.fc_max),
                        (self.t_star_min, self.t_star_max))
        return self._bounds

    @bounds.setter
    def bounds(self, value):
        """Set bounds from a sequence of three (min, max) pairs."""
        self._bounds = value
        self.Mw_min, self.Mw_max = value[0]
        self.fc_min, self.fc_max = value[1]
        self.t_star_min, self.t_star_max = value[2]

    def get_bounds_curve_fit(self):
        """Get bounds for curve-fit()."""
        bnds = np.array(self.bounds, dtype=float).T
        if np.all(np.isnan(bnds)):
            return None
        bnds[0, np.isnan(bnds[0])] = -1e100
        bnds[1, np.isnan(bnds[1])] = 1e100
        return bnds


class StationSourceParameters(dict):
    """Source parameters for one station."""

    def __init__(self, statId, params, errors):
        self['statId'] = statId
        for key, val in dict(params).items():
            self[key] = val
        for key, val in dict(errors).items():
            self[key + '_err'] = val

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


class SourceParameters(dict):
    """Source parameters for all stations."""

    def value_array(self, key, filter_outliers=False):
        self.station_parameters = self.values()
        vals = np.array([x.get(key, np.nan) for x in self.station_parameters])
        if filter_outliers:
            outliers = self.outlier_array(key)
            vals = vals[~outliers]
        return vals

    def error_array(self, key, filter_outliers=False):
        self.station_parameters = self.values()
        errs = np.array(
            [x.get(key + '_err', np.nan) for x in self.station_parameters])
        if filter_outliers:
            outliers = self.outlier_array(key)
            errs = errs[~outliers]
        return errs

    def outlier_array(self, key):
        self.station_parameters = self.values()
        key += '_outlier'
        return np.array([x.get(key) for x in self.station_parameters])

    def find_outliers(self, key, nstd):
        """Find extreme values that are larger than nstd*std."""
        values = self.value_array(key)
        _values = values.copy()
        nval = len(_values)
        outliers = np.zeros(nval).astype(bool)
        for _ in range(nval):
            if np.all(np.isnan(values)):
                break
            # find the extreme value
            vmean = np.nanmean(_values)
            argextreme = np.nanargmax(np.abs(_values-vmean))
            extreme = values[argextreme]
            # trim the extreme value and compute statistics
            # for the remaining values
            values_trim = np.delete(_values, argextreme)
            vmean = np.nanmean(values_trim)
            vstd = np.nanstd(values_trim)
            if np.abs(extreme - vmean) > nstd*vstd:
                _values[argextreme] = np.nan
                outliers[argextreme] = True
            else:
                # if no outlier is found, break
                break
            if np.sum(~outliers) == 3:
                # if only 3 non-outliers remain, break
                break
        self.station_parameters = self.values()
        if len(self.station_parameters) != len(outliers):
            raise ValueError
        key += '_outlier'
        for par, outl in zip(self.station_parameters, outliers):
            par[key] = outl
