# Requirements (example):
# python -m pip install markdown pandas tabulate linkify-it-py selenium beautifulsoup4 pymdown-extensions
#
# Usage examples:
#   python convert.py --out 1
#   python convert.py --out 2
#   python convert.py --out 3
#   python convert.py --out 1,3
#   python convert.py --out 123
#   python convert.py --out 1 2 3
#
# Notes:
# - 1=HTML, 2=Markdown, 3=PDF
# - If HTML/PDF are requested, Markdown intermediate will be generated as needed.

import argparse
import base64
import glob
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.parse

import markdown
import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

print(sys.getdefaultencoding())

link_pattern_regx = r'\[([^\]]+)\]\(([^()]+(?:\([^()]*\)[^()]*)*)\)'

def copyGlobalBackgroundToOutput(output_root: str, global_dir: str = "./watermark"):
    src_svg = os.path.join(global_dir, "watermark.svg")
    if not os.path.exists(src_svg):
        raise SystemExit(
            "ERROR: watermark.svg not found.\n"
            f"Expected: {os.path.abspath(src_svg)}"
        )

    dest_dir = os.path.join(output_root, "resources")
    os.makedirs(dest_dir, exist_ok=True)

    dest_svg = os.path.join(dest_dir, "logo_bg.svg")
    shutil.copy(src_svg, dest_svg)
    print(f"Copied background: {src_svg} -> {dest_svg}")

def collectDirectoryAndFileNames(directory: str):
    directory_paths = []
    filename_paths = []
    for root, dirs, files in os.walk(directory):
        relative_path = os.path.relpath(root, directory).replace("\\", "/")
        directory_paths.append(relative_path)

        for file in files:
            file_path = os.path.join(root, file)
            relative_file_path = os.path.relpath(file_path, directory).replace("\\", "/")
            filename_paths.append(relative_file_path)

    if "." in directory_paths:
        directory_paths.remove(".")
    return directory_paths, filename_paths


def removeUnnecessaryWordInDierectoryName(directory_name: str):
    # Keep as-is (your original code returns directory_name immediately)
    return directory_name


def removeUnnecessaryWordInFileName(filename: str):
    remained_path, extension = os.path.splitext(filename)
    words = remained_path.split(' ')
    if extension.lower() in ['.md']:
        if len(words) > 1:
            words.pop()

    newPath = ' '.join(words)
    return f"{newPath}{extension}"


def changeSpaceToUnderbarInString(name: str):
    return name.replace(" ", "_")


def linkDirectoryName(directory_path):
    names = directory_path.split('/')

    converted_names = [removeUnnecessaryWordInDierectoryName(name) for name in names]
    converted_names = [changeSpaceToUnderbarInString(name) for name in converted_names]

    ret = '/'.join(converted_names)
    ret = unicodedata.normalize('NFC', ret)
    return ret


def createDirectoryNameMap(directory_paths):
    return {key: linkDirectoryName(key) for key in directory_paths}


def linkFileName(file_path):
    file_path = urllib.parse.unquote(file_path, 'utf-8')
    file_path = unicodedata.normalize('NFC', file_path)

    names = file_path.split('/')
    filename = names[-1]
    directory_names = names[:-1]

    converted_directory_names = [removeUnnecessaryWordInDierectoryName(name) for name in directory_names]
    converted_directory_names = [changeSpaceToUnderbarInString(name) for name in converted_directory_names]
    converted_filename = removeUnnecessaryWordInFileName(filename)
    converted_filename = changeSpaceToUnderbarInString(converted_filename)

    if len(converted_directory_names) != 0:
        converted_directory_name = '/'.join(converted_directory_names)
        return f"{converted_directory_name}/{converted_filename}"
    return converted_filename


def createFileNameMap(file_paths):
    return {key: linkFileName(key) for key in file_paths}


def convertURLToUTF8(url):
    new_url = urllib.parse.unquote(url, 'utf-8')
    new_url = unicodedata.normalize('NFC', new_url)
    return new_url


def _ensure_windows_long_path(path: str) -> str:
    # Only adjust on Windows; harmless elsewhere but keep logic simple
    if os.name != "nt":
        return path

    if os.path.exists(path):
        return path

    abs_path = os.path.abspath(path)
    if abs_path.startswith('\\\\'):
        return '\\\\?\\UNC\\' + abs_path[2:]
    return '\\\\?\\' + abs_path


def createIntermediateDirectory(input_path: str, output_path: str, directorypath_map, filepath_map):
    os.makedirs(output_path, exist_ok=True)

    for root, dirs, files in os.walk(input_path):
        relative_path = os.path.relpath(root, input_path).replace("\\", "/")
        if relative_path and relative_path[0] != '.':
            new_directory_path = directorypath_map.get(relative_path, relative_path)
            os.makedirs(os.path.join(output_path, new_directory_path), exist_ok=True)

        for file in files:
            file_path = os.path.join(root, file)
            relative_file_path = os.path.relpath(file_path, input_path).replace("\\", "/")
            new_file_path = filepath_map.get(relative_file_path, relative_file_path)
            new_full_file_path = os.path.join(output_path, new_file_path)

            print(f"copy File : {file_path} -> {new_full_file_path}")

            src = _ensure_windows_long_path(file_path)
            os.makedirs(os.path.dirname(new_full_file_path), exist_ok=True)
            shutil.copy(src, new_full_file_path)


def createResourceDirectory(input_path: str, output_path: str):
    os.makedirs(output_path, exist_ok=True)
    for root, dirs, files in os.walk(input_path):
        relative_path = os.path.relpath(root, input_path).replace("\\", "/")
        output_directory_path = os.path.join(output_path, relative_path)
        if relative_path and relative_path[0] != '.':
            os.makedirs(output_directory_path, exist_ok=True)

        for file in files:
            _, extension = os.path.splitext(file)
            if extension.lower() in ['.jpg', '.png', '.bmp', '.svg', '.zip', '.mp4']:
                src_path = os.path.join(root, file)
                dest_path = os.path.join(output_directory_path, file)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy(src_path, dest_path)


def removeCSVFiles(directory: str):
    for root, dirs, files in os.walk(directory):
        for file in files:
            _, extension = os.path.splitext(file)
            if extension.lower() in ['.csv']:
                os.remove(os.path.join(root, file))


def readMarkdownFile(root_path: str, relative_path: str):
    with open(f"{root_path}/{relative_path}", 'r', encoding='utf-8') as file:
        return file.read()


def readHTMLFile(root_path: str, relative_path: str):
    with open(f"{root_path}/{relative_path}", 'r', encoding='utf-8') as file:
        return file.read()


def replace_link_urls(markdown_text):
    link_pattern = re.compile(link_pattern_regx)

    def replace_url(match):
        link_text, old_url = match.groups()
        print(f"link_text : {link_text} old_url : {old_url}")

        if old_url.startswith("https://"):
            return f"[{link_text}]({old_url})"

        linkUTF8 = convertURLToUTF8(link_text)
        new_url = linkFileName(old_url)
        print(f"new_link : {linkUTF8} new_url : {new_url}")
        return f"[{linkUTF8}]({new_url})"

    return link_pattern.sub(replace_url, markdown_text)


def csvToTable(path: str):
    path = _ensure_windows_long_path(path)
    print(f"csv path : {path}")
    df = pandas.read_csv(path)
    return df.to_markdown(index=False)


def replace_csv(markdown_text, root_path, relative_path):
    full_path = f"{root_path}/{relative_path}"
    directoryname = os.path.dirname(full_path)

    link_pattern = re.compile(link_pattern_regx)

    def replace_url(match):
        link_text, old_url = match.groups()
        print(f"link_text : {link_text} old_url : {old_url}")

        if old_url.endswith(".csv"):
            table = csvToTable(f"{directoryname}/{old_url}")
            return f"{table}\n"
        return f"[{link_text}]({old_url})"

    return link_pattern.sub(replace_url, markdown_text)


def replaceNewLineInMarkdownTable(text):
    cell_pattern = re.compile(r'\|([^\n|]+(\n[^\n|]+)*)')
    matches = cell_pattern.findall(text)

    for match in matches:
        sentence = match[0]
        replaced_sentence = sentence.replace('\n', '<br>')
        text = text.replace(f'|{sentence}|', f'|{replaced_sentence}|')

    return text


def generateAnchor(header_text):
    text = re.sub(r'[^\w\s]', '', header_text).strip().lower().replace(" ", "-")
    return text


def removeMarkdownSyntax(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    return text


def generateHeaderList(markdown_text):
    headers = re.findall(r'^(#+)\s+(.*)$', markdown_text, flags=re.MULTILINE)
    header_metadata_list = []
    header_count = {}

    for header in headers:
        header_level = len(header[0])
        header_text = removeMarkdownSyntax(header[1])
        header_anchor = generateAnchor(header_text)

        if header_text in header_count:
            current_header_count = header_count[header_text]
            header_anchor += f"-{current_header_count}"
            header_count[header_text] += 1
        else:
            header_count[header_text] = 1

        header_metadata_list.append({"level": header_level, "text": header_text, "anchor": f"{header_anchor}"})

    return header_metadata_list


def generateHeaderMap(markdown_text):
    headers = re.findall(r'^(#+)\s+(.*)$', markdown_text, flags=re.MULTILINE)
    header_metadata_map = {}

    for header in headers:
        header_text = removeMarkdownSyntax(header[1])
        header_anchor = generateAnchor(header_text)
        header_metadata_map[header_text] = header_anchor

    return header_metadata_map


def generateTableOfContent(header_metadata):
    ret = "\n\n"
    for header in header_metadata:
        text = header["text"]
        anchor = header["anchor"]
        ret += "\t" * (header["level"] - 1)
        ret += f"- [{text}](#{anchor})\n"
    ret += "\n"
    return ret


def insertTableOfContent(markdown_text, toc):
    match = re.search(r'^(#+)\s+(.*)$', markdown_text, flags=re.MULTILINE)
    idx = -1
    if match:
        idx = match.end()
    return markdown_text[:idx] + toc + markdown_text[idx:]


def collectAllMarkdownFileRelativePaths(root_path: str):
    paths = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(file_path, root_path).replace("\\", "/")
                paths.append(relative_file_path)
    return paths


def collectAllHTMLFileRelativePaths(root_path: str):
    paths = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(file_path, root_path).replace("\\", "/")
                paths.append(relative_file_path)
    return paths


def replaceLinkFromMarkdownToHTML(markdown_text):
    link_pattern = re.compile(link_pattern_regx)

    def replace_url(match):
        link_text, old_url = match.groups()
        print(f"link_text : {link_text} old_url : {old_url}")
        new_url = old_url.replace(".md", ".html")
        return f"[{link_text}]({new_url})"

    return link_pattern.sub(replace_url, markdown_text)


def replaceLinkFromHTMLToPDF(html_text):
    link_pattern = re.compile(r'<a\s+href="([^"]+\.html)">')

    def replace_url(match):
        old_url = match.group(0)
        new_url = old_url.replace(".html", ".pdf")
        return f"{new_url}"

    return link_pattern.sub(replace_url, html_text)


def createMarkdownFile(content: str, root_path: str, relative_path: str):
    full_path = f"{root_path}/{relative_path}"
    directoryname = os.path.dirname(full_path)
    os.makedirs(directoryname, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as result_file:
        result_file.write(content)


def createHTMLContent(markdown_text: str):
    md = markdown.Markdown(extensions=['codehilite', 'extra', 'pymdownx.tilde'])
    return md.convert(markdown_text)


def replaceMP4LinksInHTML(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.lower().endswith('.mp4'):
            video_tag = soup.new_tag('video', controls=True, width="640")
            source_tag = soup.new_tag('source', src=href, type="video/mp4")
            video_tag.append(source_tag)
            video_tag.append(soup.new_string("Your browser doesn’t support the video tag."))

            a_tag_parent = a_tag.parent
            if a_tag_parent and a_tag_parent.name == 'p':
                a_tag_parent.replace_with(video_tag)
            else:
                a_tag.replace_with(video_tag)

    return str(soup)


def addAnchorToHTMLHeader(html_content, header_map):
    soup = BeautifulSoup(html_content, 'html.parser')
    headers = soup.find_all(re.compile('^h\d'))

    header_count = {}

    for header in headers:
        header_text = header.text
        if header_text not in header_map:
            print(f"[WARN] header not found in map: {header_text}")
            continue

        anchor = header_map[header_text]
        if header_text in header_count:
            current_header_count = header_count[header_text]
            anchor += f"-{current_header_count}"
            header_count[header_text] += 1
        else:
            header_count[header_text] = 1

        header["id"] = anchor
        print(f"header : {header} header_txt : {header_text} anchor : {anchor}")

    return str(soup)


def applyCSS(html_content: str) -> str:
    main_file_path = os.path.dirname(os.path.abspath(__file__))
    with open(f"{main_file_path}/apply_markdown.html", "r", encoding="utf-8") as f:
        template = f.read()

    if "__HTML_CONTENT__" not in template:
        raise SystemExit("ERROR: apply_markdown.html must contain '__HTML_CONTENT__'.")
    if "__BG_PATH__" not in template:
        raise SystemExit("ERROR: apply_markdown.html must contain '__BG_PATH__'.")

    return template.replace("__HTML_CONTENT__", html_content)

def createHTMLFile(content, root_path, relative_path):
    full_path = f"{root_path}/{relative_path}"
    directoryname = os.path.dirname(full_path)
    os.makedirs(directoryname, exist_ok=True)

    html_path = full_path.replace(".md", ".html")

    # Calculate depth to reach root_path/watermark/watermark.svg
    rel_dir = os.path.dirname(relative_path)  # e.g. "sub/dir"
    depth = 0 if rel_dir == "" else len(rel_dir.split("/"))
    prefix = "../" * depth
    bg_relative_path = f"{prefix}resources/logo_bg.svg"

    # Replace token
    if "__BG_PATH__" not in content:
        raise SystemExit(
            f"ERROR: __BG_PATH__ token not found in HTML template content.\n"
            f"File: {relative_path}\n"
            "Check apply_markdown.html contains '__BG_PATH__'."
        )

    content = content.replace("__BG_PATH__", bg_relative_path)

    # Validate replacement worked
    if "__BG_PATH__" in content:
        raise SystemExit(
            f"ERROR: __BG_PATH__ token still present after replacement.\n"
            f"File: {relative_path}\n"
            f"Attempted path: {bg_relative_path}"
        )

    with open(html_path, "w", encoding="utf-8") as result_file:
        result_file.write(content)


def createPDFFile(content: str, root_path: str, relative_path: str):
    full_path = f"{root_path}/{relative_path}"
    print(f"fullpath : {full_path}")
    directoryname = os.path.dirname(full_path)
    os.makedirs(directoryname, exist_ok=True)

    pdf_path = full_path.replace(".html", ".pdf")

    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.execute_script("document.write(arguments[0]);", content)
        time.sleep(1)

        options = {
            "printBackground": True,
            "paperWidth": 8.3,
            "paperHeight": 11.7,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0
        }
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", options)["data"]
        with open(pdf_path, "wb") as f:
            f.write(base64.b64decode(pdf_data))
    finally:
        driver.quit()


def removeDirectory(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)


def parse_out_selection(values) -> set:
    """
    Valid values:
      1 = HTML
      2 = Markdown
      3 = PDF

    Acceptable formats:
      --out 1
      --out 1,3
      --out 13
      --out 1 2 3
    """

    allowed = {"1", "2", "3"}
    selected = set()
    invalid = set()

    for v in values:
        v = v.strip()
        if not v:
            continue

        parts = v.split(',')

        for p in parts:
            p = p.strip()
            if not p:
                continue

            # Case: "13"
            if len(p) > 1 and p.isdigit():
                for ch in p:
                    if ch in allowed:
                        selected.add(int(ch))
                    else:
                        invalid.add(ch)
            else:
                if p in allowed:
                    selected.add(int(p))
                else:
                    invalid.add(p)

    if invalid:
        print("\nERROR: Invalid --out value(s):", ", ".join(sorted(invalid)))
        print("\nAllowed values:")
        print("  1 = HTML")
        print("  2 = Markdown")
        print("  3 = PDF")
        print("\nExamples:")
        print("  --out 1")
        print("  --out 2")
        print("  --out 3")
        print("  --out 1,3")
        print("  --out 123")
        print("  --out 1 2 3\n")
        raise SystemExit(1)

    if not selected:
        raise SystemExit("ERROR: No valid --out value provided.")

    return selected


def build_markdown(input_dir: str, md_dir: str):
    directory_paths, filename_paths = collectDirectoryAndFileNames(input_dir)
    directorypath_map = createDirectoryNameMap(directory_paths)
    filepath_map = createFileNameMap(filename_paths)

    removeDirectory(md_dir)
    createIntermediateDirectory(input_dir, md_dir, directorypath_map, filepath_map)

    md_paths = collectAllMarkdownFileRelativePaths(md_dir)
    for path in md_paths:
        content = readMarkdownFile(md_dir, path)

        content = replace_link_urls(content)
        content = replace_csv(content, md_dir, path)
        content = replaceNewLineInMarkdownTable(content)

        header_list = generateHeaderList(content)
        toc = generateTableOfContent(header_list)
        content = insertTableOfContent(content, toc)

        createMarkdownFile(content, md_dir, path)

    removeCSVFiles(md_dir)


def build_html(md_dir: str, html_dir: str):
    removeDirectory(html_dir)

    # resources (images, zip, mp4...) from markdown dir to html dir
    createResourceDirectory(md_dir, html_dir)

    # ✅ Add: copy global watermark (./watermark/watermark.svg) into html/watermark/
    copyGlobalBackgroundToOutput(html_dir, "./watermark")

    md_paths = collectAllMarkdownFileRelativePaths(md_dir)
    for path in md_paths:
        content = readMarkdownFile(md_dir, path)

        content = replaceLinkFromMarkdownToHTML(content)
        print(content)

        metadata = generateHeaderMap(content)

        content = createHTMLContent(content)
        print(content)

        content = replaceMP4LinksInHTML(content)
        print(content)

        content = addAnchorToHTMLHeader(content, metadata)
        print(content)

        content = applyCSS(content)
        print(content)

        createHTMLFile(content, html_dir, path)


def build_pdf(html_dir: str, pdf_dir: str):
    removeDirectory(pdf_dir)

    # resources from html dir to pdf dir
    createResourceDirectory(html_dir, pdf_dir)

    # ✅ Safety: ensure watermark exist in pdf output too
    # (If createResourceDirectory already copied it, this just overwrites same file.)
    copyGlobalBackgroundToOutput(pdf_dir, "./watermark")

    html_paths = collectAllHTMLFileRelativePaths(html_dir)
    for path in html_paths:
        content = readHTMLFile(html_dir, path)
        print(content)

        content = replaceLinkFromHTMLToPDF(content)
        print(content)

        createPDFFile(content, pdf_dir, path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_dir", default="./test/input", help="Input root directory")
    parser.add_argument("--md_dir", default="./test/markdown", help="Markdown output directory")
    parser.add_argument("--html_dir", default="./test/html", help="HTML output directory")
    parser.add_argument("--pdf_dir", default="./test/pdf", help="PDF output directory")

    parser.add_argument(
    "--out",
    nargs="+",
    required=True,
    help=(
        "Output types:\n"
        "  1 = HTML\n"
        "  2 = Markdown\n"
        "  3 = PDF\n"
        "\n"
        "Examples:\n"
        "  --out 1\n"
        "  --out 2\n"
        "  --out 3\n"
        "  --out 1,3\n"
        "  --out 123\n"
        "  --out 1 2 3\n"
    )
)
    parser.add_argument(
        "--keep_temp",
        action="store_true",
        help="Keep intermediate directories when only HTML/PDF are requested"
    )

    args = parser.parse_args()
    out_set = parse_out_selection(args.out)
    if not out_set:
        raise SystemExit("No valid --out selection. Use 1, 2, 3 (or combinations like 1,3 / 13 / 1 2 3).")

    need_md = (2 in out_set) or (1 in out_set) or (3 in out_set)
    need_html = (1 in out_set) or (3 in out_set)
    need_pdf = (3 in out_set)

    # If user didn't request Markdown but we need it as intermediate, treat as temp
    md_is_temp = (2 not in out_set)
    html_is_temp = (1 not in out_set) and (3 in out_set)

    # Build Markdown (always required for HTML/PDF in your pipeline)
    if need_md:
        build_markdown(args.in_dir, args.md_dir)

    # Build HTML if needed
    if need_html:
        build_html(args.md_dir, args.html_dir)

    # Build PDF if needed
    if need_pdf:
        build_pdf(args.html_dir, args.pdf_dir)

    # Cleanup temps unless keep_temp
    if not args.keep_temp:
        if md_is_temp:
            removeDirectory(args.md_dir)
        if html_is_temp:
            removeDirectory(args.html_dir)

    print("Done.")
    print(f"Requested outputs: {sorted(list(out_set))}")
    if 2 in out_set:
        print(f"- Markdown: {args.md_dir}")
    if 1 in out_set:
        print(f"- HTML:     {args.html_dir}")
    if 3 in out_set:
        print(f"- PDF:      {args.pdf_dir}")


if __name__ == "__main__":
    main()