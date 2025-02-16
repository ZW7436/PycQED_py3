"""
This file reads in a pygsti dataset file and converts it to a valid
OpenQL sequence.
"""

from os.path import join

from pycqed.measurement.randomized_benchmarking import \
    randomized_benchmarking as rb
from pycqed.measurement.openql_experiments import openql_helpers as oqh
from pycqed.measurement.randomized_benchmarking.two_qubit_clifford_group \
    import SingleQubitClifford, TwoQubitClifford


def randomized_benchmarking(qubits: list, platf_cfg: str,
                            nr_cliffords, nr_seeds: int,
                            net_cliffords: list=[0],
                            max_clifford_idx: int=11520,
                            simultaneous_single_qubit_RB=False, 
                            initialize: bool=True,
                            interleaving_cliffords=[None],
                            program_name: str='randomized_benchmarking',
                            cal_points: bool=True,
                            f_state_cal_pts: bool=True,
                            recompile: bool=True):
    '''
    Input pars:
        qubits:         list of ints specifying qubit indices.
                        based on the length this function detects if it should
                        generate a single or two qubit RB sequence.
        platf_cfg:      filename of the platform config file
        nr_cliffords:   list nr_cliffords for which to generate RB seqs
        nr_seeds:       int  nr_seeds for which to generate RB seqs
        net_cliffords:  list of ints index of net clifford the sequence
                        should perform. See examples below on how to use this.
                            Important clifford indices
                                0 -> Idx
                                3 -> rx180
                                3*24+3 -> {rx180 q0 | rx180 q1}
                                4368 -> CZ 

        max_clifford_idx:   Set's the maximum clifford group index from which 
                        to sample random cliffords. 
                            Important clifford indices 
                                24 -> Size of the single qubit Cl group 
                                576  -> Size of the single qubit like class 
                                    contained in the two qubit Cl group
                                11520 -> Size of the complete two qubit Cl group

        initialize:     if True initializes qubits to 0, disable for restless
            tuning
        program_name:           some string that can be used as a label.
        cal_points:     bool whether to replace the last two elements with
                        calibration points, set to False if you want
                        to measure a single element (for e.g. optimization)

        recompile:      True -> compiles the program,
                        'as needed' -> compares program to timestamp of config
                            and existence, if required recompile.
                        False -> compares program to timestamp of config.
                            if compilation is required raises a ValueError

                        If the program is more recent than the config
                        it returns an empty OpenQL program object with
                        the intended filename that can be used to upload the
                        previously compiled file.

    Returns:
        p:              OpenQL Program object

    ***************************************************************************
    Examples:
        1. Single qubit randomized benchmarking:

            p = cl_oql.randomized_benchmarking(
                qubits=[0],

                nr_cliffords=[2, 4, 8, 16, 32, 128, 512, 1024],
                nr_seeds=1,  # for CCL memory reasons
                platf_cfg=qubit.cfg_openql_platform_fn(),
                program_name='RB_{}'.format(i))

        2. Two qubit simultaneous randomized benchmarking:

            p = cl_oql.randomized_benchmarking(
                qubits=[0, 1],          # simultaneous RB on both qubits
                simultaneous_single_qubit_RB=True, 
                nr_cliffords=[2, 4, 8, 16, 32, 128, 512, 1024],
                nr_seeds=1,  # for CCL memory reasons
                platf_cfg=qubit.cfg_openql_platform_fn(),
                program_name='RB_{}'.format(i))

        3. Single qubit interleaved randomized benchmarking:
            p = cl_oql.randomized_benchmarking(
                qubits=[0],
                interleaving_cliffords=[None, 0, 16, 3],
                cal_points=False # relevant here because of data binning

                nr_cliffords=[2, 4, 8, 16, 32, 128, 512, 1024],
                nr_seeds=1,
                platf_cfg=qubit.cfg_openql_platform_fn(),
                program_name='Interleaved_RB_s{}_int{}_ncl{}_{}'.format(i))

    '''
    p = oqh.create_program(program_name, platf_cfg)

    # attribute get's added to program to help finding the output files
    p.filename = join(p.output_dir, p.name + '.qisa')

    if not oqh.check_recompilation_needed(
            program_fn=p.filename, platf_cfg=platf_cfg, recompile=recompile):
        return p

    if len(qubits) == 1:
        qubit_map = {'q0': qubits[0]}
        number_of_qubits = 1
        Cl = SingleQubitClifford
    elif len(qubits) == 2 and not simultaneous_single_qubit_RB:
        qubit_map = {'q0': qubits[0],
                     'q1': qubits[1]}
        number_of_qubits = 2
        Cl = TwoQubitClifford
    elif len(qubits) == 2 and simultaneous_single_qubit_RB:
        qubit_map = {'q0': qubits[0],
                     'q1': qubits[1]}
        # arguments used to generate 2 single qubit sequences
        number_of_qubits = 2
        Cl = SingleQubitClifford
    else:
        raise NotImplementedError()

    for seed in range(nr_seeds):
        for j, n_cl in enumerate(nr_cliffords):
            for interleaving_cl in interleaving_cliffords:
                if not simultaneous_single_qubit_RB:
                    cl_seq = rb.randomized_benchmarking_sequence(
                            n_cl, number_of_qubits=number_of_qubits,
                            desired_net_cl=None,#net_clifford,
                            max_clifford_idx=max_clifford_idx,
                            interleaving_cl=interleaving_cl
                            )
                    net_cl_seq = rb.calculate_net_clifford(cl_seq,Cl)
                    cl_seq_decomposed = []
                    for cl in cl_seq:
                        # hacking in exception for benchmarking only CZ
                        # (not as a member of CNOT group)
                        if cl == -4368:
                            cl_seq_decomposed.append([('CZ', ['q0', 'q1'])])
                        else:
                            cl_seq_decomposed.append(Cl(cl).gate_decomposition)
                    for net_clifford in net_cliffords:
                        recovery_to_idx_clifford = net_cl_seq.get_inverse()
                        recovery_clifford = Cl(net_clifford)*recovery_to_idx_clifford
                        cl_seq_decomposed_with_net = cl_seq_decomposed+[recovery_clifford.gate_decomposition]
                        k = oqh.create_kernel('RB_{}Cl_s{}_net{}_inter{}'.format(
                            n_cl, seed, net_clifford, interleaving_cl), p)
                        if initialize:
                            for qubit_idx in qubit_map.values():
                                k.prepz(qubit_idx)

                        for gates in cl_seq_decomposed_with_net:
                            for g, q in gates:
                                if isinstance(q, str):
                                    k.gate(g, [qubit_map[q]])
                                elif isinstance(q, list):
                                    # proper codeword
                                    k.gate(g, [qubit_map[q[0]], qubit_map[q[1]]])
                        # This hack is required to align multiplexed RO in openQL..
                        k.gate("wait",  list(qubit_map.values()), 0)
                        for qubit_idx in qubit_map.values():
                            k.measure(qubit_idx)
                        k.gate("wait",  list(qubit_map.values()), 0)
                        p.add_kernel(k)
                elif simultaneous_single_qubit_RB: 
                    for net_clifford in net_cliffords:
                        k = oqh.create_kernel('RB_{}Cl_s{}_net{}_inter{}'.format(
                            n_cl, seed, net_clifford, interleaving_cl), p)
                        if initialize:
                            for qubit_idx in qubit_map.values():
                                k.prepz(qubit_idx)

                        # Gate seqs is a hack for failing openql scheduling
                        gate_seqs = [[], []]
                        for gsi, q_idx in enumerate(qubits): 
                            cl_seq = rb.randomized_benchmarking_sequence(
                                n_cl, number_of_qubits=1,
                                desired_net_cl=net_clifford,
                                interleaving_cl=interleaving_cl)
                            for cl in cl_seq:
                                gates = Cl(cl).gate_decomposition
                                # for g, q in gates:
                                #     k.gate(g, q_idx)

                                # THIS is a hack because of OpenQL 
                                # scheduling issues #157
                                gate_seqs[gsi]+=gates
                        # OpenQL #157 HACK 
                        l = max([len(gate_seqs[0]), len(gate_seqs[1])])
                        # print('\n')
                        # print(gate_seqs[0])
                        # print(gate_seqs[1])

                        for gi in range(l): 
                            for gj, q_idx in enumerate(qubits): 
                            # gj = 0
                            # q_idx = 0
                                try: # for possible different lengths in gate_seqs
                                    g = gate_seqs[gj][gi]
                                    k.gate(g[0], [q_idx])
                                except IndexError as e: 
                                    pass 
                        # end of #157 HACK 
                        # This hack is required to align multiplexed RO in openQL..
                        k.gate("wait",  list(qubit_map.values()), 0)
                        for qubit_idx in qubit_map.values():
                            k.measure(qubit_idx)
                        k.gate("wait",  list(qubit_map.values()), 0)
                        p.add_kernel(k)


        if cal_points:
            if number_of_qubits == 1:
                p = oqh.add_single_qubit_cal_points(
                    p, qubit_idx=qubits[0],
                    f_state_cal_pts=f_state_cal_pts)
            elif number_of_qubits == 2:

                if f_state_cal_pts:
                    combinations = ['00', '01', '10', '11', '02', '20', '22']
                else:
                    combinations = ['00', '01', '10', '11']
                p = oqh.add_multi_q_cal_points(p, qubits=qubits,
                                               combinations=combinations)

    p = oqh.compile(p)
    return p
