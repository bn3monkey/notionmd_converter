# Before using it, please run `python -m pip install pandas`
# Before using it, please run `python -m pip install tabulate`
# Before using it, please run `python -m pip install linkify-it-py`
# Before using it, please run `python -m pip install selenium`
# Before using it, please run `python -m pip install beautifulsoup4`

# Before run it, `source venv/Scripts/activate`
# defendency markdown-it-py, pandas, tabulate``

import markdown
import os
import glob
import shutil
import re
import urllib.parse
import sys
import unicodedata
import pandas
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

print(sys.getdefaultencoding())

def collectDirectoryAndFileNames(directory : str) :

    directory_paths = []
    filename_paths = []
    for root, dirs, files in os.walk(directory) :
        relative_path = os.path.relpath(root, directory)
        relative_path = relative_path.replace("\\", "/")
        directory_paths.append(relative_path)

        for file in files : 
            file_path = os.path.join(root, file)
            relative_file_path = os.path.relpath(file_path, directory)
            relative_file_path = relative_file_path.replace("\\", "/")
            filename_paths.append(relative_file_path)
    directory_paths.remove(".")
    return directory_paths, filename_paths 


def removeUnnecessaryWord(directory_name, is_png_file = False) :
    words = directory_name.split(' ')
    if is_png_file == False:
        if len(words) > 1 :
            words.pop()
    
    return '_'.join(words)

def linkDirectoryName(directory_path) :
    names = directory_path.split('/')
    converted_names = [removeUnnecessaryWord(name) for name in names]
    ret = '/'.join(converted_names)
    ret = unicodedata.normalize('NFC', ret)
    return ret
    
def createDirectoryNameMap(directory_paths) :
    return {key : linkDirectoryName(key) for key in directory_paths}

def changeFileName(filename) :
    print(filename)
    words = filename.split('.')
    extension=words[-1]    
   
     
    is_png_file = extension == 'png' or extension == 'PNG'
   
    for i in range(len(words) - 1):  # 마지막 요소는 제외하도록 범위를 설정합니다.
        words[i] = removeUnnecessaryWord(words[i], is_png_file)
    return ".".join(words)

def linkFileName(file_path) :
    names = file_path.split('/')
    filename = names[-1]
    directory_names = names[:-1]
    converted_directory_names = [removeUnnecessaryWord(name) for name in directory_names]
    converted_filename = changeFileName(filename)
    ret = ""
    if len(converted_directory_names) != 0 :
        converted_directory_name = '/'.join(converted_directory_names)
        ret = f"{converted_directory_name}/{converted_filename}"
    else :
        ret = converted_filename
    ret = unicodedata.normalize('NFC', ret)
    return ret

def createFileNameMap(file_paths) :
    return {key : linkFileName(key) for key in file_paths}

def convertURLToUTF8(url) :
    new_url = urllib.parse.unquote(url, 'utf-8')
    new_url = unicodedata.normalize('NFC', new_url)
    return new_url

def createIntermediateDirectory(input_path : str, output_path : str, directorypath_map, filepath_map) :
    os.makedirs(output_path, exist_ok=True)
    for root, dirs, files in os.walk(input_path) : 
        relative_path = os.path.relpath(root, input_path)
        relative_path = relative_path.replace("\\", "/")
        if relative_path[0] != '.' :
            new_directory_path = directorypath_map[relative_path]
            os.makedirs(os.path.join(output_path, new_directory_path), exist_ok=True)

        for file in files : 
            file_path = os.path.join(root, file)
            relative_file_path = os.path.relpath(file_path, input_path)
            relative_file_path = relative_file_path.replace("\\", "/")
            new_file_path = filepath_map[relative_file_path]
            new_full_file_path = os.path.join(output_path, new_file_path)
            print(f"copy File : {file_path} -> {new_full_file_path}")
            shutil.copy(file_path, new_full_file_path)

def createResourceDirectory(input_path : str, output_path : str) :
    os.makedirs(output_path, exist_ok=True)
    for root, dirs, files in os.walk(input_path) :
        relative_path = os.path.relpath(root, input_path)
        relative_path = relative_path.replace("\\", "/")
        output_directory_path = os.path.join(output_path, relative_path)
        if relative_path[0] != '.' :
            os.makedirs(output_directory_path, exist_ok=True)

        for file in files :
            _, extension = os.path.splitext(file)
            if extension.lower() in ['.jpg', '.png', '.bmp','.svg'] :
                src_path = os.path.join(root, file)
                dest_path = os.path.join(output_directory_path, file)
                shutil.copy(src_path, dest_path)

def removeCSVFiles(directory : str) :
    for root, dirs, files in os.walk(directory) :
        for file in files :
            _, extension = os.path.splitext(file)
            if extension.lower() in ['.csv'] :
                src_path = os.path.join(root, file)
                os.remove(src_path)

def collectAllMarkdownFiles(directory : str) :
    md_files = glob.glob(os.path.join(directory, "**/*.md"),recursive=True)
    return md_files

def readMarkdownFile(root_path : str, relative_path : str) :
    content = ""
    with open(f"{root_path}/{relative_path}", 'r', encoding='utf-8') as file :
        content = file.read()
    return content

def readHTMLFile(root_path : str, relative_path : str) :
    content = ""
    with open(f"{root_path}/{relative_path}", 'r', encoding='utf-8') as file :
        content = file.read()
    return content

def replace_link_urls(markdown_text) :
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')

    def replace_url(match) :
        link_text, old_url = match.groups()
        print(f"link_text : {link_text} old_url : {old_url}")
        
        if old_url.startswith("https://") :
            return f"[{link_text}]({old_url})"
        
        linkUTF8 = convertURLToUTF8(old_url)
        new_url = linkFileName(linkUTF8)
        print(f"new_url : {new_url}")
        return f"[{link_text}]({new_url})"

    updated_text = link_pattern.sub(replace_url, markdown_text)
    return updated_text

def csvToTable(path : str) :
    print(f"csv path : {path}")
    df = pandas.read_csv(path)
    table = df.to_markdown(index = False)
    return table

def replace_csv(markdown_text, root_path, relative_path) :
    full_path = f"{root_path}/{relative_path}"
    directoryname = os.path.dirname(full_path)

    link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')


    def replace_url(match) :
        link_text, old_url = match.groups()
        print(f"link_text : {link_text} old_url : {old_url}")
        
        if old_url.endswith(".csv") :
            table = csvToTable(f"{directoryname}/{old_url}")
            return f"{table}\n"
        
        return f"[{link_text}]({old_url})"

    updated_text = link_pattern.sub(replace_url, markdown_text)
    return updated_text

def replaceNewLineInMarkdownTable(text) :
    # 정규 표현식을 사용하여 |와 | 사이의 모든 문장을 찾기
    cell_pattern = re.compile(r'\|([^\n|]+(\n[^\n|]+)*)')
    matches = cell_pattern.findall(text)

    # 각 매치된 문장에 대해 \n을 </br>로 바꾸기
    for match in matches:
        # print(match)
        # input("")
        sentence = match[0]
        replaced_sentence = sentence.replace('\n', '</br>')
        text = text.replace(f'|{sentence}|', f'|{replaced_sentence}|')

    return text

def generateHeaderMetadata(markdown_text) :
    def generateAnchor(header_text) :
        return re.sub(r'[^\w\s]', '', header_text).strip().lower().replace(" ", "-") 
    
    def removeMarkdownSyntax(text) :
         # **text**를 text로 변경
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)

        # `text`를 text로 변경
        text = re.sub(r'`([^`]+)`', r'\1', text)

        return text

    headers = re.findall(r'^(#+)\s+(.*)$', markdown_text, flags=re.MULTILINE)

    header_metadata = []

    count = 0
    for header in headers :
        header_level = len(header[0])
        header_text = header[1]
        header_text = removeMarkdownSyntax(header_text)

        header_anchor = generateAnchor(header_text)
        
        header_metadata.append({ "level" : header_level, "text" : header_text, "anchor" : f"{count}-{header_anchor}"})        
        count = count + 1
    
    return header_metadata


def generateTableOfContent(header_metadata) :
    ret = "\n\n"
    for header in header_metadata :
        text = header["text"]
        anchor = header["anchor"]
        ret += "\t" * (header["level"] -1) 
        ret += f"- [{text}](#{anchor})\n"
    ret += "\n"

    return ret

def insertTableOfContent(markdown_text, toc) :

    match = re.search(r'^(#+)\s+(.*)$', markdown_text, flags=re.MULTILINE)
    idx = -1
    if match :
        idx = match.end()

    ret = markdown_text[:idx] + toc + markdown_text[idx:]
    return ret   


def collectAllMarkdownFileRelativePaths(root_path : str) :
    paths = []
    for root, dirs, files in os.walk(root_path) :

        for file in files : 
            if file.endswith(".md") :
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(file_path, root_path)
                relative_file_path = relative_file_path.replace("\\", "/")
                paths.append(relative_file_path)

    return paths

def collectAllHTMLFileRelativePaths(root_path : str) :
    paths = []
    for root, dirs, files in os.walk(root_path) :

        for file in files : 
            if file.endswith(".html") :
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(file_path, root_path)
                relative_file_path = relative_file_path.replace("\\", "/")
                paths.append(relative_file_path)

    return paths

def replaceLinkFromMarkdownToHTML(markdown_text) :
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')

    def replace_url(match) :
        link_text, old_url = match.groups()
        print(f"link_text : {link_text} old_url : {old_url}")
        new_url = old_url.replace(".md", ".html")        
        return f"[{link_text}]({new_url})"

    updated_text = link_pattern.sub(replace_url, markdown_text)
    return updated_text

def replaceLinkFromHTMLToPDF(html_text) :
    link_pattern = re.compile(r'<a\s+href="([^"]+\.html)">')

    def replace_url(match) :
        old_url = match.group(0)
        new_url = old_url.replace(".html", ".pdf")        
        return f"{new_url}"

    updated_text = link_pattern.sub(replace_url, html_text)
    return updated_text

def createMarkdownFile(content : str, root_path : str, relative_path : str) :
    full_path = f"{root_path}/{relative_path}"
    directoryname = os.path.dirname(full_path)
    os.makedirs(directoryname, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as result_file :
        result_file.write(content)

def createHTMLContent(markdown_text : str) :
    md = markdown.Markdown(extensions=['tables'])
    html = md.convert(markdown_text)
    return html

def addAnchorToHTMLHeader(html_content, header_map) :
    soup = BeautifulSoup(html_content, 'html.parser')

    headers = soup.find_all(re.compile('^h\d'))
    
    count = 0
    for header in headers :
        header_metadata = header_map[count]
        anchor = header_metadata["anchor"]

        header["id"] = anchor
        count += 1


    return str(soup)

def applyCSS(html_content : str) :
    html_body = ""
    main_file_path = os.path.dirname(os.path.abspath(__file__))
    with open(f"{main_file_path}/apply_markdown.html", "r") as apply_markdown_file :
        html_body = apply_markdown_file.read()
    print(html_body)
    print(type(html_body))
    new_body = html_body.format(html_content)
    print(new_body)
    return new_body

def createHTMLFile(content, root_path, relative_path) :
    full_path = f"{root_path}/{relative_path}"
    directoryname = os.path.dirname(full_path)
    os.makedirs(directoryname, exist_ok=True)

    html_path = full_path.replace(".md", ".html")
    with open(html_path, "w", encoding="utf-8") as result_file :
        result_file.write(content)



def createPDFFile(content : str, root_path : str, relative_path : str) :
    full_path = f"{root_path}/{relative_path}"
    print(f"fullpath : {full_path}")
    directoryname = os.path.dirname(full_path)
    os.makedirs(directoryname, exist_ok=True)

    pdf_path = full_path.replace(".html", ".pdf")

    chrome_options = Options()
    chrome_options.add_argument('--headless')

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("document.write(arguments[0]);", content)
    time.sleep(1)
    
    options={"paperWidth": 8.3, "paperHeight":11.7, "marginTop": 0, "marginBottom":0, "marginLeft":0, "marginRight":0}
    pdf_data = driver.execute_cdp_cmd("Page.printToPDF",options)
    pdf_data = pdf_data["data"]
    if pdf_path is not None:
        with open(pdf_path, "wb") as f :
            f.write(base64.b64decode(pdf_data))
            f.close()
        

if __name__ == "__main__" : 
    directory_paths, filename_paths = collectDirectoryAndFileNames("./test/input")
    for directoryname in directory_paths :
        print(directoryname)
    print("\n")
    for filename in filename_paths :
        print(filename)
    # input("Press Enter!")
    
    directorypath_map = createDirectoryNameMap(directory_paths)
    for key, value in directorypath_map.items() :
        print(f"{key} -> {value}")
    # input("Press Enter!")

    filepath_map = createFileNameMap(filename_paths)
    for key, value in filepath_map.items() :
        print(f"{key} -> {value}")
   
    createIntermediateDirectory("./test/input", "./test/markdown", directorypath_map, filepath_map)
        
    paths = collectAllMarkdownFileRelativePaths("./test/markdown")
    for path in paths :
        content = readMarkdownFile("./test/markdown", path)
        print(f"======= File Name : {path} ======\n")

        print(content)

        print(f"======= File Name : {path} ======\n")

        content = replace_link_urls(content)
        print(content)

        content = replace_csv(content, "./test/markdown", path)
        print(content)

        content = replaceNewLineInMarkdownTable(content)
        print(content)

        metadata = generateHeaderMetadata(content)
        toc = generateTableOfContent(metadata)

        content = insertTableOfContent(content, toc)
        print(content)

        createMarkdownFile(content, "./test/markdown", path)
    removeCSVFiles("./test/markdown")

    createResourceDirectory("./test/markdown", "./test/html")
    paths = collectAllMarkdownFileRelativePaths("./test/markdown")
    for path in paths :
        content = readMarkdownFile("./test/markdown", path)

        content = replaceLinkFromMarkdownToHTML(content)
        print(content)

        metadata = generateHeaderMetadata(content)

        content = createHTMLContent(content)
        print(content)

        content = addAnchorToHTMLHeader(content, metadata)
        print(content)
        
        content = applyCSS(content)
        print(content)
        
        createHTMLFile(content, "./test/html", path)
    

    createResourceDirectory("./test/html", "./test/pdf")
    paths = collectAllHTMLFileRelativePaths("./test/html")
    for path in paths :
        content = readHTMLFile("./test/html", path)
        print(content)

        content = replaceLinkFromHTMLToPDF(content)
        print(content)

        createPDFFile(content, "./test/pdf", path)
