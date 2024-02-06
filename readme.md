# Notion Markdown Converter

## 사용법

### Windows 사용법

1. 파이썬 가상환경 만들기
```bash
python -m venv
```

2. 가상환경 활성화 하기
```bash
source venv/Scripts/activate
``` 

3. 종속성 설치하기
```bash
pip install -r requirements.txt
```

4. test/input에 notion에서 뽑은 하위 디렉토리를 포함한 md 파일 넣기

5. 실행하기
```bash
python main.py
```

6. 가상환경 빠져나오기
```bash
deactivate
```

## 종속성 추출

1. 개발 중 새로운 종속성이 생겼을 때, 아래의 명령어로 추출한다.

```bash
pip freeze > requirements.txt
```
