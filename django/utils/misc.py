from django.db import models
from datetime import datetime


class ModelMixin(object):

  def __repr__(self):
    class_name, args = self.generic_repr_bits()
    args_strs = [key+'='+value for key, value in args if key is not None]
    return '{}({})'.format(class_name, ', '.join(args_strs))

  def generic_repr_bits(self, first_fields=(), skip_fields=()):
    args = []
    for name in first_fields:
      args.append(self.generic_repr_format(name))
    for field in self._meta.fields:
      if type(field) is models.ForeignKey:
        continue
      name = field.name
      if name not in first_fields and name not in skip_fields:
        args.append(self.generic_repr_format(name))
    class_name = type(self).__name__
    return class_name, args


  def generic_repr_format(self, name, max_len=100):
    if hasattr(self, name):
      value = getattr(self, name)
      if value is not None and value != '':
        value_str = repr(value)
        if len(value_str) > max_len:
          if isinstance(value, str):
            value_str = repr(value[:max_len-5]+'...')
          else:
            # It's hard to truncate an arbitrary repr string. Let's just make a little effort to close
            # any opening quote marks.
            value_str = repr(value_str[:max_len-5]+'...')
        return name, value_str
    return None, None
