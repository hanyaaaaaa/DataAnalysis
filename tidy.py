import pandas as pd
from bs4 import BeautifulSoup
import re
import os
import requests
import pdfplumber

# 設定資料夾和輸出路徑
input_dir = "C:/Users/李/Desktop/數據分析"
output_path = "C:/Users/李/Desktop/數據分析/importantcsv/import.csv"

# 中文數字轉換
def chinese_to_number(text):
    mapping = {'零': 0, '壹': 1, '貳': 2, '參': 3, '肆': 4, '伍': 5, '陸': 6, '柒': 7, '捌': 8, '玖': 9, 
               '拾': 10, '佰': 100, '仟': 1000, '萬': 10000}
    num = 0
    temp = 0
    for char in text:
        if char in mapping:
            if char in '拾佰仟萬':
                temp = temp or 1
                num += temp * mapping[char]
                temp = 0
            else:
                temp = mapping[char]
    return num + temp if temp else num

# 初始化資料列表
all_cases = []

# 迴圈處理檔案
for i in range(1, 411):  
    file_path = os.path.join(input_dir, f"case_{i}_detail.html")
    
    if not os.path.exists(file_path):
        print(f"⚠️ 檔案不存在：{file_path}")
        continue

    # 讀取 HTML
    with open(file_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # 從 <title> 提取基本資訊
    court_name = soup.find("title").text.strip().split(" ")[0] if soup.find("title") else "未知"
    title_text = soup.find("title").text.strip() if soup.find("title") else ""
    # 從 <title> 提取日期
    date_match = re.search(r"(\d{3,4})\s*年度", title_text)
    judgment_date = f"民國 {date_match.group(1)} 年" if date_match else "未知"
    # 從 HTML 提取更精確日期
    date_elem = soup.select_one(".int-table .row:nth-child(2) .col-td")
    if date_elem:
        judgment_date = date_elem.text.strip()
    case_type = "聲請定應執行刑" if "聲字第" in title_text else "未知"

    # 提取相關法條、罪名、刑期和上下文
    laws = []
    offenses = []
    sentences = []
    raw_content = []

    # 從 PDF 提取
    pdf_link = soup.find("a", id="hlExportPDF")
    if pdf_link:
        pdf_url = "https://judgment.judicial.gov.tw" + pdf_link["href"]
        pdf_path = os.path.join(input_dir, f"case_{i}_detail.pdf")
        
        try:
            response = requests.get(pdf_url, timeout=10)
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(response.content)

            with pdfplumber.open(pdf_path) as pdf:
                text = "".join(page.extract_text() or "" for page in pdf.pages if page.extract_text())
                
                # 提取日期（備用）
                if judgment_date == "未知":
                    date_match = re.search(r"民國\s*(\d{3,4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
                    if date_match:
                        judgment_date = f"民國 {date_match.group(1)} 年 {date_match.group(2)} 月 {date_match.group(3)} 日"
                
                # 提取案件類型
                if case_type == "未知":
                    case_match = re.search(r"裁判案由\D*([^\n]+)", text)
                    case_type = case_match.group(1).strip() if case_match else "未知"
                
                # 提取主文
                main_match = re.search(r"主\s*文\s*(.+?)(?:事\s*實|理\s*由|$)", text, re.DOTALL)
                if main_match:
                    main_content = main_match.group(1).strip()
                    raw_content.append(re.sub(r'\n\d+\s*', ' ', main_content))  # 移除行號
                    offense_match = re.findall(r"犯(.+?罪)", main_content)
                    sentence_match = re.findall(r"處\s*([^，。]+[年月日])|應執行([^，。]+[年月日])", main_content)
                    if offense_match:
                        offenses.extend([o.strip() for o in offense_match])
                    if sentence_match:
                        for match in sentence_match:
                            sentence = next((s for s in match if s), None)
                            if sentence:
                                sentences.append(sentence.strip())
                
                # 提取附表
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:
                            headers = table[0]
                            offense_idx = -1
                            sentence_idx = -1
                            for idx, header in enumerate(headers):
                                if header and "罪" in header and "日期" not in header:
                                    offense_idx = idx
                                if header and "刑" in header:
                                    sentence_idx = idx
                            if offense_idx != -1 and sentence_idx != -1:
                                for row in table[1:]:
                                    if len(row) > max(offense_idx, sentence_idx):
                                        offense = row[offense_idx].strip() if row[offense_idx] else ""
                                        sentence = row[sentence_idx].strip() if row[sentence_idx] else "未知"
                                        if offense and "罪" in offense:
                                            offenses.append(offense)
                                            sentences.append(sentence)
                                            raw_content.append(f"{offense}，處{sentence}")
                
                # 提取法條
                law_match = re.findall(r"(?:中華民國刑法|刑事訴訟法|洗錢防制法)[^\n]+", text)
                if law_match:
                    laws.extend(law_match)

            os.remove(pdf_path)
        except Exception as e:
            print(f"⚠️ PDF 下載或解析失敗：{file_path}，錯誤：{e}")

    # 清理格式
    offenses = list(set(o.strip() for o in offenses if o.strip() and "罪" in o and "日期" not in o and "編號" not in o)) or ["未知"]
    sentences = [re.sub(r"如易科罰金.*$", "", s.strip()) for s in sentences if s.strip()]
    sentences = [f"{chinese_to_number(re.sub(r'[年月日]', '', s))}{next((c for c in '年月日' if c in s), '月' if '有期徒刑' in s else '日' if '拘役' in s else '')}" 
                 for s in sentences if any(c in s for c in "年月日") or "有期徒刑" in s or "拘役" in s] or ["未知"]

    # 若罪名含「如附表所示」，用附表罪名替換
    if any("附表" in o or "附件" in o for o in offenses):
        offenses = [o for o in offenses if "附表" not in o and "附件" not in o] or ["未知"]

    # 建立案件資料
    case_data = {
        "法院名稱": court_name,
        "裁判日期": judgment_date,
        "案件類型": case_type,
        "罪名": "; ".join(offenses),
        "刑期": "; ".join(sentences),
        "相關法條": "; ".join(laws) if laws else "無",
        "原始內容": "; ".join(raw_content) if raw_content else "無"
    }

    all_cases.append(case_data)
    print(f"✅ 已處理：{file_path}")

# 轉換為 DataFrame 並存成 CSV
df = pd.DataFrame(all_cases)
df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"📂 所有案件資料已儲存為：{output_path}")