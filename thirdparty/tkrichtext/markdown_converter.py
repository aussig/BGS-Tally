"""
Lightweight, pure Python markdown to HTML converter.
Supports basic markdown syntax without external dependencies.
"""

import re
from typing import List

class MarkdownConverter:
    """Simple markdown to HTML converter with support for common markdown syntax."""

    def __init__(self):
        """Initialize the converter."""
        self.reset()

    def reset(self):
        """Reset internal state."""
        self.in_list = False
        self.list_level = 0

    def convert(self, markdown_text: str) -> str:
        """
        Convert markdown text to HTML.

        Args:
            markdown_text: Markdown formatted string

        Returns:
            HTML formatted string
        """
        self.reset()

        if not markdown_text:
            return ""

        lines = markdown_text.split("\n")

        # Replace consecutive empty lines with a special marker
        normalized:list = []
        prev_empty:bool = False
        for line in lines:
            if prev_empty == True and not line.strip():
                normalized.append("__BR__")
                continue
            prev_empty = not line.strip()
            normalized.append(line)

        lines = normalized
        html_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Handle the <br> marker for consecutive empty lines
            if line == "__BR__":
                html_lines.append("<br>")
                i += 1
                continue

            # Empty lines
            if not line.strip():
                i += 1
                continue

            # Headings (h1-h6)
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2).strip()
                html_lines.append(f"<h{level}>{self._process_inline(content)}</h{level}>")
                i += 1
                continue

            # Horizontal rule
            if re.match(r"^[\*\-_]{3,}$", line.strip()):
                html_lines.append("<hr>")
                i += 1
                continue

            # Code blocks (indented by 4+ spaces or tab)
            if line.startswith("    ") or line.startswith("\t"):
                code_lines = []
                while i < len(lines) and (
                    lines[i].startswith("    ") or lines[i].startswith("\t") or not lines[i].strip()
                ):
                    if lines[i].strip():
                        code_lines.append(lines[i][4:] if lines[i].startswith("    ") else lines[i][1:])
                    i += 1
                if code_lines:
                    code = "\n".join(code_lines).rstrip()
                    escaped_code = self._escape_html(code)
                    html_lines.append(f"<pre><code>{escaped_code}</code></pre>")
                continue

            # Fenced code blocks (``` or ~~~)
            if re.match(r"^(`{3}|~{3})", line):
                fence = "```" if "```" in line else "~~~"
                code_lines = []
                i += 1
                while i < len(lines) and fence not in lines[i]:
                    code_lines.append(lines[i])
                    i += 1
                code = "\n".join(code_lines).rstrip()
                escaped_code = self._escape_html(code)
                html_lines.append(f"<pre><code>{escaped_code}</code></pre>")
                i += 1
                continue

            # Lists (ordered and unordered) - support nested sub-lists
            list_match = re.match(r"^(\s*)([-\*\+]|\d+\.)\s+(.*)$", line)
            if list_match:
                list_html, new_index = self._parse_list(lines, i)
                html_lines.extend(list_html)
                i = new_index
                continue

            # Block quotes
            if line.startswith("> "):
                quote_lines = []
                while i < len(lines) and (lines[i].startswith("> ") or not lines[i].strip()):
                    if lines[i].startswith("> "):
                        quote_lines.append(lines[i][2:])
                    i += 1
                quote_text = "\n".join(quote_lines).strip()
                html_lines.append(f"<blockquote><p>{self._process_inline(quote_text)}</p></blockquote>")
                continue

            # Regular paragraphs
            paragraph_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not any(
                re.match(pattern, lines[i])
                for pattern in [
                    r"^#{1,6}\s+",
                    r"^[\*\-_]{3,}$",
                    r"^[\*\-\+]\s+",
                    r"^\d+\.\s+",
                    r"^> ",
                    r"^(`{3}|~{3})",
                    r"^    ",
                ]
            ):
                paragraph_lines.append(lines[i])
                i += 1

            paragraph = " ".join(paragraph_lines).strip()
            if paragraph:
                html_lines.append(f"<p>{self._process_inline(paragraph)}</p>")

        return "\n".join(html_lines)

    def _parse_list(self, lines: List[str], start_index: int):
        """Parse a (possibly nested) list starting at start_index.

        Returns a tuple of (html_lines, new_index) where new_index is the
        index of the next line after the list block.
        """
        # Tree node structure: nodes have {'type': 'ul'|'ol', 'items': [{'text':..., 'children': [...]}, ...], 'indent': int}
        root = {'type': None, 'items': [], 'indent': -1}
        stack = [root]
        i = start_index

        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue

            m = re.match(r"^(\s*)([-\*\+]|(\d+)\.)\s+(.*)$", line)
            if not m:
                break

            indent = len(m.group(1).replace('\t', '    '))
            marker = m.group(2)
            content = m.group(4).strip()
            list_type = 'ol' if marker.endswith('.') else 'ul'

            # if we need to go up in nesting
            while len(stack) > 1 and indent < stack[-1].get('indent', 0):
                stack.pop()

            # if deeper indent than current list, create nested list under last item
            if indent > stack[-1].get('indent', -1):
                parent = stack[-1]
                new_list = {'type': list_type, 'items': [], 'indent': indent}
                if parent is root:
                    # top-level list: append directly to root
                    parent['items'].append(new_list)
                else:
                    # nested list: attach under the last item of the parent
                    if not parent['items']:
                        parent['items'].append({'text': '', 'children': []})
                    parent['items'][-1].setdefault('children', []).append(new_list)
                stack.append(new_list)
            else:
                # same indent level - ensure current stack node is list_type
                current = stack[-1]
                if current.get('type') != list_type:
                    # create sibling list under parent
                    parent = stack[-2] if len(stack) > 1 else root
                    new_list = {'type': list_type, 'items': [], 'indent': indent}
                    parent['items'].append(new_list)
                    stack[-1] = new_list

            # Add current list item to the current top list
            stack[-1]['items'].append({'text': content})
            i += 1

        # Render tree to HTML
        html_lines = []

        def render_list(node):
            list_tag = node.get('type', 'ul')
            html_lines.append(f"<{list_tag}>")
            for item in node.get('items', []):
                text = item.get('text', '')
                html_lines.append(f"<li>{self._process_inline(text)}")
                for child in item.get('children', []):
                    render_list(child)
                html_lines.append("</li>")
            html_lines.append(f"</{list_tag}>")

        # Render any top-level lists attached to root
        for item in root['items']:
            if isinstance(item, dict) and item.get('type'):
                render_list(item)

        return html_lines, i

    def _process_inline(self, text: str) -> str:
        """
        Process inline markdown syntax (bold, italic, links, code).

        Args:
            text: Text containing inline markdown

        Returns:
            HTML with processed inline elements
        """
        # Escape HTML characters first (but not in code)
        text = self._escape_html(text)

        # Code spans (backticks)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

        # Strong (bold) - **text** or __text__
        text = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)

        # Emphasis (italic) - *text* or _text_
        text = re.sub(r"\*([^\*]+)\*", r"<em>\1</em>", text)
        text = re.sub(r"_([^_]+)_", r"<em>\1</em>", text)

        # Images ![alt](url)
        text = re.sub(r"!\[([^\]]*)\]\(([^\)]+)\)", r'<img alt="\1" src="\2">', text)

        # Links [text](url)
        text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', text)

        # Colors [text]{color}
        text = re.sub(r"\[([^\]]+)\]\{([^\)]+)\}", r'<span style="color:\2">\1</span>', text)
        return text

    @staticmethod
    def _escape_html(text: str) -> str:
        """
        Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


def markdown_to_html(markdown_text: str) -> str:
    """
    Convert markdown text to HTML.

    Args:
        markdown_text: Markdown formatted string

    Returns:
        HTML formatted string
    """
    converter = MarkdownConverter()
    return converter.convert(markdown_text)
