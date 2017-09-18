import copy
import numpy as np


def nelder_mead(fun, x0,
                initial_step=0.1,
                no_improve_thr=10e-6, no_improv_break=10,
                maxiter=0,
                alpha=1., gamma=2., rho=-0.5, sigma=0.5,
                verbose=False):
    '''
    parameters:
        fun (function): function to optimize, must return a scalar score
            and operate over a numpy array of the same dimensions as x0
        x0 (numpy array): initial position
        initial_step (float/np array): determines the stepsize to construct
            the initial simplex. If a float is specified it uses the same
            value for all parameters, if an array is specified it uses
            the specified step for each parameter.

        no_improv_thr,  no_improv_break (float, int): break after
            no_improv_break iterations with an improvement lower than
            no_improv_thr
        maxiter (int): always break after this number of iterations.
            Set it to 0 to loop indefinitely.
        alpha (float): reflection coefficient
        gamma (float): expansion coefficient
        rho (float): contraction coefficient
        sigma (float): shrink coefficient
            For details on these parameters see Wikipedia page

    return: tuple (best parameter array, best score)


    Pure Python/Numpy implementation of the Nelder-Mead algorithm.
    Implementation from https://github.com/fchollet/nelder-mead, edited by
    Adriaan Rol for use in PycQED.
    Reference: https://en.wikipedia.org/wiki/Nelder%E2%80%93Mead_method
    '''
    # init
    x0 = np.array(x0)  # ensures algorithm also accepts lists
    dim = len(x0)
    prev_best = fun(x0)
    no_improv = 0
    res = [[x0, prev_best]]
    if type(initial_step) is float:
        initial_step_matrix = np.eye(dim)*initial_step
    elif (type(initial_step) is list) or (type(initial_step) is np.ndarray):
        if len(initial_step) != dim:
            raise ValueError('initial_step array must be same lenght as x0')
        initial_step_matrix = np.diag(initial_step)
    else:
        raise TypeError('initial_step ({})must be list or np.array'.format(
                        type(initial_step)))

    for i in range(dim):
        x = copy.copy(x0)
        x = x + initial_step_matrix[i]
        score = fun(x)
        res.append([x, score])

    # simplex iter
    iters = 0
    while 1:
        # order
        res.sort(key=lambda x: x[1])
        best = res[0][1]

        # break after maxiter
        if maxiter and iters >= maxiter:
            # Conclude failure break the loop
            if verbose:
                print('max iterations exceeded, optimization failed')
            break
        iters += 1

        if best < prev_best - no_improve_thr:
            no_improv = 0
            prev_best = best
        else:
            no_improv += 1

        if no_improv >= no_improv_break:
            # Conclude success, break the loop
            if verbose:
                print('No improvement registered for {} rounds,'.format(
                      no_improv_break) + 'concluding succesful convergence')
            break

        # centroid
        x0 = [0.] * dim
        for tup in res[:-1]:
            for i, c in enumerate(tup[0]):
                x0[i] += c / (len(res)-1)

        # reflection
        xr = x0 + alpha*(x0 - res[-1][0])
        rscore = fun(xr)
        if res[0][1] <= rscore < res[-2][1]:
            del res[-1]
            res.append([xr, rscore])
            continue

        # expansion
        if rscore < res[0][1]:
            xe = x0 + gamma*(x0 - res[-1][0])
            escore = fun(xe)
            if escore < rscore:
                del res[-1]
                res.append([xe, escore])
                continue
            else:
                del res[-1]
                res.append([xr, rscore])
                continue

        # contraction
        xc = x0 + rho*(x0 - res[-1][0])
        cscore = fun(xc)
        if cscore < res[-1][1]:
            del res[-1]
            res.append([xc, cscore])
            continue

        # reduction
        x1 = res[0][0]
        nres = []
        for tup in res:
            redx = x1 + sigma*(tup[0] - x1)
            score = fun(redx)
            nres.append([redx, score])
        res = nres

    # once the loop is broken evaluate the final value one more time as
    # verification
    fun(res[0][0])
    return res[0]


def SPSA(fun,
         x0,
         ctrl_min,
         ctrl_max,
         initial_step,
         no_improve_thr=10e-6,
         no_improv_break=10,
         maxiter=0,
         a=0.1,
         gamma=0.101, alpha=0.602, c=0.01, A=50,
         p=0.5,
         verbose=False):
    '''
    parameters:
        fun (function): function to optimize, must return a scalar score
            and operate over a numpy array of the same dimensions as x0
        x0 (numpy array): initial position


        no_improv_thr,  no_improv_break (float, int): break after
            no_improv_break iterations with an improvement lower than
            no_improv_thr
        maxiter (int): always break after this number of iterations.
            Set it to 0 to loop indefinitely.
        alpha, gamma, a, c, A, (float): parameters for the SPSA gains
            (see refs for definitions)
        p (float): probability to get 1 in Bernoulli +/- 1 distribution
            (see refs for context)
        ctrl_min, ctrl_max (float/array): boundaries for the parameters.
            can be either a global boundary for all dimensions, or a
            numpy array containing the boundary for each dimension.
    return: tuple (best parameter array, best score)

    alpha, gamma, a, c, A and p, are parameters for the algorithm.
    Their function is described in the references below,
    and even optimal values have been discussed in the literature.


    Pure Python/Numpy implementation of the SPSA algorithm designed by Spall.
    Implementation from http://www.jhuapl.edu/SPSA/PDF-SPSA/Spall_An_Overview.PDF,
    edited by Ramiro Sagastizabal for use in PycQED.
    Reference: http://www.jhuapl.edu/SPSA/Pages/References-Intro.htm
    '''
    # init
      # ensures algorithm also accepts lists
    try:
        dim = len(x0)
        # print(dim)
        x0 = np.array(x0)
    except Exception:
        dim = 1
    
    prev_best = fun(x0)
    no_improv = 0
    res = [[x0, prev_best]]
    # print(res)
    x = copy.copy(x0)
    

    # SPSA iter init
    iters = 0

# here the calibration of a
    
    prev_best = fun(x0)
    no_improv = 0
    res = [[x0, prev_best]]
    # print(res)
    x = copy.copy(x0)
    # print('the lines above have finished executing')
       #tuneup a according to the chosen value of c
   #add them to the ad_func_pars
    num_directions = dim*2
    num_gradient_measurements = 1
    fluctuation_components = np.zeros(num_directions)
    for i in range(num_directions):
        
        # sample from a bernoulli(rescaled binomial) distribution
        delta_binomial = np.random.binomial(1, 0.5, dim)
        delta_binomial[delta_binomial == 0] = -1
        delta = delta_binomial 
        if dim == 1:
            delta = float(delta)
        # gradient measurement
    
    
        #print('this loop is executing')
        x_plus = x0+c*delta
        x_minus = x0-c*delta

        y_plus = fun(x_plus)
        y_minus = fun(x_minus)
        #fluctuation[j] = y_plus - y_minus
        # print(fluctuation[j])
        # HERE THERE IS A PROBLEM, THIS GETS NAN!
        #fluctuation_single_direction = np.std(np.absolute(fluctuation))
        # fluctuation_components[i] =  fluctuation_single_direction
        fluctuation_components[i] =  y_plus - y_minus
    # a is the gradient averaged along many directions
    #sampled from a bernoulli distribution
    print(fluctuation_components)
    print(np.mean(np.absolute(fluctuation_components)))
    a = (initial_step*2*c)/(np.mean(np.absolute(fluctuation_components)))
    print('long awaited tuneup {}'.format(a))
    #print("The tuned up value a is {}".format(a))



    while 1:
        # order


        # print ('a has been callibrated to {}'.format(a))
        res.sort(key=lambda x: x[1])
        best = res[0][1]

        # break after maxiter
        if maxiter and iters >= maxiter:
            # Conclude failure break the loop
            if verbose:
                print('max iterations exceeded, optimization failed')
            break
        iters += 1

        if best < prev_best - no_improve_thr:
            no_improv = 0
            prev_best = best
        else:
            no_improv += 1

        if no_improv >= no_improv_break:
            # Conclude success, break the loop
            if verbose:
                print('No improvement registered for {} rounds,'.format(
                      no_improv_break) + 'concluding succesful convergence')
            break

        #step 1: setup gain sequence for c_k
        
        a_k = a/(iters + 1 +A)**alpha
        c_k = c/(iters + 1)**gamma
        # sample from a bernoulli(rescaled binomial) distribution
        delta_binomial = np.random.binomial(1, 0.5, dim)
        delta_binomial[delta_binomial == 0] = -1
        delta = delta_binomial 
        if dim == 1:
            delta = float(delta)
        # gradient measurement
        x_plus = np.minimum(x+c_k*delta, ctrl_max)
        x_minus = np.maximum(x-c_k*delta, ctrl_min)
        
        y_plus = fun(x_plus)
        y_minus = fun(x_minus)
        
        res.append([x_plus, y_plus])
        res.append([x_minus, y_minus])
        
        #gradient update
        gradient = ((y_plus-y_minus)/(2.*c_k))*np.reciprocal(delta)
        
        
        # update x
        x = x-a_k*gradient
        
        #compare x_plus and x_minus with ctrl_max and ctrl_min 
        #if algorithm goes out of bounds
        #set by ctrl_min and ctrl_max put
        #x back to ctrl_min or ctrl_max 
        if dim == 1:
            x = float(x)
        score = fun(x)
        res.append([x, score])

    # once the loop is broken evaluate the final value one more time as
    # verification
    fun(res[0][0])
    return res[0]
