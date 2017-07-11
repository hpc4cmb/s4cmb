#!/usr/bin/python
"""
Script to simulate time-ordered data generated by a CMB experiment
scanning the sky.

Author: Julien Peloton, j.peloton@sussex.ac.uk
"""
from __future__ import division, absolute_import, print_function

import healpy as hp
import numpy as np
from numpy import cos
from numpy import sin
from numpy import tan
from pyslalib import slalib

sec2deg = 360.0/86400.0
d2r = np.pi / 180.0
ASTROMETRIC_GEOCENTRIC = 0
APPARENT_GEOCENTRIC = 1
APPARENT_TOPOCENTRIC = 2

class TimeOrderedData():
    """ Class to handle Time-Ordered Data (TOD) """
    def __init__(self, hardware, scanning_strategy, HealpixFitsMap):
        """
        C'est parti!

        Parameters
        ----------
        hardware : hardware instance
            Instance of hardware containing instrument parameters and models.
        scanning_strategy : scanning_strategy instance
            Instance of scanning_strategy containing scan parameters.
        HealpixFitsMap : HealpixFitsMap instance
            Instance of HealpixFitsMap containing input sky parameters.
        """
        self.hardware = hardware
        self.scanning_strategy = scanning_strategy
        self.HealpixFitsMap = HealpixFitsMap

        self.pointing = None

    def ComputeBoresightPointing(self):
        """
        Compute the boresight pointing for all the focal plane bolometers.
        """
        lat = float(
            self.scanning_strategy.telescope_location.lat) * 180. / np.pi

        self.pointing = pointing(
            az_enc=self.scanning_strategy.scan0['azimuth'],
            el_enc=self.scanning_strategy.scan0['elevation'],
            time=self.scanning_strategy.scan0['clock-utc'],
            value_params=self.hardware.pointing_model.value_params,
            allowed_params=self.hardware.pointing_model.allowed_params,
            lat=lat)

    def get_tod(self):
        """
        Scan the input sky maps to generate timestreams.
        """
        pass

    def map_tod(self):
        """
        Project time-ordered data into sky maps.
        """

class pointing():
    """ """
    def __init__(self, az_enc, el_enc, time, value_params,
                 allowed_params='ia ie ca an aw',
                 ra_src=0.0, dec_src=0.0, lat=-22.958,
                 ut1utc_fn='data/ut1utc.ephem'):
        """
        Apply pointing model with parameters `value_params` and
        names `allowed_params` to encoder az,el. Order of terms is
        `value_params` is same as order of terms in `allowed_params`.

        Full list of parameters (Thx Fred!):
            an:  azimuth axis tilt north of vertical
            aw:  azimuth axis tilt west of vertical
            an2:  potato chip
            aw2:  potato chip
            npae:  not parallel azimuth/elevation
            ca:  angle of beam to boresight in azimuth
            ia:  azimuth encoder zero
            ie:  elevation encoder zero + angle of beam
                to boresight in elevation
            tf:  cosine flexure
            tfs:  sine flexure
            ref:  refraction
            dt:  timing error in seconds (requires lat argument)
            elt:  time from start elevation correction
            ta1: linear order structural thermal warping in azimuth
            te1: linear order structural thermal warping in elevation
            sa,sa2: solar radiation structural warping in azimuth
            se,se2: solar radiation structural warping in elevation

        Parameters
        ----------
        az_enc : 1d array
            Encoder azimuth in radians.
        el_enc : 1d array
            Encoder elevation in radians.
        time : 1d array
            Encoder time (UTC) in mjd
        value_params : 1d array
            Value of the pointing model parameters (see instrument.py).
            In degrees (see below for full description)
        allowed_params : list of string
            Name of the pointing model parameters used in `value_params`.
        ra_src : float
            RA of the source (center of the patch).
        dec_src : float
            Dec of the source (center of the patch).
        lat : float, optional
            Latitude of the telescope, in degree.
        ut1utc_fn : string
            File containing time correction to UTC.
            The \Delta{UT} (UT1-UTC) is tabulated in IERS circulars
            and elsewhere. It increases by exactly one second at the end
            of each UTC leap second, introduced in order to
            keep \Delta{UT} within \pm 0s.9.
            The 'sidereal \Delta{UT}' which forms part of AOPRMS(13)
            is the same quantity, but converted from solar to sidereal
            seconds and expressed in radians.
            WTF?

        Examples
        ----------
        See hardware.py for more information on the pointing model.
        >>> allowed_params = 'ia ie ca an aw'
        >>> value_params = [10.28473073, 8.73953334, -15.59771781,
        ...     -0.50977716, 0.10858016]
        >>> az_enc = np.array([np.sin(2 * np.pi * i / 100)
        ...     for i in range(100)])
        >>> el_enc = np.ones(100) * 0.5
        >>> time = np.array([56293 + t/84000 for t in range(100)])
        >>> pointing = pointing(az_enc, el_enc, time, value_params,
        ...     allowed_params, lat=-22.)
        >>> print(az_enc[2:4], pointing.az[2:4])
        [ 0.12533323  0.18738131] [ 0.11717842  0.17922137]
        """
        self.az_enc = az_enc
        self.el_enc = el_enc
        self.time = time
        self.value_params = value_params
        self.allowed_params = allowed_params
        self.lat = lat * d2r
        self.ut1utc_fn = ut1utc_fn
        self.ra_src = ra_src
        self.dec_src = dec_src

        self.ut1utc = self.get_ut1utc(self.ut1utc_fn, self.time[0])

        ## Initialise the object
        self.az, self.el = self.apply_pointing_model()
        self.azel2radec()

        ## And then for each det, apply offset_detector

    @staticmethod
    def get_ut1utc(ut1utc_fn, mjd):
        """
        Return the time correction to UTC.

        Returns
        ----------
        ut1utc : float
            Contain the time correction to apply to MJD values.

        Examples
        ----------
        >>> round(pointing.get_ut1utc('data/ut1utc.ephem', 56293), 3)
        0.277
        """
        umjds, ut1utcs = np.loadtxt(ut1utc_fn, usecols=(1, 2)).T
        uindex = np.searchsorted(umjds, mjd)
        ut1utc = ut1utcs[uindex]

        return ut1utc

    def apply_pointing_model(self):
        """
        Apply pointing corrections specified by the pointing model.

        Returns
        ----------
        az : 1d array
            The corrected azimuth in arcminutes.
        el : 1d array
            The corrected elevation in arcminutes.
        """
        assert len(self.value_params) == len(self.allowed_params.split()), \
            AssertionError("Vector containing parameters " +
                           "(value_params) has to have the same " +
                           "length than the vector containing names " +
                           "(allowed_params).")

        ## Here are many parameters defining a pointing model.
        ## Of course, we do not use all of them. They are zero by default,
        ## and only those specified by the user will be used.
        params = {p: 0.0 for p in ['an', 'aw', 'an2', 'aw2', 'an4',
                                   'aw4', 'npae', 'ca', 'ia', 'ie', 'tf',
                                   'tfs', 'ref', 'dt', 'elt', 'ta1',
                                   'te1', 'sa', 'se', 'sa2',
                                   'se2', 'sta', 'ste', 'sta2', 'ste2']}

        for param in params:
            if param in self.allowed_params.split():
                index = self.allowed_params.split().index(param)
                params[param] = self.value_params[index]

        params['dt'] *= sec2deg

        ## Azimuth
        azd = -params['an'] * sin(self.az_enc) * sin(self.el_enc)
        azd -= params['aw'] * cos(self.az_enc) * sin(self.el_enc)

        azd -= -params['an2'] * sin(2 * self.az_enc) * sin(self.el_enc)
        azd -= params['aw2'] * cos(2 * self.az_enc) * sin(self.el_enc)

        azd -= -params['an4'] * sin(4 * self.az_enc) * sin(self.el_enc)
        azd -= params['aw4'] * cos(4 * self.az_enc) * sin(self.el_enc)

        azd += params['npae'] * sin(self.el_enc)
        azd -= params['ca']
        azd += params['ia'] * cos(self.el_enc)

        azd += params['dt'] * (
            -sin(self.lat) + cos(self.az_enc) *
            cos(self.lat) * tan(self.el_enc))

        ## Elevation
        eld = params['an'] * cos(self.az_enc)
        eld -= params['aw'] * sin(self.az_enc)
        eld -= params['an2'] * cos(2 * self.az_enc)
        eld -= params['aw2'] * sin(2 * self.az_enc)
        eld -= params['an4'] * cos(4 * self.az_enc)
        eld -= params['aw4'] * sin(4 * self.az_enc)

        eld -= params['ie']
        eld += params['tf'] * cos(self.el_enc)
        eld += params['tfs'] * sin(self.el_enc)
        eld -= params['ref'] / tan(self.el_enc)

        eld += -params['dt'] * cos(self.lat) * sin(self.az_enc)

        eld += params['elt'] * (self.time - np.min(self.time))

        ## Convert back in radian and apply to the encoder values.
        azd *= np.pi / (180.0 * 60.)
        eld *= np.pi / (180.0 * 60.)

        azd /= np.cos(self.el_enc)

        az = self.az_enc - azd
        el = self.el_enc - eld

        return az, el

    def azel2radec(self):
        """
        """
        self.ra, self.dec, self.pa = self.azel2radecpa()
        v_ra = self.ra
        v_dec = self.dec
        v_pa = self.pa
        v_ra_src = self.ra_src
        v_dec_src = self.dec_src

        self.meanpa = np.median(v_pa)

        # q = quat_pointing.offset_radecpa_makequat(
        #     v_ra, v_dec, v_pa, v_ra_src, v_dec_src)
        # assert q.shape == (self.az.size, 4)
        # self.q = q

    def azel2radecpa(self):
        """
        """
        converter = Azel2Radec(self.time[0], self.ut1utc)
        vconv = np.vectorize(converter.azel2radecpa)
        ra, dec, pa = vconv(self.time, self.az, self.el)
        return ra, dec, pa

    def radec2azel(self):
        """
        """
        converter = Azel2Radec(self.time[0], self.ut1utc)
        vconv = np.vectorize(converter.radec2azel)
        az, el = vconv(self.time, self.ra, self.dec)
        return az, el

    # def offset_detector(self, azd, eld):
    #     """
    #     """
    #     ra, dec, pa = quat_pointing.offset_radecpa_applyquat(
    #         self.q, -azd, -eld)
    #     return ra, dec, pa

class Azel2Radec(object):
    """ Class to handle az/el <-> ra/dec conversion """
    def __init__(self, mjd, ut1utc,
                 lon=-67.786, lat=-22.958, height=5200,
                 pressure=533.29, temp=273.15, humidity=0.1, epequi=2000.0):
        """
        """
        self.lon = (360. - lon) * d2r
        self.lat = lat * d2r
        self.height = height
        self.pressure = pressure
        self.temp = temp
        self.humidity = humidity
        self.mjd = mjd

        self.epequi = epequi
        self.ut1utc = ut1utc

        self.updateaoprms(mjd)

    def updateaoprms(self, mjd):
        """
        """
        xpm = 0.0
        ypm = 0.0
        wavelength = (299792458.0 / 150.0e9) * 1e6
        lapserate = 0.0065
        self.aoprms = slalib.sla_aoppa(mjd, self.ut1utc, self.lon, self.lat,
                                       self.height, xpm, ypm, self.temp,
                                       self.pressure, self.humidity,
                                       wavelength, lapserate)

    def azel2radecpa(self, mjd, az, el, lst_gcp=0):
        """
        This routine does not return a precisely correct parallactic angle
        """
        zd = np.pi / 2 - el
        amprms = slalib.sla_mappa(self.epequi, mjd)
        self.aoprms = slalib.sla_aoppat(mjd, self.aoprms)

        ra_app1, dec_app1 = slalib.sla_oapqk('a', az, zd + 1e-8, self.aoprms)
        ra1, dec1 = slalib.sla_ampqk(ra_app1, dec_app1, amprms)
        ra_app2, dec_app2 = slalib.sla_oapqk('a', az, zd - 1e-8, self.aoprms)
        ra2, dec2 = slalib.sla_ampqk(ra_app2, dec_app2, amprms)
        pa = slalib.sla_dbear(ra1, dec1, ra2, dec2)
        ra = 0.5 * (ra1 + ra2)
        dec = 0.5 * (dec1 + dec2)

        return ra, dec, pa

    def radec2azel(self, mjd, ra, dec):
        """
        """
        amprms = slalib.sla_mappa(self.epequi, mjd)
        self.aoprms = slalib.sla_aoppat(mjd, self.aoprms)
        ra_app, dec_app = slalib.sla_mapqkz(ra, dec, amprms)
        az, zd, a, b, c = slalib.sla_aopqk(ra_app, dec_app, self.aoprms)
        el = np.pi / 2 - zd
        return az, el


if __name__ == "__main__":
    import doctest
    doctest.testmod()
