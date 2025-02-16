import os
import sys
import numpy as np
import h5py
import string
import json
import datetime
from pycqed.measurement import hdf5_data as h5d
from pycqed.analysis import analysis_toolbox as a_tools
import errno
import pycqed as pq
import glob
from os.path import dirname, exists
from os import makedirs
import logging
import subprocess
from functools import reduce  # forward compatibility for Python 3
import operator
import string
from contextlib import ContextDecorator
from pycqed.analysis.tools.plotting import SI_prefix_and_scale_factor


try:
    import msvcrt  # used on windows to catch keyboard input
except:
    pass

digs = string.digits + string.ascii_letters


def get_git_revision_hash():
    try:
        # Refers to the global qc_config
        PycQEDdir = pq.__path__[0]
        hash = subprocess.check_output(['git', 'rev-parse',
                                        '--short=10', 'HEAD'], cwd=PycQEDdir)
    except:
        logging.warning('Failed to get Git revision hash, using 00000 instead')
        hash = '00000'

    return hash


def str_to_bool(s):
    valid = {'true': True, 't': True, '1': True,
             'false': False, 'f': False, '0': False, }
    if s.lower() not in valid:
        raise KeyError('{} not a valid boolean string'.format(s))
    b = valid[s.lower()]
    return b


def bool_to_int_str(b):
    if b:
        return '1'
    else:
        return '0'


def int_to_bin(x, w, lsb_last=True):
    """
    Converts an integer to a binary string of a specified width
    x (int) : input integer to be converted
    w (int) : desired width
    lsb_last (bool): if False, reverts the string e.g., int(1) = 001 -> 100
    """
    bin_str = '{0:{fill}{width}b}'.format((int(x) + 2**w) % 2**w,
                                          fill='0', width=w)
    if lsb_last:
        return bin_str
    else:
        return bin_str[::-1]


def int2base(x: int, base: int, fixed_length: int=None):
    """
    Convert an integer to string representation in a certain base.
    Useful for e.g., iterating over combinations of prepared states.

    Args:
        x    (int)          : the value to convert
        base (int)          : the base to covnert to
        fixed_length (int)  : if specified prepends zeros
    """
    if x < 0:
        sign = -1
    elif x == 0:
        string_repr = digs[0]
        if fixed_length is None:
            return string_repr
        else:
            return string_repr.zfill(fixed_length)

    else:
        sign = 1

    x *= sign
    digits = []

    while x:
        digits.append(digs[int(x % base)])
        x = int(x / base)

    if sign < 0:
        digits.append('-')

    digits.reverse()
    string_repr = ''.join(digits)
    if fixed_length is None:
        return string_repr
    else:
        return string_repr.zfill(fixed_length)


def mopen(filename, mode='w'):
    if not exists(dirname(filename)):
        try:
            makedirs(dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    file = open(filename, mode='w')
    return file


def dict_to_ordered_tuples(dic):
    '''Convert a dictionary to a list of tuples, sorted by key.'''
    if dic is None:
        return []
    keys = dic.keys()
    # keys.sort()
    ret = [(key, dic[key]) for key in keys]
    return ret


def to_hex_string(byteval):
    '''
    Returns a hex representation of bytes for printing purposes
    '''
    return "b'" + ''.join('\\x{:02x}'.format(x) for x in byteval) + "'"


def load_settings_onto_instrument(instrument, load_from_instr=None,
                                  folder=None, label=None,
                                  timestamp=None, **kw):
    '''
    Loads settings from an hdf5 file onto the instrument handed to the
    function.
    By default uses the last hdf5 file in the datadirectory.
    By giving a label or timestamp another file can be chosen as the
    settings file.
    '''

    older_than = None
    instrument_name = instrument.name
    success = False
    count = 0
    while success is False and count < 10:
        try:
            if folder is None:
                folder = a_tools.get_folder(timestamp=timestamp,
                                            older_than=older_than, **kw)
            else:
                folder = folder
            filepath = a_tools.measurement_filename(folder)
            f = h5py.File(filepath, 'r')
            sets_group = f['Instrument settings']
            if load_from_instr is None:
                ins_group = sets_group[instrument_name]
            else:
                ins_group = sets_group[load_from_instr]
            print('Loaded Settings Successfully')
            success = True
        except:
            older_than = os.path.split(folder)[0][-8:] \
                + '_' + os.path.split(folder)[1][:6]
            folder = None
            success = False
        count += 1

    if not success:
        print('Could not open settings for instrument "%s"' % (
            instrument_name))
        return False

    for parameter, value in ins_group.attrs.items():
        if value != 'None':  # None is saved as string in hdf5
            if type(value) == str:
                if value == 'False':
                    try:
                        instrument.set(parameter, False)
                    except:
                        print('Could not set parameter: "%s" to "%s" for instrument "%s"' % (
                            parameter, value, instrument_name))
                else:
                    try:
                        instrument.set(parameter, float(value))
                    except Exception:
                        try:
                            instrument.set(parameter, value)
                        except:
                            try:
                                instrument.set(parameter, int(value))
                            except:
                                print('Could not set parameter: "%s" to "%s" for instrument "%s"' % (
                                    parameter, value, instrument_name))
            else:
                instrument.set(parameter, value)
    f.close()
    return True


def load_settings_onto_instrument_v2(instrument, load_from_instr: str=None,
                                     label: str='', filepath: str=None,
                                     timestamp: str=None):
    '''
    Loads settings from an hdf5 file onto the instrument handed to the
    function. By default uses the last hdf5 file in the datadirectory.
    By giving a label or timestamp another file can be chosen as the
    settings file.

    Args:
        instrument (instrument) : instrument onto which settings should be
            loaded
        load_from_instr (str) : optional name of another instrument from
            which to load the settings.
        label (str)           : label used for finding the last datafile
        filepath (str)        : exact filepath of the hdf5 file to load.
            if filepath is specified, this takes precedence over the file
            locating options (label, timestamp etc.).
        timestamp (str)       : timestamp of file in the datadir


    '''

    older_than = None
    folder = None
    instrument_name = instrument.name
    success = False
    count = 0
    # Will try multiple times in case the last measurements failed and
    # created corrupt data files.
    while success is False and count < 3:
        if filepath is None:
            folder = a_tools.get_folder(timestamp=timestamp, label=label,
                                        older_than=older_than)
            filepath = a_tools.measurement_filename(folder)
        try:

            f = h5py.File(filepath, 'r')
            snapshot = {}
            h5d.read_dict_from_hdf5(snapshot, h5_group=f['Snapshot'])

            if load_from_instr is None:
                ins_group = snapshot['instruments'][instrument_name]
            else:
                ins_group = snapshot['instruments'][load_from_instr]
            success = True
        except Exception as e:
            logging.warning('Exception occured reading from {}'.format(folder))
            logging.warning(e)
            # This check makes this snippet a bit more robust
            if folder is not None:
                older_than = os.path.split(folder)[0][-8:] \
                    + '_' + os.path.split(folder)[1][:6]
            # important to set all to None, otherwise the try except loop
            # will not look for an earlier data file
            folder = None
            filepath = None
            success = False
        count += 1

    if not success:
        logging.warning('Could not open settings for instrument "%s"' % (
            instrument_name))
        return False

    for parname, par in ins_group['parameters'].items():
        try:
            if hasattr(instrument.parameters[parname], 'set'):
                instrument.set(parname, par['value'])
        except Exception as e:
            print('Could not set parameter: "{}" to "{}" '
                  'for instrument "{}"'.format(parname, par['value'],
                                               instrument_name))
            logging.warning(e)
    f.close()
    return True


def send_email(subject='PycQED needs your attention!',
               body='', email=None):
    # Import smtplib for the actual sending function
    import smtplib
    # Here are the email package modules we'll need
    from email.mime.image import MIMEImage
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    if email is None:
        email = qt.config['e-mail']

    # Create the container (outer) email message.
    msg = MIMEMultipart()
    msg['Subject'] = subject
    family = 'serwan.asaad@gmail.com'
    msg['From'] = 'Lamaserati@tudelft.nl'
    msg['To'] = email
    msg.attach(MIMEText(body, 'plain'))

    # Send the email via our own SMTP server.
    s = smtplib.SMTP_SSL('smtp.gmail.com')
    s.login('DCLabemail@gmail.com', 'DiCarloLab')
    s.sendmail(email, family, msg.as_string())
    s.quit()


def list_available_serial_ports():
    '''
    Lists serial ports

    :raises EnvironmentError:
        On unsupported or unknown platforms
    :returns:
        A list of available serial ports

    Frunction from :
    http://stackoverflow.com/questions/12090503/
        listing-available-com-ports-with-python
    '''
    import serial
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)]

    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this is to exclude your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')

    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')

    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


def add_suffix_to_dict_keys(inputDict, suffix):
    return {str(key)+suffix: (value) for key, value in inputDict.items()}


def execfile(path, global_vars=None, local_vars=None):
    """
    Args:
        path (str)  : filepath of the file to be executed
        global_vars : use globals() to use globals from namespace
        local_vars  : use locals() to use locals from namespace

    execfile function that existed in python 2 but does not exists in python3.
    """
    with open(path, 'r') as f:
        code = compile(f.read(), path, 'exec')
        exec(code, global_vars, local_vars)


def span_num(center: float, span: float, num: int, endpoint: bool=True):
    """
    Creates a linear span of points around center
    Args:
        center (float) : center of the array
        span   (float) : span the total range of values to span
        num      (int) : the number of points in the span
        endpoint (bool): whether to include the endpoint

    """
    return np.linspace(center-span/2, center+span/2, num, endpoint=endpoint)


def span_step(center: float, span: float, step: float, endpoint: bool=True):
    """
    Creates a range of points spanned around a center
    Args:
        center (float) : center of the array
        span   (float) : span the total range of values to span
        step   (float) : the stepsize between points in the array
        endpoint (bool): whether to include the endpoint in the span

    """
    # True*step/100 in the arange ensures the right boundary is included
    return np.arange(center-span/2, center+span/2+endpoint*step/100, step)


def gen_sweep_pts(start: float=None, stop: float=None,
                  center: float=0, span: float=None,
                  num: int=None, step: float=None, endpoint=True):
    """
    Generates an array of sweep points based on different types of input
    arguments.
    Boundaries of the array can be specified using either start/stop or
    using center/span. The points can be specified using either num or step.

    Args:
        start  (float) : start of the array
        stop   (float) : end of the array
        center (float) : center of the array
                         N.B. 0 is chosen as a sensible default for the span.
                         it is argued that no such sensible default exists
                         for the other types of input.
        span   (float) : span the total range of values to span

        num      (int) : number of points in the array
        step   (float) : the stepsize between points in the array
        endpoint (bool): whether to include the endpoint

    """
    if (start is not None) and (stop is not None):
        if num is not None:
            return np.linspace(start, stop, num, endpoint=endpoint)
        elif step is not None:
            # numpy arange does not natively support endpoint
            return np.arange(start, stop + endpoint*step/100, step)
        else:
            raise ValueError('Either "num" or "step" must be specified')
    elif (center is not None) and (span is not None):
        if num is not None:
            return span_num(center, span, num, endpoint=endpoint)
        elif step is not None:
            return span_step(center, span, step, endpoint=endpoint)
        else:
            raise ValueError('Either "num" or "step" must be specified')
    else:
        raise ValueError('Either ("start" and "stop") or '
                         '("center" and "span") must be specified')


def getFromDict(dataDict: dict, mapList: list):
    """
    get a value from a nested dictionary by specifying a list of keys

    Args:
        dataDict: nested dictionary to get the value from
        mapList : list of strings specifying the key of the item to get
    Returns:
        value from dictionary

    example:
        example_dict = {'a': {'nest_a': 5, 'nest_b': 8}
                        'b': 4}
        getFromDict(example_dict, ['a', 'nest_a']) -> 5
    """
    return reduce(operator.getitem, mapList, dataDict)


def setInDict(dataDict: dict, mapList: list, value):
    """
    set a value in a nested dictionary by specifying the location using a list
    of key.

    Args:
        dataDict: nested dictionary to set the value in
        mapList : list of strings specifying the key of the item to set
        value   : the value to set

    example:
        example_dict = {'a': {'nest_a': 5, 'nest_b': 8}
                        'b': 4}
        example_dict_after = getFromDict(example_dict, ['a', 'nest_a'], 6)
        example_dict = {'a': {'nest_a': 6, 'nest_b': 8}
                        'b': 4}
    """
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


def is_more_rencent(filename: str, comparison_filename: str):
    """
    Returns True if the contents of "filename" has changed more recently
    than the contents of "comparison_filename".
    """
    return os.path.getmtime(filename) > os.path.getmtime(comparison_filename)


class NumpyJsonEncoder(json.JSONEncoder):
    '''
    JSON encoder subclass that converts Numpy types to native python types
    for saving in JSON files.
    Also converts datetime objects to strings.
    '''

    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, datetime.datetime):
            return str(o)
        else:
            return super().default(o)


class suppress_stdout(ContextDecorator):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).

    Source: "https://stackoverflow.com/questions/11130156/
        suppress-stdout-stderr-print-from-python-functions"

    '''

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close all file descriptors
        for fd in self.null_fds + self.save_fds:
            os.close(fd)


class KeyboardFinish(KeyboardInterrupt):
    """
    Indicates that the user safely aborts/finishes the experiment.
    Used to finish the experiment without raising an exception.
    """
    pass


def check_keyboard_interrupt():
    try:  # Try except statement is to make it work on non windows pc
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if b'q' in key:
                # this causes a KeyBoardInterrupt
                raise KeyboardInterrupt('Human "q" terminated experiment.')
            elif b'f' in key:
                # this should not raise an exception
                raise KeyboardFinish(
                    'Human "f" terminated experiment safely.')
    except Exception:
        pass


class SafeFormatter(string.Formatter):
    """
    A formatter that replaces "missing" values and "bad_fmt" to prevent
    unexpected Exceptions being raised.

    Based on https://stackoverflow.com/questions/20248355/how-to-get-python-to-gracefully-format-none-and-non-existing-fields
    """

    def __init__(self, missing='~~', bad_fmt='!!'):
        self.missing, self.bad_fmt = missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val = super(SafeFormatter, self).get_field(
                field_name, args, kwargs)
            # Python 3, 'super().get_field(field_name, args, kwargs)' works
        except (KeyError, AttributeError):
            val = None, field_name
        return val

    def format_field(self, value, spec):
        # handle an invalid format
        if value is None:
            return self.missing
        try:
            return super(SafeFormatter, self).format_field(value, spec)
        except ValueError:
            if self.bad_fmt is not None:
                return self.bad_fmt
            else:
                raise


def format_value_string(par_name: str, lmfit_par, end_char='', unit=None):
    """
    Format an lmfit par to a  string of value with uncertainty.

    par_name (str):
        the name of the parameter to use in the string
    lmfit_par :
        an lmfit Parameter object. The value and stderr of this parameter
        will be used.
    end_char (str):
        A character that will be put at the end of the line.
    unit (str):
        a unit. If this is an SI unit it will be used in automatically
        determining a prefix for the unit and rescaling accordingly.
    """
    val_string = par_name
    val_string += ': {:.4f}$\pm${:.4f} {}{}'

    scale_factor, unit = SI_prefix_and_scale_factor(
            lmfit_par.value, unit)
    val = lmfit_par.value*scale_factor
    if lmfit_par.stderr is not None:
        stderr = lmfit_par.stderr*scale_factor
    else:
        stderr = None
    fmt = SafeFormatter(missing='NaN')
    val_string = fmt.format(val_string, val, stderr,
                            unit, end_char)
    return val_string
