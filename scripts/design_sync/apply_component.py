"""
apply_component.py — Sync a Claude Design component back into the HCA mockup repo.

Workflow:
  1. Edit a component visually at claude.ai/design
  2. Download the updated HTML (it arrives wrapped in a bundler shell)
  3. Drop the file anywhere on disk
  4. Run this script:
       python scripts/design_sync/apply_component.py path/to/info-block.html
  5. Review the diff printed to stdout
  6. Re-run with --apply to write CSS-variable changes to style.css
  7. `git diff design/` shows all markup changes for manual propagation

Usage:
    python scripts/design_sync/apply_component.py <downloaded-file> [--apply] [--list-usages]

Options:
    --apply          Write detected CSS-variable changes into mockup/css/style.css
    --list-usages    List mockup/*.html files that reference the changed classes
"""

import sys
import json
import re
import argparse
from pathlib import Path
from difflib import unified_diff

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STYLE_CSS  = REPO_ROOT / 'mockup' / 'css' / 'style.css'
DESIGN_DIR = REPO_ROOT / 'design'
MOCKUP_DIR = REPO_ROOT / 'mockup'


# ---------------------------------------------------------------------------
# Unwrap Claude Design bundler shell
# ---------------------------------------------------------------------------

def unwrap_bundler(content: str) -> str:
    """Return the inner HTML if content is a Claude Design bundler wrapper."""
    m = re.search(
        r'<script[^>]+type="__bundler/template"[^>]*>\s*(".*?")\s*</script>',
        content, re.DOTALL
    )
    if m:
        return json.loads(m.group(1))
    return content


# ---------------------------------------------------------------------------
# CSS helpers
# ---------------------------------------------------------------------------

def _extract_style_block(html: str) -> str:
    m = re.search(r'<style[^>]*>(.*?)</style>', html, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ''


def _parse_css_vars(css: str) -> dict:
    m = re.search(r':root\s*\{([^}]+)\}', css, re.DOTALL)
    if not m:
        return {}
    out = {}
    # Split on ; first so compact multi-declaration lines work too
    for decl in re.split(r';', m.group(1)):
        decl = decl.strip()
        if decl.startswith('--') and ':' in decl:
            name, _, val = decl.partition(':')
            out[name.strip()] = val.strip()
    return out


def _parse_class_rules(css: str) -> dict:
    """Map selector → {prop: val} for every non-:root rule."""
    css_body = re.sub(r':root\s*\{[^}]+\}', '', css, flags=re.DOTALL)
    rules: dict = {}
    for m in re.finditer(r'([.:#\w][^{]+?)\{([^}]+)\}', css_body, re.DOTALL):
        selector = m.group(1).strip()
        props: dict = {}
        # Split by ; first so compact multi-property-per-line declarations parse correctly
        for decl in re.split(r';', m.group(2)):
            decl = decl.strip()
            if ':' in decl and not decl.startswith('/*'):
                prop, _, val = decl.partition(':')
                prop = prop.strip()
                if prop:
                    props[prop] = val.strip()
        if props:
            rules[selector] = props
    return rules


def _diff_vars(comp: dict, style: dict) -> dict:
    """Return {var: (old, new)} for vars that changed between component and style.css."""
    return {
        name: (style[name], val)
        for name, val in comp.items()
        if name in style and style[name] != val
    }


def _patch_style_css(path: Path, var_diffs: dict) -> None:
    content = path.read_text(encoding='utf-8')
    for name, (old_val, new_val) in var_diffs.items():
        pattern = re.compile(
            r'(' + re.escape(name) + r'\s*:\s*)' + re.escape(old_val) + r'(\s*;)'
        )
        content = pattern.sub(lambda m: m.group(1) + new_val + m.group(2), content)
    path.write_text(content, encoding='utf-8')


# ---------------------------------------------------------------------------
# HTML diff helpers
# ---------------------------------------------------------------------------

def _strip_style(html: str) -> str:
    """Remove <style> block so we diff only markup, not the embedded CSS."""
    return re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)


def _html_diff(original: str, updated: str, label: str) -> list[str]:
    orig_lines = _strip_style(original).splitlines(keepends=True)
    upd_lines  = _strip_style(updated).splitlines(keepends=True)
    return list(unified_diff(orig_lines, upd_lines, fromfile=f'a/{label}', tofile=f'b/{label}', n=2))


# ---------------------------------------------------------------------------
# Usage search
# ---------------------------------------------------------------------------

def _find_usages(classes: list[str]) -> list[str]:
    """Return mockup HTML files that reference any of the given CSS class names."""
    hits = set()
    for f in MOCKUP_DIR.glob('*.html'):
        text = f.read_text(encoding='utf-8', errors='ignore')
        if any(cls in text for cls in classes):
            hits.add(f.relative_to(REPO_ROOT).as_posix())
    return sorted(hits)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Sync a Claude Design component back into the HCA mockup repo.'
    )
    parser.add_argument('component', help='Path to the downloaded component HTML file')
    parser.add_argument('--apply', action='store_true',
                        help='Write CSS-variable changes into style.css (default: dry run)')
    parser.add_argument('--list-usages', action='store_true',
                        help='List mockup/*.html files that use the changed CSS classes')
    args = parser.parse_args()

    src = Path(args.component)
    if not src.exists():
        sys.exit(f'Error: {src} not found')

    raw     = src.read_text(encoding='utf-8')
    updated = unwrap_bundler(raw)
    was_bundled = (updated != raw)

    # Destination in design/
    dest = DESIGN_DIR / src.name
    original_html = dest.read_text(encoding='utf-8') if dest.exists() else None

    # ---- CSS analysis ----
    comp_css     = _extract_style_block(updated)
    style_css_text = STYLE_CSS.read_text(encoding='utf-8')

    comp_vars    = _parse_css_vars(comp_css)
    style_vars   = _parse_css_vars(style_css_text)
    var_diffs    = _diff_vars(comp_vars, style_vars)

    comp_rules   = _parse_class_rules(comp_css)
    style_rules  = _parse_class_rules(style_css_text)
    class_diffs  = [
        (sel, prop, style_rules[sel][prop], val)
        for sel, props in comp_rules.items()
        if sel in style_rules
        for prop, val in props.items()
        if prop in style_rules[sel] and style_rules[sel][prop] != val
    ]

    # ---- HTML diff ----
    html_diff_lines = (
        _html_diff(original_html, updated, src.name)
        if original_html else []
    )

    # ---- Report ----
    tag = ' [bundler unwrapped]' if was_bundled else ''
    print(f'\n=== {src.name}{tag} ===')

    if var_diffs:
        print(f'\n  CSS variable changes ({len(var_diffs)}):')
        for name, (old, new) in var_diffs.items():
            print(f'    {name}')
            print(f'      - {old}')
            print(f'      + {new}')
        if args.apply:
            _patch_style_css(STYLE_CSS, var_diffs)
            print(f'\n  ✓ Patched {len(var_diffs)} variable(s) in {STYLE_CSS.relative_to(REPO_ROOT).as_posix()}')
        else:
            print('\n  (dry run — re-run with --apply to patch style.css)')
    else:
        print('\n  CSS variables: no changes.')

    if class_diffs:
        print(f'\n  Component class changes ({len(class_diffs)}) — patch style.css manually:')
        for sel, prop, old, new in class_diffs:
            print(f'    {sel}  ->  {prop}: {old}  =>  {new}')
    else:
        print('  Component classes: no changes.')

    if html_diff_lines:
        print(f'\n  Markup changes ({len(html_diff_lines)} lines):')
        for line in html_diff_lines[:60]:
            sys.stdout.write('  ' + line)
        if len(html_diff_lines) > 60:
            print(f'\n  ... ({len(html_diff_lines) - 60} more lines, see git diff)')
    else:
        print('  Markup: no changes.' if original_html else
              '  Markup: no baseline in design/ to compare against.')

    if args.list_usages:
        # Collect component-specific class names (skip body, universal selectors, :root)
        skip = {'body', 'html', '*', 'a', 'h1', 'h2', 'h3', 'h4', 'p', 'table', 'tr', 'td', 'ul', 'li'}
        def _cls_token(sel: str) -> str:
            parts = sel.lstrip('.').split(':')[0].split()
            return parts[0] if parts else ''

        changed_classes = [
            _cls_token(sel)
            for sel in comp_rules
            if sel.startswith('.') and _cls_token(sel) and _cls_token(sel) not in skip
        ]
        usages = _find_usages(list(set(changed_classes)))
        if usages:
            print(f'\n  Mockup files that use these classes:')
            for u in usages:
                print(f'    {u}')

    # ---- Write clean HTML to design/ ----
    DESIGN_DIR.mkdir(exist_ok=True)
    dest.write_text(updated, encoding='utf-8')
    verb = 'Updated' if original_html else 'Saved'
    print(f'\n  {verb} design/{src.name}')
    if html_diff_lines:
        print('  Run: git diff design/ to review markup changes')


if __name__ == '__main__':
    main()
