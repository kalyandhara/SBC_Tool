import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import os
import re

epub_path = r'C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\raw\Dolzhenko-Algorithmic-Trading-Systems-Strategies-2024.epub'
output_base = r'C:\Users\Owner\OneDrive\Documents\Trading\SBC_Tool\Financial_Astrology\Raw\Books'
book_slug = 'Dolzhenko-Algorithmic-Trading-Systems-Strategies-2024'
book_dir = os.path.join(output_base, book_slug)
os.makedirs(book_dir, exist_ok=True)

z = zipfile.ZipFile(epub_path)

# Parse container
container_xml = z.read('META-INF/container.xml')
container_root = ET.fromstring(container_xml)
ns = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container'}
rootfile = container_root.find('.//c:rootfile', ns)
opf_path = rootfile.attrib['full-path']

opf_data = z.read(opf_path)
# Parse OPF with namespaces
ns_opf = {
    'opf': 'http://www.idpf.org/2007/opf',
    'dc': 'http://purl.org/dc/elements/1.1/'
}
root = ET.fromstring(opf_data)

metadata = root.find('opf:metadata', ns_opf)
title = metadata.find('dc:title[@id="pub-title"]', ns_opf)
title_text = title.text if title is not None else 'Unknown Title'
subtitle_elem = metadata.find('dc:title[@id="pub-subtitle"]', ns_opf)
subtitle_text = subtitle_elem.text if subtitle_elem is not None else ''
creator = metadata.find('dc:creator', ns_opf)
creator_text = creator.text if creator is not None else 'Unknown'

print(f'Title: {title_text} - {subtitle_text}')
print(f'Creator: {creator_text}')

# Manifest
manifest = {}
for item in root.find('opf:manifest', ns_opf):
    item_id = item.attrib.get('id')
    href = item.attrib.get('href')
    manifest[item_id] = href

# Spine
spine = []
spine_elem = root.find('opf:spine', ns_opf)
for itemref in spine_elem:
    idref = itemref.attrib.get('idref')
    spine.append(manifest.get(idref))

# Also get navigation for titles
nav_path = manifest.get('nav')
nav_html = ''
if nav_path:
    try:
        nav_html = z.read(os.path.join('OEBPS', nav_path)).decode('utf-8')
    except:
        pass

# Parse navigation for chapter titles
soup_nav = BeautifulSoup(nav_html, 'html.parser')
nav_titles = {}
# Simple mapping using order
# fallback: use filename
chapter_files = spine

# For each chapter, read content
chapters = []
for idx, rel_path in enumerate(chapter_files):
    # Skip navigation etc
    if not rel_path or rel_path.endswith('nav.xhtml'):
        continue
    full_path = 'OEBPS/' + rel_path.replace('\\', '/')
    try:
        content = z.read(full_path).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'Failed to read {full_path}: {e}')
        continue
    soup = BeautifulSoup(content, 'html.parser')
    # Get chapter title
    title_tag = soup.find(['h1','h2','h3'])
    chapter_title = title_tag.get_text(strip=True) if title_tag else f'Chapter {idx+1}'
    # Clean text
    text = soup.get_text(separator='\n')
    # Clean excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    chapters.append({
        'index': idx+1,
        'title': chapter_title,
        'filename': rel_path,
        'text': text[:200000]  # limit
    })

# Write markdown files
index_lines = [
f'# {title_text}',
f'**Author:** {creator_text}',
]
if subtitle_text:
    index_lines.append(f'**Subtitle:** {subtitle_text}')
index_lines.append(f'**Source:** {epub_path}')
index_lines.append('')
index_lines.append('## Chapters')
for ch in chapters:
    safe_title = re.sub(r'[\\/*?:"<>|]', '_', ch['title'])
    filename = f'{ch["index"]:02d}-{safe_title[:60]}.md'
    filepath = os.path.join(book_dir, filename)
    md_content = f'# {ch["title"]}\n\n'
    md_content += f'**Source Book:** {title_text}\n'
    md_content += f'**Author:** {creator_text}\n'
    md_content += f'**Chapter File:** {ch["filename"]}\n\n'
    md_content += ch['text']
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    index_lines.append(f'- [{ch["title"]}]({filename})')

index_path = os.path.join(book_dir, 'README.md')
with open(index_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(index_lines))

print(f'Extracted {len(chapters)} chapters to {book_dir}')
print('Done')
