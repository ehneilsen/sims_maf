import numpy as np
from .baseMetric import BaseMetric
import lsst.sims.maf.utils as mafUtils
import lsst.sims.utils as utils


__all__ = ['DcrPrecisionMetric']


class DcrPrecisionMetric(BaseMetric):
    """Determine how precise a DCR correction could be made

    Parameters
    ----------
    atm_err : float
        Minimum error in photometry centroids introduced by the atmosphere (arcseconds). Default 0.01.
    """

    def __init__(self, metricName='DCRprecision', seeingCol='seeingFwhmGeom',
                 m5Col='fiveSigmaDepth', HACol='HA', PACol='paraAngle',
                 filterCol='filter', atm_err=0.01, SedTemplate='flat',
                 rmag=20., **kwargs):

        self.m5Col = m5Col
        self.filterCol = filterCol
        self.PACol = PACol
        self.seeingCol = seeingCol
        self.mags = {}
        self.filters = ['u', 'g', 'r', 'i', 'z', 'y']
        if SedTemplate == 'flat':
            for f in self.filters:
                self.mags[f] = rmag
        else:
            self.mags = utils.stellarMags(SedTemplate, rmag=rmag)
        cols = ['ra_dcr_amp', 'dec_dcr_amp', seeingCol, m5Col, filterCol, 'zenithDistance', PACol]
        units = 'arcseconds'
        self.atm_err = atm_err
        super(DcrPrecisionMetric, self).__init__(cols, metricName=metricName, units=units,
                                                 **kwargs)

    def run(self, dataSlice, slicePoint=None):

        snr = np.zeros(len(dataSlice), dtype='float')
        for filt in self.filters:
            inFilt = np.where(dataSlice[self.filterCol] == filt)
            snr[inFilt] = mafUtils.m52snr(self.mags[filt], dataSlice[self.m5Col][inFilt])

        position_errors = np.sqrt(mafUtils.astrom_precision(dataSlice[self.seeingCol], snr)**2 +
                                  self.atm_err**2)

        x_coord = np.tan(dataSlice['zenithDistance'])*np.sin(dataSlice[self.PACol])
        # Things should be the same for RA and dec.
        # Now I want to compute the error if I interpolate/extrapolate to +/-1.

        # function is of form, y=ax. a=y/x. da = dy/x.
        # Only strictly true if we know the unshifted position. But this should be a reasonable approx.
        slope_uncerts = position_errors/x_coord
        total_slope_uncert = 1./np.sqrt(np.sum(1./slope_uncerts**2))

        # So, this will be the uncertainty in the RA or Dec offset at x= +/- 1.
        result = total_slope_uncert

        return result
