from pygments import token
from pygments.style import Style
from pygments.formatters import get_formatter_by_name

from . import highlight

base03  = '#002b36'
base02  = '#073642'
base01  = '#586e75'
base00  = '#657b83'
base0   = '#839496'
base1   = '#93a1a1'
base2   = '#eee8d5'
base3   = '#fdf6e3'
yellow  = '#b58900'
orange  = '#cb4b16'
red     = '#dc322f'
magenta = '#d33682'
violet  = '#6c71c4'
blue    = '#268bd2'
cyan    = '#2aa198'
green   = '#859900'

class SolarizedStyle(Style):
    background_color = base03
    highlight_color = base02
    styles = {
        token.Token:               base0,

        token.Comment:             base00 + ' italic',
        token.Comment.Preproc:     red + ' noitalic',
        token.Comment.PreprocFile: violet + ' noitalic',

        token.Keyword:             green,
        token.Keyword.Constant:    cyan,
        token.Keyword.Type:        yellow,

        token.Operator:            base0,
        token.Operator.Word:       green,

        token.Name.Attribute:      yellow,
        token.Name.Builtin:        blue,
        token.Name.Builtin.Pseudo: base00 + ' italic',
        token.Name.Class:          magenta,
        token.Name.Constant:       cyan,
        token.Name.Decorator:      orange,
        token.Name.Exception:      yellow,
        token.Name.Function:       blue,
        token.Name.Namespace:      magenta,
        token.Name.Tag:            green,
        token.Name.Variable:       base0,

        token.String:              cyan,
        token.String.Doc:          base00 + ' italic',

        token.Number:              cyan,
    }

if __name__ == "__main__":
    formatter = get_formatter_by_name('html', style=SolarizedStyle)
    print(formatter.get_style_defs('.' + highlight.CLASS))
