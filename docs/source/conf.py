import sphinx_rtd_theme

# -- Project information -----------------------------------------------------
project          = 'ModernAuth API Docs'
author           = 'ModernAuthentication Team'
release          = '1.0'

# -- General configuration ---------------------------------------------------
extensions       = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]
templates_path   = ['_templates']
exclude_patterns = []

# -- HTML output -------------------------------------------------------------
html_theme        = "furo"
html_theme_path   = [sphinx_rtd_theme.get_html_theme_path()]

# point to your logo file:
html_logo         = "_static/logo.png"

# title shown in the sidebar and page header
html_title        = "ModernAuth API Docs"
html_short_title  = "ModernAuth API Docs"

html_static_path  = ['_static']
html_css_files    = ['custom.css']

# remove the default “Built with Sphinx” footer if you like:
html_show_sphinx = False

html_theme_options = {
    "sidebar_hide_name":    False,
    "navigation_with_keys": True,

    # dark theme overrides
    "dark_css_variables": {
        "font-stack":             "Inter, sans-serif",
        "font-stack--monospace":  "Source Code Pro, Menlo, monospace",

        # true black‐ish background & crisp borders
        "color-page-background":   "#0F0F0F",
        "color-sidebar-background":"#0F0F0F",
        "color-sidebar-border":    "#1A1A1A",

        # pure white text everywhere
        "color-prose-default":     "#FFFFFF",
        "color-prose-headings":    "#FFFFFF",
        "color-brand-content":     "#FFFFFF",

        # sidebar links
        "color-sidebar-link-text":        "#FFFFFF",
        "color-sidebar-link-hover":       "#FFFFFF",
        "color-sidebar-link-active-text": "#FFFFFF",
        "color-sidebar-link-active-background":"#1A1A1A",

        # force links themselves to be white
        "color-brand-primary":     "#FFFFFF",

        # keep code‐block backgrounds dark but separated
        "color-code-background":               "#1A1A1A",
        "color-highlighted-code-line-background":"#272727",
        "color-inline-code-background":        "#1A1A1A",

        # tables & blockquotes
        "color-table-border":       "#333333",
        "color-blockquote-border":  "#333333",
        "color-blockquote-background":"#1A1A1A",

        # you can tweak admonitions if you like:
        "color-admonition-info-background":    "#111E3C",
        "color-admonition-tip-background":     "#0E3F3A",
        "color-admonition-note-background":    "#402A04",
        "color-admonition-warning-background": "#4A3B00",
        "color-admonition-danger-background":  "#3A0E0E",
    }
}
