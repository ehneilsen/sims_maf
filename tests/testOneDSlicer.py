import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import warnings
import unittest
from lsst.sims.maf.slicers.oneDSlicer import OneDSlicer
from lsst.sims.maf.slicers.uniSlicer import UniSlicer

def makeDataValues(size=100, min=0., max=1., random=True):
    """Generate a simple array of numbers, evenly arranged between min/max, but (optional) random order."""
    datavalues = np.arange(0, size, dtype='float')
    datavalues *= (float(max) - float(min)) / (datavalues.max() - datavalues.min())
    datavalues += min
    if random:
        randorder = np.random.rand(size)
        randind = np.argsort(randorder)
        datavalues = datavalues[randind]
    datavalues = np.array(zip(datavalues), dtype=[('testdata', 'float')])
    return datavalues


class TestOneDSlicerSetup(unittest.TestCase):
    def setUp(self):
        self.testslicer = OneDSlicer(sliceColName='testdata')

    def tearDown(self):
        del self.testslicer
        self.testslicer = None

    def testSlicertype(self):
        """Test instantiation of slicer sets slicer type as expected."""
        self.assertEqual(self.testslicer.slicerName, self.testslicer.__class__.__name__)
        self.assertEqual(self.testslicer.slicerName, 'OneDSlicer')

    def testSetupSlicerBins(self):
        """Test setting up slicer using defined bins."""
        dvmin = 0
        dvmax = 1
        nvalues = 1000
        bins = np.arange(dvmin, dvmax, 0.1)
        dv = makeDataValues(nvalues, dvmin, dvmax, random=True)
        # Used right bins?
        self.testslicer = OneDSlicer(sliceColName='testdata', bins=bins)
        self.testslicer.setupSlicer(dv)
        np.testing.assert_equal(self.testslicer.bins, bins)
        self.assertEqual(self.testslicer.nslice, len(bins)-1)

    def testSetupSlicerNbins(self):
        """Test setting up slicer using bins as integer."""
        for nvalues in (100, 1000, 10000):
            for nbins in (5, 25, 75):
                dvmin = 0
                dvmax = 1
                dv = makeDataValues(nvalues, dvmin, dvmax, random=False)
                # Right number of bins?
                # expect two more 'bins' to accomodate padding on left/right
                self.testslicer = OneDSlicer(sliceColName='testdata', bins=nbins)
                self.testslicer.setupSlicer(dv)
                self.assertEqual(self.testslicer.nslice, nbins)
                # Bins of the right size? 
                bindiff = np.diff(self.testslicer.bins)
                expectedbindiff = (dvmax - dvmin) / float(nbins)
                np.testing.assert_allclose(bindiff, expectedbindiff)

    def testSetupSlicerNbinsZeros(self):
        """Test what happens if give slicer test data that is all single-value."""
        dv = np.zeros(100, float)
        dv = np.array(zip(dv), dtype=[('testdata', 'float')])
        nbins = 10
        self.testslicer = OneDSlicer(sliceColName='testdata', bins=nbins)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.testslicer.setupSlicer(dv)
            self.assertTrue("creasing binMax" in str(w[-1].message))
        self.assertEqual(self.testslicer.nslice, nbins)

    def testSetupSlicerEquivalent(self):
        """Test setting up slicer using defined bins and nbins is equal where expected."""
        dvmin = 0
        dvmax = 1
        for nbins in (20, 50, 100, 105):
            bins = makeDataValues(nbins+1, dvmin, dvmax, random=False)
            bins = bins['testdata']
            for nvalues in (100, 1000, 10000):
                dv = makeDataValues(nvalues, dvmin, dvmax, random=True)
                self.testslicer = OneDSlicer(sliceColName='testdata', bins=bins)
                self.testslicer.setupSlicer(dv)
                np.testing.assert_allclose(self.testslicer.bins, bins)

    def testSetupSlicerLimits(self):
        """Test setting up slicer using binMin/Max."""
        binMin = 0
        binMax = 1
        nbins = 10
        dvmin = -.5
        dvmax = 1.5
        dv = makeDataValues(1000, dvmin, dvmax, random=True)
        self.testslicer = OneDSlicer(sliceColName='testdata',
                                     binMin=binMin, binMax=binMax, bins=nbins)
        self.testslicer.setupSlicer(dv)
        self.assertAlmostEqual(self.testslicer.bins.min(), binMin)
        self.assertAlmostEqual(self.testslicer.bins.max(), binMax)

    def testSetupSlicerBinsize(self):
        """Test setting up slicer using binsize."""
        dvmin = 0
        dvmax = 1
        dv = makeDataValues(1000, dvmin, dvmax, random=True)
        # Test basic use.
        binsize=0.5
        self.testslicer = OneDSlicer(sliceColName='testdata', binsize=binsize)
        self.testslicer.setupSlicer(dv)
        # When binsize is specified, oneDslicer adds an extra bin to first/last spots.
        self.assertEqual(self.testslicer.nslice, (dvmax-dvmin)/binsize+2)
        # Test that warning works.
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.testslicer = OneDSlicer(sliceColName='testdata',bins=200,binsize=binsize)
            self.testslicer.setupSlicer(dv)
            # Verify some things
            self.assertTrue("binsize" in str(w[-1].message))


    def testSetupSlicerFreedman(self):
        """Test that setting up the slicer using bins=None works."""
        dvmin = 0
        dvmax = 1
        dv = makeDataValues(1000, dvmin, dvmax, random=True)
        self.testslicer = OneDSlicer(sliceColName='testdata', bins=None)
        self.testslicer.setupSlicer(dv)
        # How many bins do you expect from optimal binsize?
        from lsst.sims.maf.utils import optimalBins
        bins = optimalBins(dv['testdata'])
        np.testing.assert_equal(self.testslicer.nslice, bins)


class TestOneDSlicerIteration(unittest.TestCase):
    def setUp(self):
        self.testslicer = OneDSlicer(sliceColName='testdata')
        dvmin = 0
        dvmax = 1
        nvalues = 1000
        self.bins = np.arange(dvmin, dvmax, 0.01)
        dv = makeDataValues(nvalues, dvmin, dvmax, random=True)
        self.testslicer = OneDSlicer(sliceColName='testdata',bins=self.bins)
        self.testslicer.setupSlicer(dv)

    def tearDown(self):
        del self.testslicer
        self.testslicer = None

    def testIteration(self):
        """Test iteration."""
        for i,(s, b) in enumerate(zip(self.testslicer, self.bins)):
            self.assertEqual(s['slicePoint']['sid'], i)
            self.assertEqual(s['slicePoint']['binLeft'], b)

    def testGetItem(self):
        """Test that can return an individual indexed values of the slicer."""
        for i in ([0, 10, 20]):
            self.assertEqual(self.testslicer[i]['slicePoint']['sid'], i)
            self.assertEqual(self.testslicer[i]['slicePoint']['binLeft'], self.bins[i])

class TestOneDSlicerEqual(unittest.TestCase):
    def setUp(self):
        self.testslicer = OneDSlicer(sliceColName='testdata')

    def tearDown(self):
        del self.testslicer
        self.testslicer = None

    def testEquivalence(self):
        """Test equals method."""
        # Note that two OneD slicers will be considered equal if they are both the same kind of
        # slicer AND have the same bins.
        # Set up self..
        dvmin = 0
        dvmax = 1
        nvalues = 1000
        bins = np.arange(dvmin, dvmax, 0.01)
        dv = makeDataValues(nvalues, dvmin, dvmax, random=True)
        self.testslicer = OneDSlicer(sliceColName='testdata', bins=bins)
        self.testslicer.setupSlicer(dv)
        # Set up another slicer to match (same bins, although not the same data).
        dv2 = makeDataValues(nvalues+100, dvmin, dvmax, random=True)
        testslicer2 = OneDSlicer(sliceColName='testdata', bins=bins)
        testslicer2.setupSlicer(dv2)
        self.assertEqual(self.testslicer, testslicer2)
        # Set up another slicer that should not match (different bins)
        dv2 = makeDataValues(nvalues, dvmin+1, dvmax+1, random=True)
        testslicer2 = OneDSlicer(sliceColName='testdata', bins=len(bins))
        testslicer2.setupSlicer(dv2)
        self.assertNotEqual(self.testslicer, testslicer2)
        # Set up a different kind of slicer that should not match.
        dv2 = makeDataValues(100, 0, 1, random=True)
        testslicer2 = UniSlicer()
        testslicer2.setupSlicer(dv2)
        self.assertNotEqual(self.testslicer, testslicer2)


class TestOneDSlicerSlicing(unittest.TestCase):
    def setUp(self):
        self.testslicer = OneDSlicer(sliceColName='testdata')

    def tearDown(self):
        del self.testslicer
        self.testslicer = None

    def testSlicing(self):
        """Test slicing."""
        dvmin = 0
        dvmax = 1
        nbins = 100
        binsize = (dvmax - dvmin) / (float(nbins))
        # Test that testbinner raises appropriate error before it's set up (first time)
        self.assertRaises(NotImplementedError, self.testslicer._sliceSimData, 0)
        for nvalues in (1000, 10000, 100000):
            dv = makeDataValues(nvalues, dvmin, dvmax, random=True)
            self.testslicer = OneDSlicer(sliceColName='testdata', bins=nbins)
            self.testslicer.setupSlicer(dv)
            sum = 0
            for i, s in enumerate(self.testslicer):
                idxs = s['idxs']
                dataslice = dv['testdata'][idxs]
                sum += len(idxs)
                if len(dataslice)>0:
                    self.assertTrue(len(dataslice), nvalues/float(nbins))
                else:
                    self.assertTrue(len(dataslice) > 0,
                            'Data in test case expected to always be > 0 len after slicing')
            self.assertTrue(sum, nvalues)

class TestOneDSlicerHistogram(unittest.TestCase):
    def setUp(self):
        self.testslicer = OneDSlicer(sliceColName='testdata')

    def tearDown(self):
        del self.testslicer
        self.testslicer = None

    def testHistogram(self):
        """Test that histogram values match those generated by numpy hist,
        with the exception that OneDSlicer now adds a first/last bin to extend the xrange."""
        dvmin = 0
        dvmax = 1
        for nbins in [10, 20, 30, 75, 100, 33]:
            for nvalues in [1000, 10000, 250000]:
                dv = makeDataValues(nvalues, dvmin, dvmax, random=True)
                self.testslicer = OneDSlicer(sliceColName='testdata', bins=nbins)
                self.testslicer.setupSlicer(dv)
                metricval = np.zeros(len(self.testslicer), 'float')
                for i, b in enumerate(self.testslicer):
                    idxs = b['idxs']
                    metricval[i] = len(idxs)
                numpycounts, numpybins = np.histogram(dv['testdata'], bins=nbins)
                np.testing.assert_almost_equal(numpybins, self.testslicer.bins,
                                        err_msg='Numpy bins do not match testslicer bins')
                np.testing.assert_almost_equal(numpycounts, metricval,
                                        err_msg='Numpy histogram counts do not match testslicer counts')

    def testPlotting(self):
        """Test plotting."""
        dvmin = 0
        dvmax = 1
        nbins = 100
        nvalues = 10000
        dv = makeDataValues(nvalues, dvmin, dvmax, random=True)
        testslicer = OneDSlicer(sliceColName='testdata', bins = nbins)
        testslicer.setupSlicer(dv)
        metricvals = ma.MaskedArray(data = np.zeros(len(testslicer), float),
                                    mask = np.zeros(len(testslicer), bool),
                                    fill_value = testslicer.badval)
        for i, s in enumerate(testslicer):
            idxs = s['idxs']
            metricvals.data[i] = len(idxs)
        testslicer.plotBinnedData(metricvals, xlabel='xrange', ylabel='count')
        #plt.show()

if __name__ == "__main__":
    suitelist = []
    suitelist.append(unittest.TestLoader().loadTestsFromTestCase(TestOneDSlicerSetup))
    suitelist.append(unittest.TestLoader().loadTestsFromTestCase(TestOneDSlicerIteration))
    suitelist.append(unittest.TestLoader().loadTestsFromTestCase(TestOneDSlicerEqual))
    suitelist.append(unittest.TestLoader().loadTestsFromTestCase(TestOneDSlicerSlicing))
    suitelist.append(unittest.TestLoader().loadTestsFromTestCase(TestOneDSlicerHistogram))
    suite = unittest.TestSuite(suitelist)
    unittest.TextTestRunner(verbosity=2).run(suite)
    #unittest.main()
