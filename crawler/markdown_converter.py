import re
from bs4 import BeautifulSoup, NavigableString, Comment
from typing import Optional


class MarkdownConverter:
    """将HTML转换为Markdown（参考Firecrawl思路）"""

    def __init__(self):
        self._keep_tags = {
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'hr',
            'ul', 'ol', 'li',
            'blockquote', 'pre', 'code',
            'a', 'img',
            'strong', 'b', 'em', 'i', 'u',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'div', 'span'
        }

        self._block_tags = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'li'}

    def convert(self, html: str) -> str:
        """将HTML转换为Markdown"""
        if not html:
            return ""

        soup = BeautifulSoup(html, 'lxml')

        # 移除不需要的标签
        self._remove_unwanted_tags(soup)

        # 转换
        markdown = self._convert_element(soup.body if soup.body else soup)

        # 清理多余空白
        markdown = self._cleanup(markdown)

        return markdown.strip()

    def _remove_unwanted_tags(self, soup: BeautifulSoup):
        """移除不需要的标签和内容"""
        # 移除script、style、noscript等
        for tag in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg', 'path']):
            tag.decompose()

        # 移除注释
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 移除hidden元素
        for tag in soup.find_all(attrs={'hidden': True}):
            tag.decompose()

    def _convert_element(self, element) -> str:
        """递归转换元素"""
        if isinstance(element, NavigableString):
            return self._handle_text(str(element))

        if not hasattr(element, 'name') or element.name is None:
            return ""

        tag = element.name.lower()

        if tag == 'h1':
            return f"\n\n# {self._get_text_content(element)}\n\n"
        elif tag == 'h2':
            return f"\n\n## {self._get_text_content(element)}\n\n"
        elif tag == 'h3':
            return f"\n\n### {self._get_text_content(element)}\n\n"
        elif tag == 'h4':
            return f"\n\n#### {self._get_text_content(element)}\n\n"
        elif tag in ('h5', 'h6'):
            return f"\n\n##### {self._get_text_content(element)}\n\n"
        elif tag == 'p':
            return f"\n\n{self._get_text_content(element)}\n\n"
        elif tag == 'br':
            return "  \n"
        elif tag == 'hr':
            return "\n\n---\n\n"
        elif tag == 'ul':
            return self._convert_list(element, 'ul')
        elif tag == 'ol':
            return self._convert_list(element, 'ol')
        elif tag == 'li':
            return f"- {self._get_text_content(element)}\n"
        elif tag == 'blockquote':
            return f"\n> {self._get_text_content(element)}\n\n"
        elif tag == 'pre':
            return f"\n```\n{self._get_raw_text(element)}\n```\n\n"
        elif tag == 'code':
            if element.parent and element.parent.name == 'pre':
                return self._get_raw_text(element)
            return f"`{self._get_text_content(element)}`"
        elif tag == 'a':
            text = self._get_text_content(element)
            href = element.get('href', '')
            if href:
                return f"[{text}]({href})"
            return text
        elif tag == 'img':
            src = element.get('src', '')
            alt = element.get('alt', '')
            if src:
                return f"![{alt}]({src})"
            return ""
        elif tag == 'strong' or tag == 'b':
            return f"**{self._get_text_content(element)}**"
        elif tag == 'em' or tag == 'i':
            return f"*{self._get_text_content(element)}*"
        elif tag == 'table':
            return self._convert_table(element)
        elif tag in ('div', 'span'):
            return self._convert_children(element)
        else:
            return self._convert_children(element)

    def _convert_children(self, element) -> str:
        """转换子元素"""
        result = []
        for child in element.children:
            result.append(self._convert_element(child))
        return ''.join(result)

    def _convert_list(self, element, list_type: str) -> str:
        """转换列表"""
        items = []
        for li in element.find_all('li', recursive=False):
            items.append(f"- {self._get_text_content(li)}\n")
        return '\n'.join(items) + '\n\n'

    def _convert_table(self, element) -> str:
        """转换表格"""
        rows = []
        for tr in element.find_all('tr'):
            cells = []
            for cell in tr.find_all(['th', 'td']):
                cells.append(self._get_text_content(cell))
            rows.append('| ' + ' | '.join(cells) + ' |')

        if not rows:
            return ''

        # 添加分隔行
        separator = '| ' + ' | '.join(['---'] * len(rows[0].split('|'))) + ' |'
        rows.insert(1, separator)

        return '\n'.join(rows) + '\n\n'

    def _get_text_content(self, element) -> str:
        """获取文本内容，保留基本格式"""
        parts = []
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    parts.append(text)
            elif hasattr(child, 'name') and child.name:
                if child.name == 'br':
                    parts.append(' ')
                elif child.name == 'a':
                    parts.append(self._convert_element(child))
                elif child.name in ('strong', 'b', 'em', 'i', 'code'):
                    parts.append(self._convert_element(child))
                else:
                    parts.append(self._get_text_content(child))
        return ' '.join(parts).strip()

    def _get_raw_text(self, element) -> str:
        """获取元素的原始文本（保留格式）"""
        text = element.get_text()
        # 减少多余空行
        text = re.sub(r'\n\n+', '\n', text)
        return text.strip()

    def _handle_text(self, text: str) -> str:
        """处理文本转义"""
        # 转义特殊字符
        text = re.sub(r'([\\`*_~\[\]])', r'\\\1', text)
        return text

    def _cleanup(self, text: str) -> str:
        """清理多余的空行"""
        # 移除连续超过3个空行
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        # 移除行首行尾空白
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines)
