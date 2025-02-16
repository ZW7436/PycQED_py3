import unittest
import numpy as np
import pycqed.instrument_drivers.virtual_instruments.virtual_AWG8 as v8

from pycqed.instrument_drivers.meta_instrument.LutMans import mw_lutman as mwl
from pycqed.measurement.waveform_control_CC import waveform as wf
from pycqed.instrument_drivers.meta_instrument.LutMans.base_lutman import \
    get_redundant_codewords


class Test_MW_LutMan(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.AWG = v8.VirtualAWG8('DummyAWG8')

        self.AWG8_MW_LutMan = mwl.AWG8_MW_LutMan('MW_LutMan')
        self.AWG8_MW_LutMan.AWG(self.AWG.name)
        self.AWG8_MW_LutMan.channel_I(1)
        self.AWG8_MW_LutMan.channel_Q(2)
        self.AWG8_MW_LutMan.mw_modulation(100e6)
        self.AWG8_MW_LutMan.sampling_rate(2.4e9)
        self.AWG8_MW_LutMan.set_default_lutmap()

        self.AWG8_VSM_MW_LutMan = mwl.AWG8_VSM_MW_LutMan('MW_LutMan_VSM')
        self.AWG8_VSM_MW_LutMan.AWG(self.AWG.name)
        self.AWG8_VSM_MW_LutMan.channel_GI(1)
        self.AWG8_VSM_MW_LutMan.channel_GQ(2)
        self.AWG8_VSM_MW_LutMan.channel_DI(3)
        self.AWG8_VSM_MW_LutMan.channel_DQ(4)
        self.AWG8_VSM_MW_LutMan.mw_modulation(100e6)
        self.AWG8_VSM_MW_LutMan.sampling_rate(2.4e9)
        self.AWG8_VSM_MW_LutMan.set_default_lutmap()

        self.CBox_MW_LutMan = mwl.CBox_MW_LutMan('CBox_MW_LutMan')
        self.QWG_MW_LutMan = mwl.QWG_MW_LutMan('QWG_MW_LutMan')

    def test__program_hash_differs_AWG8_lutman(self):

        # set to a random value to ensure different
        self.AWG8_MW_LutMan._awgs_mw_sequencer_program_expected_hash(351340)
        hash_differs = self.AWG8_MW_LutMan._program_hash_differs()
        self.assertTrue(hash_differs)

        self.AWG8_MW_LutMan._update_expected_program_hash()
        hash_differs = self.AWG8_MW_LutMan._program_hash_differs()
        self.assertFalse(hash_differs)

    def test__program_hash_differs_AWG8_VSM_lutman(self):

        # set to a random value to ensure different
        self.AWG8_VSM_MW_LutMan._awgs_mwG_sequencer_program_expected_hash(
            351340)
        hash_differs = self.AWG8_VSM_MW_LutMan._program_hash_differs()
        self.assertTrue(hash_differs)

        self.AWG8_VSM_MW_LutMan._update_expected_program_hash()
        hash_differs = self.AWG8_VSM_MW_LutMan._program_hash_differs()
        self.assertFalse(hash_differs)

    def test__program_hash_updated_when_loading_program(self):
        self.AWG8_MW_LutMan._awgs_mw_sequencer_program_expected_hash(351340)
        hash_differs = self.AWG8_MW_LutMan._program_hash_differs()
        self.assertTrue(hash_differs)

        self.AWG8_MW_LutMan.load_waveforms_onto_AWG_lookuptable()
        hash_differs = self.AWG8_MW_LutMan._program_hash_differs()
        self.assertFalse(hash_differs)

    def test_uploading_standard_pulses(self):
        # Tests that all waveforms are present and no error is raised.
        self.AWG8_MW_LutMan.load_waveforms_onto_AWG_lookuptable()
        expected_wf = wf.mod_gauss(
            amp=self.AWG8_MW_LutMan.mw_amp180(),
            sigma_length=self.AWG8_MW_LutMan.mw_gauss_width(),
            f_modulation=self.AWG8_MW_LutMan.mw_modulation(),
            sampling_rate=self.AWG8_MW_LutMan.sampling_rate(), phase=0,
            motzoi=self.AWG8_MW_LutMan.mw_motzoi())[0]

        uploaded_wf = self.AWG.get('wave_ch1_cw001')
        np.testing.assert_array_almost_equal(expected_wf, uploaded_wf)

        expected_wf_spec = wf.block_pulse(
            length=self.AWG8_MW_LutMan.spec_length(),
            amp=self.AWG8_MW_LutMan.spec_amp(),
            sampling_rate=self.AWG8_MW_LutMan.sampling_rate(),
            delay=0, phase=0)[0]
        uploaded_wf = self.AWG.get('wave_ch1_cw008')
        np.testing.assert_array_almost_equal(expected_wf_spec, uploaded_wf)

    def test_lut_mapping_AWG8(self):
        self.AWG8_MW_LutMan.set_default_lutmap()
        expected_dict = {
            'rY90': ('wave_ch1_cw004',
                     'wave_ch2_cw004'),
            'I': ('wave_ch1_cw000',
                  'wave_ch2_cw000'),
            'rY180': ('wave_ch1_cw002',
                      'wave_ch2_cw002'),
            'rX180': ('wave_ch1_cw001',
                      'wave_ch2_cw001'),
            'rPhi90': ('wave_ch1_cw007',
                       'wave_ch2_cw007'),
            'rX90': ('wave_ch1_cw003',
                     'wave_ch2_cw003'),
            'rYm90': ('wave_ch1_cw006',
                      'wave_ch2_cw006'),
            'rXm90': ('wave_ch1_cw005',
                      'wave_ch2_cw005'),
            'spec': ('wave_ch1_cw008',
                     'wave_ch2_cw008')}
        # Does not check the full lutmap
        dict_contained_in(expected_dict, self.AWG8_MW_LutMan.LutMap())

    def test_lut_mapping_CBox(self):
        self.CBox_MW_LutMan.set_default_lutmap()
        expected_dict = {'I': 0,
                         'rX180': 1,
                         'rY180': 2,
                         'rX90': 3,
                         'rY90': 4,
                         'rXm90': 5,
                         'rYm90': 6,
                         'rPhi90': 7}

        self.assertDictEqual.__self__.maxDiff = None
        self.assertDictEqual(expected_dict, self.CBox_MW_LutMan.LutMap())

    def test_lut_mapping_AWG8_VSM(self):
        self.AWG8_VSM_MW_LutMan.set_default_lutmap()
        expected_dict = {
            'rY90': ('wave_ch1_cw004',
                     'wave_ch2_cw004',
                     'wave_ch3_cw004',
                     'wave_ch4_cw004'),
            'I': ('wave_ch1_cw000',
                  'wave_ch2_cw000',
                  'wave_ch3_cw000',
                  'wave_ch4_cw000'),
            'rY180': ('wave_ch1_cw002',
                      'wave_ch2_cw002',
                      'wave_ch3_cw002',
                      'wave_ch4_cw002'),
            'rX180': ('wave_ch1_cw001',
                      'wave_ch2_cw001',
                      'wave_ch3_cw001',
                      'wave_ch4_cw001'),
            'rPhi90': ('wave_ch1_cw007',
                       'wave_ch2_cw007',
                       'wave_ch3_cw007',
                       'wave_ch4_cw007'),
            'rX90': ('wave_ch1_cw003',
                     'wave_ch2_cw003',
                     'wave_ch3_cw003',
                     'wave_ch4_cw003'),
            'rYm90': ('wave_ch1_cw006',
                      'wave_ch2_cw006',
                      'wave_ch3_cw006',
                      'wave_ch4_cw006'),
            'rXm90': ('wave_ch1_cw005',
                      'wave_ch2_cw005',
                      'wave_ch3_cw005',
                      'wave_ch4_cw005'),
            'spec': ('wave_ch1_cw008',
                     'wave_ch2_cw008',
                     'wave_ch3_cw008',
                     'wave_ch4_cw008')}
        # Does not check the full lutmap
        dict_contained_in(expected_dict, self.AWG8_VSM_MW_LutMan.LutMap())

    def test_realtime_loading_square_wf_AWG8_VSM(self):
        self.AWG8_VSM_MW_LutMan.load_waveform_realtime('square', wf_nr=3)

    def test_uploading_standard_pulses_AWG8_VSM(self):
        # Tests that all waveforms are present and no error is raised.
        self.AWG8_VSM_MW_LutMan.load_waveforms_onto_AWG_lookuptable()
        expected_wfs = wf.mod_gauss_VSM(
            amp=self.AWG8_VSM_MW_LutMan.mw_amp180(),
            sigma_length=self.AWG8_VSM_MW_LutMan.mw_gauss_width(),
            f_modulation=self.AWG8_VSM_MW_LutMan.mw_modulation(),
            sampling_rate=self.AWG8_VSM_MW_LutMan.sampling_rate(), phase=0,
            motzoi=self.AWG8_VSM_MW_LutMan.mw_motzoi())

        for i in range(4):
            uploaded_wf = self.AWG.get('wave_ch{}_cw001'.format(i+1))
            np.testing.assert_array_almost_equal(expected_wfs[i], uploaded_wf)

    @classmethod
    def tearDownClass(self):
        for inststr in list(self.AWG._all_instruments):
            try:
                inst = self.AWG.find_instrument(inststr)
                inst.close()
            except KeyError:
                pass


class Test_LutMan_Utils(unittest.TestCase):
    def test_get_redundant_codewords(self):
        target_cw = 5
        red_cws_A = get_redundant_codewords(target_cw, 4, 0)
        for cw in red_cws_A:
            print(bin(cw))
            self.assertEqual(cw & 15, target_cw)
        self.assertEqual(len(red_cws_A), 2**4)

        red_cws_B = get_redundant_codewords(target_cw, 4, 4)
        for cw in red_cws_B:
            print(bin(cw))
            self.assertEqual((cw & (256-16)) >> 4, target_cw)
        self.assertEqual(len(red_cws_B), 2**4)


def dict_contained_in(subset, superset):
    if subset.items() <= superset.items():
        return True
    else:
        raise ValueError
