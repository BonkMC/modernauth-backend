import sphinx_rtd_theme
# in docs/source/conf.py

# -- Project information -----------------------------------------------------
project = 'ModernAuthentication'
author  = 'ModernAuthentication Team'
release = '1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',   # if you start embedding docstrings
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = "furo"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

