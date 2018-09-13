import os
import unittest
from openql import openql as ql
from pycqed.measurement.openql_experiments import clifford_rb_oql as rb_oql


rootDir = os.path.dirname(os.path.realpath(__file__))
curdir = os.path.dirname(__file__)
config_fn = os.path.join(curdir, 'test_cfg_CCL.json')

output_dir = os.path.join(curdir, 'test_output')
ql.set_option('output_dir', output_dir)


class Test_cliff_rb_oql(unittest.TestCase):
    def test_single_qubit_rb_seq(self):
        p = rb_oql.randomized_benchmarking([0], platf_cfg=config_fn,
                                           program_name= 'single_q_RB',
                                           nr_cliffords=[1, 5], nr_seeds=1,
                                           cal_points=True)
        self.assertEqual(p.name, 'single_q_RB')

    def test_two_qubit_rb_seq(self):
        p = rb_oql.randomized_benchmarking([2, 0], platf_cfg=config_fn,
                                           program_name= 'two_q_RB',
                                           nr_cliffords=[1, 5], nr_seeds=1,
                                           cal_points=True)
        self.assertEqual(p.name, 'two_q_RB')

    def test_simultaneous_single_qubit_rb_seq(self):
        p = rb_oql.randomized_benchmarking([2, 0], platf_cfg=config_fn,
                                           program_name= 'sim_single_q_RB',
                                           nr_cliffords=[1, 5], nr_seeds=1,
                                           simultaneous_single_qubit_RB=True,
                                           cal_points=True)
        self.assertEqual(p.name, 'sim_single_q_RB')

