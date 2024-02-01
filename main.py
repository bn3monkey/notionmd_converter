# Before Using it, please run `python -m pip install markdown-it-py`
# Before using it, please run `python -m pip install pandas`
# Before using it, please run `python -m pip install tabulate`
from markdown_it import MarkdownIt
import os
import glob
import shutil
import re
import urllib.parse
import sys
import unicodedata
import pandas

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
    name = words[0]
    extension = words[1]
     
    is_png_file = extension == 'png' or extension == 'PNG'
    converted_name = removeUnnecessaryWord(name, is_png_file)
    return f"{converted_name}.{extension}"

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


def collectAllMarkdownFiles(directory : str) :
    md_files = glob.glob(os.path.join(directory, "**/*.md"),recursive=True)
    return md_files

def readMarkdownFile(filePath : str) :
    content = ""
    with open(filePath, 'r', encoding='utf-8') as file :
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

def replace_csv(markdown_text, filePath) :
    directoryname = os.path.dirname(filePath)

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
    input("Press Enter!")

    createIntermediateDirectory("./test/input", "./test/intermediate", directorypath_map, filepath_map)
    # input("Press Enter!")

    files = collectAllMarkdownFiles("./test/intermediate")
    for file in files :
        print(file)
    # input("Press Enter!")

    md = MarkdownIt("commonmark").enable('table')

    count = 0
    for file in files :
        count = count + 1
        content = readMarkdownFile(file)
        print(f"======= File Name : {file} ======\n")

        print(content)

        print(f"======= File Name : {file} ======\n")

        converted_content = replace_link_urls(content)
        print(converted_content)

        csv_converted_content = replace_csv(converted_content, file)
        print(csv_converted_content)

        newline_content = replaceNewLineInMarkdownTable(csv_converted_content)
        print(newline_content)

        with open(file, "w") as mdfile :
            mdfile.write(newline_content)

    

          

# print(f"======= File Parse Tree : {file} ======\n")

# tokens = md.parse(content)
# with open(f"./test/log/token_{count}.txt", "w") as token_file :
#     for token in tokens :
#         print(token)
#         token_file.write(f"{token}\n")

# filtered_tokens = [token for token in tokens if token.type == 'inline' ]
# with open(f"./test/log/filtered_token_{count}.txt", "w") as token_file :
#     for token in filtered_tokens :
#         print(token)
#         token_file.write(f"{token}\n")


# print(f"======= File Parse Tree : {file} ======\n")
