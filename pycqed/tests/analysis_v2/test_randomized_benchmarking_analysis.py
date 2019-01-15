import unittest
from matplotlib import rcParams
import pycqed as pq
import os
from pycqed.analysis_v2 import measurement_analysis as ma


class Test_RBAnalysis(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.datadir = os.path.join(pq.__path__[0], 'tests', 'test_data')
        ma.a_tools.datadir = self.datadir
        # to have fast tests
        rcParams['figure.dpi'] = 80


    def test_single_qubit_RB_analysis(self):
        a = ma.RandomizedBenchmarking_SingleQubit_Analysis(
            t_start='20180601_135117',
            classification_method='rates', rates_ch_idx=1)

        leak_pars = a.fit_res['leakage_decay'].params
        L1 = leak_pars['L1'].value
        L2 = leak_pars['L2'].value
        self.assertAlmostEqual(L1*100, 0.010309, places=2)
        self.assertAlmostEqual(L2*100, 0.37824, places=2)

        rb_pars = a.fit_res['rb_decay'].params
        F = rb_pars['F'].value
        self.assertAlmostEqual(F, 0.997895, places=4)

    def test_single_qubit_RB_analysis_missing_f_cal(self):
        a = ma.RandomizedBenchmarking_SingleQubit_Analysis(
            t_start='20180815_150417',
            classification_method='rates', rates_ch_idx=0,
            ignore_f_cal_pts=True)

        rb_pars = a.fit_res['rb_decay'].params
        eps = rb_pars['eps'].value
        self.assertAlmostEqual(eps, 0.00236731, places=4)

    def test_two_qubit_RB_analysis_missing_f_cal(self):
        a = ma.RandomizedBenchmarking_TwoQubit_Analysis(
            t_start='20180727_182529',
            classification_method='rates', rates_ch_idxs=[1, 3])

        leak_pars = a.fit_res['leakage_decay'].params
        L1 = leak_pars['L1'].value
        L2 = leak_pars['L2'].value
        self.assertAlmostEqual(L1, 0.029, places=2)
        self.assertAlmostEqual(L2, 0.040, places=2)

        rb_pars = a.fit_res['rb_decay'].params
        eps = rb_pars['eps'].value
        self.assertAlmostEqual(eps, 0.205, places=3)

        rb_pars = a.fit_res['rb_decay_simple'].params
        eps = rb_pars['eps'].value
        self.assertAlmostEqual(eps, 0.157, places=3)

    def test_UnitarityBenchmarking_TwoQubit_Analysis(self):
        a = ma.UnitarityBenchmarking_TwoQubit_Analysis(
            t_start='20180926_110112',
            classification_method='rates', rates_ch_idxs=[0, 3],
            nseeds=200)
        u_dec = a.fit_res['unitarity_decay'].params
        self.assertAlmostEqual(u_dec['u'].value, 0.7354, places=3)
        self.assertAlmostEqual(u_dec['eps'].value, 0.1068, places=3)




class Test_CharRBAnalysis():
    def test_char_rb_extract_data(self):

        ts = '20181129_170623'
        a = ma.CharacterBenchmarking_TwoQubit_Analysis(t_start=ts)
        df = a.raw_data_dict['df']
        assert df.shape == (135, 12)
        assert {'pauli', 'interleaving_cl', 'ncl'}<=set(df.keys())

        char_df = a.proc_data_dict['char_df']
        assert {'P00', 'P01', 'P10', 'P11',
                'P00_CZ', 'P01_CZ', 'P10_CZ', 'P11_CZ',
                'C1', 'C2', 'C12', 'C1_CZ', 'C2_CZ', 'C12_CZ'} \
                    <= set(char_df.keys())

