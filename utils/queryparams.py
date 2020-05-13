import collections
import urllib.parse
import logging
log = logging.getLogger(__name__)

ParamInput = collections.namedtuple('ParamInput', ('param', 'value', 'error'))

class QueryParams(collections.OrderedDict):
  """A class to simplify handling query parameters and enable simpler query strings.
  This encapsulates parsing the values of query strings, holding their values, and producing
  altered query strings in a simplified format.
  It works by first declaring the accepted ("canonical") query string parameters with add().
  This object retains information on the preferred order of parameters, along with their default
  values and type.
  Then, you give parse() the parameters given by the user, and it will interpret the values
  according to their expected type.
  Then, you can continue using this object as a dict holding the parameter values, and getting and
  setting them as you wish.
  Finally, you can produce query strings by giving this object to str(). The query strings will list
  the parameters in the preferred order, omitting parameters with the default values."""

  def __init__(self):
    self.params = collections.OrderedDict()
    self.invalid_value = False
    self.invalid_values = []

  def parse(self, params_dict):
    """Convenience function to set all the parameters at once.
    Intended to be used like:
      query_params.parse(request.GET)"""
    for param_name, value in params_dict.items():
      self.set(param_name, value)

  def add(
      self, param_name, default=None, type=lambda x: x, min=None, max=None, choices=None,
      allow_empty=False,
    ):
    """Add a canonical parameter, set its default value and type.
    The type should be a callable. Incoming values will be passed through the callable before
    storing. If it throws a TypeError or ValueError, the default will be stored instead."""
    param = QueryParam(
      name=param_name, default=default, type=type, min=min, max=max, choices=choices,
      allow_empty=allow_empty
    )
    self.params[param_name] = param
    self[param_name] = default

  def set(self, param_name, value):
    """Set the value of a parameter.
    The value will be converted into the parameter's type.
    It doesn't have to be a canonical one. In that case, its order will be after all current
    canonical ones."""
    param = self.params.get(param_name, QueryParam(param_name))
    if param_name not in self.params:
      self.params[param_name] = param
    error = None
    try:
      parsed_value = param.type(value)
    except (TypeError, ValueError) as exception:
      if value == '' and param.allow_empty:
        parsed_value = None
      else:
        # If it's an invalid value, set it to be the default.
        parsed_value = param.default
        error = 'wrong type'
    if error or (param.allow_empty and parsed_value is None):
      pass  # Don't need to check validity further.
    elif param.min is not None and parsed_value < param.min:
      parsed_value = param.min
      error = 'less than min'
    if param.max is not None and parsed_value > param.max:
      parsed_value = param.max
      error = 'greater than max'
    if param.choices is not None and parsed_value not in param.choices:
      parsed_value = param.default
      error = 'invalid choice'
    if error:
      self.invalid_value = True
      self.invalid_values.append(ParamInput(param=param_name, value=value, error=error))
    self[param_name] = parsed_value

  def but_with(self, *args, **kwargs):
    """Return a copy of the current object, but with the given parameter(s) set to the given value.
    Either give keyword arguments, or positional arguments with alternating parameter names & values.
    Usage:
      params.but_with(p=1, user='me')
      params.but_with('p', 1, 'user', 'me')
    """
    new_query_params = self.copy()
    for i in range(0, len(args), 2):
      if len(args) < i+2:
        break
      param_name = args[i]
      value = args[i+1]
      new_query_params.set(param_name, value)
    for param_name, value in kwargs.items():
      new_query_params.set(param_name, value)
    return new_query_params

  def copy(self):
    copy = super().copy()
    copy.params = collections.OrderedDict()
    for param_name, param in self.params.items():
      copy.params[param_name] = param.copy()
    return copy

  def format_invalids(self):
    invalid_strs = []
    for invalid in self.invalid_values:
      invalid_strs.append(f'{invalid.param!r}: {invalid.value!r} ({invalid.error})')
    return ', '.join(invalid_strs)

  def __str__(self):
    """Return a query string with the parameters set to their current values.
    Preserves the canonical order of the parameters, and omits any whose current value is the default.
    """
    components = []
    for param_name, value in self.items():
      param = self.params.get(param_name, QueryParam(param_name))
      if value == param.default:
        continue
      param_name_quoted = urllib.parse.quote(param_name)
      value_quoted = urllib.parse.quote(str(value))
      components.append('{}={}'.format(param_name_quoted, value_quoted))
    if components:
      return '?'+'&'.join(components)
    else:
      return ''


class QueryParam(object):

  def __init__(
      self, name, default=None, type=lambda x: x, min=None, max=None, choices=None, allow_empty=False,
    ):
    self.name = name
    self.default = default
    self.type = type
    self.min = min
    self.max = max
    self.choices = choices
    self.allow_empty = allow_empty

  def copy(self):
    return QueryParam(self.name, default=self.default, type=self.type, min=self.min, max=self.max)


def boolish(value):
  if value in (False, None, 0, '', 'False', 'false', '0', 'None', 'none', 'null'):
    return False
  elif value in (True, 1, 'True', 'true', '1'):
    return True
  else:
    raise ValueError('Invalid boolish value {!r}.'.format(value))
