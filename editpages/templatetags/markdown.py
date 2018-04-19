from django import template
import re


register = template.Library()


@register.filter(name='markdown')
def parse_markdown(markdown, span_lines=False):
  """Parse a small subset of Markdown: italics/bold, and links.
  italics are only recognized with the * syntax, bold with **.
  links are only recognized in the form of [title](url)."""
  #TODO: Just use the Markdown package.
  #      py-gfm can get it close to Github syntax: https://pypi.python.org/pypi/py-gfm
  if span_lines:
    lines = [markdown]
  else:
    lines = markdown.splitlines()
  html_lines = []
  for line in lines:
    html = parse_links(line)
    html = parse_style(html, '**', 'strong')
    html = parse_style(html, '*', 'em')
    html_lines.append(html)
  return '\n'.join(html_lines)


def parse_links(markdown):
  return re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', markdown)


def parse_style(markdown, delim='**', tag='strong'):
  html = ''
  fields = markdown.split(delim)
  i = 0
  while i < len(fields):
    if i < len(fields)-1 and fields[i].endswith('\\'):
      html += fields[i] + delim
      i += 1
    elif i <= len(fields)-3:
      html += '{0}<{tag}>{1}</{tag}>'.format(fields[i], fields[i+1], tag=tag)
      i += 2
    elif i == len(fields)-2:
      html += fields[i] + delim
      i += 1
    else:
      html += fields[i]
      i += 1
  return html
