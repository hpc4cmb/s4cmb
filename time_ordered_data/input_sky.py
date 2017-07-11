#!/usr/bin/python
"""
Script to simulate and handle input sky maps to be scanned.
Default file format is .fits containing healpix maps, and it comes with a
class HealpixFitsMap to handle it easily.
If you have a different I/O in your pipeline, just add a new class.

Author: Julien Peloton, j.peloton@sussex.ac.uk
"""
from __future__ import division, absolute_import, print_function

import glob
import os

import healpy as hp
import numpy as np
from astropy.io import fits as pyfits

class HealpixFitsMap():
    """ Class to handle fits file containing healpix maps """
    def __init__(self, input_filename,
                 do_pol=True, verbose=False,
                 no_ileak=False, no_quleak=False):
        """

        """
        self.input_filename = input_filename
        self.do_pol = do_pol
        self.verbose = verbose
        self.no_ileak = no_ileak
        self.no_quleak = no_quleak

        self.nside = None
        self.I = None
        self.Q = None
        self.U = None

        self.load_healpix_fits_map()
        self.set_leakage_to_zero()

    def load_healpix_fits_map(self, force=False):
        """
        Load from disk into memory a sky map.

        Parameters
        ----------
        force : bool
            If true, force to load the maps in memory even if it is already
            loaded. Default is False.

        Examples
        ----------
        Let's generate fake data
        >>> filename = 'myfits_to_test_.fits'
        >>> write_dummy_map(filename, nside=16)

        Let's now read the data
        >>> hpmap = HealpixFitsMap(input_filename=filename)
        >>> hpmap.load_healpix_fits_map(force=True)
        >>> print(hpmap.nside)
        16

        If the data is already loaded, it won't reload it by default
        >>> hpmap.load_healpix_fits_map()
        External data already present in memory
        """
        if self.nside is None or force:
            if self.do_pol:
                self.I, self.Q, self.U = hp.read_map(
                    self.input_filename, (0, 1, 2), verbose=self.verbose)
            else:
                self.I = hp.read_map(
                    self.input_filename, field=0, verbose=self.verbose)
            self.nside = hp.npix2nside(len(self.I))
        else:
            print("External data already present in memory")

    def set_leakage_to_zero(self):
        """
        Remove either I, Q or U to remove possible leakages

        Examples
        ----------
        Test with no input intensity
        >>> write_dummy_map('myfits_to_test_.fits')
        >>> hpmap = HealpixFitsMap('myfits_to_test_.fits', no_ileak=True)
        >>> print(hpmap.I)
        [ 0.  0.  0. ...,  0.  0.  0.]

        Test with no input polarisation
        >>> write_dummy_map('myfits_to_test_.fits')
        >>> hpmap = HealpixFitsMap('myfits_to_test_.fits', no_quleak=True)
        >>> print(hpmap.Q, hpmap.U)
        [ 0.  0.  0. ...,  0.  0.  0.] [ 0.  0.  0. ...,  0.  0.  0.]
        """
        ## Set temperature to zero to avoid I->QU leakage
        if self.no_ileak:
            self.I[:] = 0.0

        ## Set polarisation to zero to avoid QU leakage
        if self.no_quleak:
            if self.Q is not None:
                self.Q[:] = 0.0
            if self.U is not None:
                self.U[:] = 0.0

    @staticmethod
    def write_healpix_cmbmap(output_filename, data, nside, fits_IDL=False,
                             coord=None, colnames=None, nest=False):
        """
        Write healpix fits map in full sky mode or custom partial sky,
        i.e. file with obspix and CMB_fields. Input data have to be a list
        with n fields to be written.

        / ! \
        By default, even the full sky mode write the maps in partial mode, in
        the sense that the data is compressed. so unless you know what you
        are doing, always choose partial_custom=False.
        / ! \

        Parameters
        ----------
        output_filename : string
            Name of the output file (.fits).
        data : list of 1d array(s)
            Data to save on disk.
        nside : int
            Resolution of the map. Must be a power of 2.
        fits_IDL : bool
            If True, store the data reshaped in row of 1024 (IDL style).
            Default is False.
        coord : string
            The system of coordinates in which the data are
            (G(alactic), C(elestial), and so on). Default is None.
        colnames : list of strings
            The name of each data vector to be saved.
        nest : bool, optional
            If True, save the data in the nest scheme. Default is False (i.e.
            data are saved in the RING format).

        Examples
        ----------
        >>> nside = 16
        >>> I, Q, U = np.random.rand(3, hp.nside2npix(nside))
        >>> colnames = ['I', 'Q', 'U']
        >>> HealpixFitsMap.write_healpix_cmbmap('myfits_to_test_.fits',
        ...     data=[I, Q, U], nside=nside, colnames=colnames)
        """
        ## Write the header
        extra_header = []
        for c in colnames:
            extra_header.append(('column_names', c))
        extra_header = HealpixFitsMap.add_hierarch(extra_header)

        hp.write_map(output_filename, data, fits_IDL=fits_IDL,
                     coord=coord, column_names=None, partial=True,
                     extra_header=extra_header)

        return

    @staticmethod
    def add_hierarch(lis):
        """
        Convert in correct format for fits header.

        Parameters
        ----------
        lis: list of tuples
            Contains tuples (keyword, value [, comment]).

        Returns
        ----------
        lis : list of strings
            Contains strings in the pyfits header format.

        """
        for i, item in enumerate(lis):
            if len(item) == 3:
                lis[i] = ('HIERARCH ' + item[0], item[1], item[2])
            else:
                lis[i] = ('HIERARCH ' + item[0], item[1])
        return lis

    # def get_obspix(xmin,xmax,ymin,ymax,nside,verbose=False):
    # 	# check that healpy version is compatible. If not load the old functions called in
    # 	# the healpix map class and add them to the healpy namespace
    # 	if not (hasattr(hp,'in_ring') and hasattr(hp,'ring2z') and hasattr(hp,'ring_num')):
    # 		import tod_and_mapmaking.so_healpy_compatibility as hp_comp
    # 		if (not hasattr(hp,'in_ring')):
    # 			if verbose:
    # 				print('WARNING: current healpy version does not support in_ring function. Added compatibility mode')
    # 			hp.in_ring=hp_comp.in_ring
    # 		if not hasattr(hp,'ring2z'):
    # 			hp.ring2z=hp_comp.ring2z
    # 		if (not hasattr(hp,'ring_num')):
    # 			if verbose:
    # 				print('WARNING: current healpy version does not support ring_num function. Added compatibility mode')
    # 			hp.ring_num=hp_comp.ring_num
    #
    # 	theta_min=np.pi/2.-ymax
    # 	theta_max=np.pi/2.-ymin
    # 	fpix,lpix=hp.ang2pix(nside,[theta_min,theta_max],[0.,2.*np.pi])
    # 	pixs=np.arange(fpix,lpix+1,dtype=np.int)
    #
    # 	theta,phi=hp.pix2ang(nside,pixs)
    # 	if xmin<0:
    # 		phi[phi>np.pi]=(phi[phi>np.pi]-2*np.pi)
    # 	good = (theta>=theta_min)*(theta<=theta_max)*(phi<=xmax)*(phi>=xmin)
    # 	obspix=pixs[good]
    #
    # 	### old method to retrive observed pixel in a patch.
    # 	### Changed to optimize it for large patches on 2014-10-09 by GF
    # 	#first_ring = hp.ring_num(nside,np.cos(np.pi/2.-ymax))
    # 	#last_ring = hp.ring_num(nside,np.cos(np.pi/2.-ymin))
    # 	#obspix = hp.in_ring(nside,first_ring,(2*np.pi + (xmin+xmax)/2.),abs(xmax-xmin)/2.)
    # 	#for i in range(first_ring+1,last_ring+1):
    # 	#	# in_ring healpy func to be rewritten in C for speed-up?
    # 	#	# the following commented line retrieved a wrong list of pixels. in_ring function
    # 	#	# appear to give back the pixel list [phi-dphi,phi+dphi] instad of what's written
    # 	#	# in the doc
    # 	#	#obspix = np.concatenate((obspix,hp.in_ring(nside,i,xmin,xmax-xmin)))
    # 	#	obspix = np.concatenate((obspix,hp.in_ring(nside,i,(2*np.pi + (xmin+xmax)/2.)%(2*np.pi),(xmax-xmin)/2.)))
    #
    # 	obspix.sort()
    #
    # 	return obspix

def write_dummy_map(filename='myfits_to_test_.fits', nside=16):
    """
    Write dummy file on disk for test purposes.

    Parameters
    ----------
    filename : string, optional
        Name of the output file (.fits)
    nside : int
        Resolution of the maps.

    Examples
    ----------
    >>> write_dummy_map()
    """
    nside = 16
    I, Q, U = np.random.rand(3, hp.nside2npix(nside))
    colnames = ['I', 'Q', 'U']
    HealpixFitsMap.write_healpix_cmbmap(filename,
                                        data=[I, Q, U],
                                        nside=nside,
                                        colnames=colnames)

def remove_test_data(has_id='_to_test_', silent=True):
    """
    Remove data with name containing the `has_id`.

    Parameters
    ----------
    has_id : string
        String included in filename(s) to remove.

    Examples
    ----------
    >>> file = open('file_to_erase_.txt', 'w')
    >>> file.close()
    >>> remove_test_data(has_id='_to_erase_', silent=False)
    Removing files:  ['file_to_erase_.txt']
    """
    fns = glob.glob('*' + has_id + '*')
    if not silent:
        print('Removing files: ', fns)
    for fn in fns:
        os.remove(fn)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
    remove_test_data(has_id='_to_test_', silent=True)
