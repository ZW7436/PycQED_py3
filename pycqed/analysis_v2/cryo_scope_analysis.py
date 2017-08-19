import pycqed.analysis_v2.base_analysis as ba
import pycqed.measurement.waveform_control_CC.waveform as wf
import pycqed.analysis.fitting_models as fit_mods
import numpy as np
from numpy.fft import fft, ifft, fftfreq


class DistortionFineAnalysis(ba.BaseDataAnalysis):
    '''
    Analysis for the enhanced cryogenic oscilloscpe.
    '''
    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):
        if options_dict is None:
            options_dict = dict()
        options_dict['scan_label'] = 'distortion_scope_fine'
        options_dict['tight_fig'] = False
        options_dict['apply_default_fig_settings'] = False

        super().__init__(t_start=t_start, t_stop=t_stop,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)

        # Extract metadata to know where to extract the parameters from
        self.params_dict = {
            'qubit_name':
                'Experimental Data.Experimental Metadata.qubit_name',
            'QWG_channel':
                'Experimental Data.Experimental Metadata.QWG_channel',
            'flux_LutMan':
                'Experimental Data.Experimental Metadata.flux_LutMan',
        }
        self.numeric_params = []
        self.extract_data()

        # Now actually extract the parameters and the data
        self.params_dict = {
            # Data
            'xlabel': 'sweep_name',
            'xunit': 'sweep_unit',
            'measurementstring': 'measurementstring',
            'sweep_points': 'sweep_points',
            'value_names': 'value_names',
            'value_units': 'value_units',
            'measured_values': 'measured_values',

            # Pulse parameters
            'gauss_sigma':
                '{}.S_gauss_sigma'.format(self.data_dict['flux_LutMan'][0]),
            'gauss_amp': '{}.S_amp'.format(self.data_dict['flux_LutMan'][0]),
            'wave_dict_unit':
                '{}.wave_dict_unit'.format(self.data_dict['flux_LutMan'][0]),
            'sampling_rate':
                '{}.sampling_rate'.format(self.data_dict['flux_LutMan'][0]),
            'QWG_amp':
                'QWG.ch{}_amp'.format(self.data_dict['QWG_channel'][0]),
            'distortions_amp':
                '{}.F_amp'.format(self.data_dict['flux_LutMan'][0]),

            # Qubit parameters
            'f_max': '{}.f_max'.format(self.data_dict['qubit_name'][0]),
            'E_c': '{}.E_c'.format(self.data_dict['qubit_name'][0]),
            'V_offset': '{}.V_offset'.format(self.data_dict['qubit_name'][0]),
            'V_per_phi0':
                '{}.V_per_phi0'.format(self.data_dict['qubit_name'][0]),
            'asymmetry':
                '{}.asymmetry'.format(self.data_dict['qubit_name'][0]),
        }
        self.numeric_params = [
            'gauss_sigma',
            'gauss_amp',
            'sampling_rate',
            'QWG_amp',
            'distortions_amp',
            'f_max',
            'E_c',
            'V_offset',
            'V_per_phi0',
            'asymmetry',
        ]

        if auto:
            self.run_analysis()

    def process_data(self):
        # Convert lists of duplicated params to floats
        for k in self.numeric_params:
            self.data_dict[k] = self.data_dict[k][1]

        # Background
        cos = (self.data_dict['measured_values'][0][0, ::2] - 0.5) * 2
        sin = (self.data_dict['measured_values'][0][0, 1::2] - 0.5) * 2
        bg_phase = np.unwrap(np.arctan2(sin, cos))
        self.data_dict['background phase'] = np.mean(bg_phase)
        n = fft(bg_phase)
        self.data_dict['noise power spectrum'] = np.conj(n) * n

        # Data
        self.data_dict['cos'] = (
            self.data_dict['measured_values'][1][0, ::2] - 0.5) * 2
        self.data_dict['sin'] = (
            self.data_dict['measured_values'][1][0, 1::2] - 0.5) * 2

        self.data_dict['raw phase'] = np.arctan2(self.data_dict['sin'],
                                                 self.data_dict['cos'])
        # Unwrap phase back-to-front, because it makes more sense to assume
        # it's closer to zero at later times.
        self.data_dict['phase'] = (
            np.unwrap(self.data_dict['raw phase'][::-1])[::-1] -
            self.data_dict['background phase'])

        # After unwrapping we can convert phases to degrees
        self.data_dict['raw phase'] = np.rad2deg(self.data_dict['raw phase'])
        self.data_dict['phase'] = np.rad2deg(self.data_dict['phase'])
        self.data_dict['background phase'] = np.rad2deg(
            self.data_dict['background phase'])

        self.data_dict['tau'] = self.data_dict['sweep_points'][1][::2]

        # Calculate integral of the scoping pulse
        data_dt = (self.data_dict['tau'][1] -
                   self.data_dict['tau'][0])
        gauss_pulse = wf.gauss_pulse(
            self.data_dict['gauss_amp'],
            self.data_dict['gauss_sigma'],
            nr_sigma=4,
            sampling_rate=data_dt,
            axis='x', phase=0, motzoi=0, delay=0)[0]  # Returns I and Q

        if self.data_dict['wave_dict_unit'] == 'frac':
            # Convert to volts
            gauss_pulse *= self.data_dict['QWG_amp'] / 2

        # Add zeros to front and back of data because the signal does not
        # start at tau = 0.
        # t0: time from start to center of scoping pulse
        t0 = self.data_dict['gauss_sigma'] * 2
        t0_samples = int(np.round(t0 / data_dt))

        y = np.concatenate((
            np.zeros(t0_samples),
            self.data_dict['phase'],
            np.zeros(t0_samples)))
        N = np.concatenate((
            np.zeros(t0_samples),
            self.data_dict['noise power spectrum'],
            np.zeros(t0_samples)))
        self.y = y

        # Calculate convolution kernel
        # Kernel needs to be sampled at the same rate as data.

        h = 360 * fit_mods.Qubit_dac_sensitivity(
            dac_voltage=gauss_pulse,
            f_max=self.data_dict['f_max'],
            E_c=self.data_dict['E_c'],
            dac_sweet_spot=self.data_dict['V_offset'],
            V_per_phi0=self.data_dict['V_per_phi0'],
            asymmetry=self.data_dict['asymmetry'])
        self.h = h

        # Note that we assume now that the magnitude of the phase error is
        # smaller than 180 degrees, i.e. we assume the phase has not wrapped
        # due to distortions.
        h = np.hstack((h, np.zeros(len(y) - len(h))))
        # Abs of fft, because we want the spectrum of a gauss window centered
        # around zero. Note: f real, symmetric => fft(f) real, symmetric.
        freqs = fftfreq(len(h), d=data_dt)
        H = np.abs(fft(h))
        x = np.real(ifft(fft(y) / H)) * (freqs[1] - freqs[0])
        # Wiener deconvolution
        # x = np.real(ifft(fft(y) * np.conj(H) /
        #                  (np.conj(H) * H + N / (np.conj(y) * y))))

        self.data_dict['tau'] += t0
        self.data_dict['dV'] = x[t0_samples:-t0_samples]

    def prepare_plots(self):
        self.plot_dicts['raw data'] = {
            'plotfn': self.plot_line,
            'title': self.timestamps[0] + ' raw data',
            'xvals': self.data_dict['tau'],
            'xlabel': self.data_dict['xlabel'][1],
            'xunit': self.data_dict['xunit'][1][0],
            'yvals': [self.data_dict['cos'], self.data_dict['sin']],
            'multiple': True,
            'setlabel': ['cos', 'sin'],
            'do_legend': True,
        }

        self.plot_dicts['raw_phase'] = {
            'plotfn': self.plot_line,
            'title': self.timestamps[0] + ' raw phase',
            'xvals': self.data_dict['tau'],
            'xlabel': self.data_dict['xlabel'][1],
            'xunit': self.data_dict['xunit'][1][0],
            'yvals': self.data_dict['raw phase'],
            'ylabel': 'phase',
            'yunit': 'deg',
        }

        self.plot_dicts['phase'] = {
            'plotfn': self.plot_line,
            'title': self.timestamps[0] + ' phase',
            'xvals': self.data_dict['tau'],
            'xlabel': self.data_dict['xlabel'][1],
            'xunit': self.data_dict['xunit'][1][0],
            'yvals': self.data_dict['phase'],
            'ylabel': 'phase',
            'yunit': 'deg',
        }

        self.plot_dicts['dV'] = {
            'plotfn': self.plot_line,
            'title': self.timestamps[0] + ' $\\delta V$',
            'xvals': self.data_dict['tau'][:len(self.data_dict['dV'])],
            'xlabel': self.data_dict['xlabel'][1],
            'xunit': self.data_dict['xunit'][1][0],
            'yvals': self.data_dict['dV'],
            'ylabel': '$\\delta V$',
            'yunit': 'V',
        }

    def run_fitting(self):
        pass
