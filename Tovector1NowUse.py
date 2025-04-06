import os
import pandas as pd
from datetime import datetime
import re
import logging

# 設置日誌
logging.basicConfig(
    filename='C:/Users/李/Desktop/數據分析/date_parsing.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# 中文數字轉換表
CHINESE_NUMS = {
    '零': 0, '壹': 1, '貳': 2, '參': 3, '肆': 4,
    '伍': 5, '陸': 6, '柒': 7, '捌': 8, '玖': 9,
    '拾': 10, '佰': 100, '仟': 1000
}

def convert_chinese_to_arabic(text):
    """將中文數字轉換為阿拉伯數字"""
    if not text:
        return text
    num = 0
    temp = 0
    for char in text:
        if char in CHINESE_NUMS:
            if char in '拾佰仟':
                temp = (temp or 1) * CHINESE_NUMS[char]
            else:
                temp += CHINESE_NUMS[char]
        else:
            num += temp
            temp = 0
    num += temp
    return str(num) if num > 0 else text

def convert_sentence_to_days(sentence):
    """將刑期轉換為天數，支援帶單位的刑期，並處理無效輸入"""
    if pd.isna(sentence) or sentence == '未知' or not sentence:
        return 0
    total_days = 0
    for part in str(sentence).split(';'):  # 以分號分隔多段刑期
        part = part.strip()
        if not part:  # 跳過空字符串
            continue
        try:
            if '年' in part:
                years = int(re.sub(r'[年]', '', part))
                total_days += years * 365
            elif '月' in part:
                months = int(re.sub(r'[月]', '', part))
                total_days += months * 30
            elif '日' in part:
                days = int(re.sub(r'[日]', '', part))
                total_days += days
        except ValueError as e:
            logging.warning(f"無法解析刑期部分: {part}, 錯誤: {e}")
            continue
    return total_days

def calculate_weight(file_date, current_date):
    """根據日期計算權重"""
    days_difference = (current_date - file_date).days
    return max(1 / (1 + days_difference), 0.01)

def parse_judgment_date(date_str):
    """解析裁判日期，支持只有年份的格式"""
    try:
        date_str = date_str.strip()
        match_full = re.search(r'民國 (\d+) 年 (\d+) 月 (\d+) 日', date_str)
        if match_full:
            year = int(match_full.group(1)) + 1911
            month = int(match_full.group(2))
            day = int(match_full.group(3))
            return datetime(year, month, day)
        match_year = re.search(r'民國 (\d+) 年', date_str)
        if match_year:
            year = int(match_year.group(1)) + 1911
            return datetime(year, 1, 1)
        logging.info(f"無法解析的日期: {date_str}")
        return None
    except Exception as e:
        logging.error(f"解析日期時發生錯誤: {e}, 日期: {date_str}")
        return None

def extract_sentence_from_content(content):
    """從原始內容中提取刑期，保留單位"""
    if pd.isna(content) or not content:
        logging.info("原始內容為空，無法提取刑期")
        return '未知'

    content = re.sub(r'\s+', ' ', content.strip())

    patterns = [
        r'應\s*執\s*行(?:.*?)(?:有期徒刑|拘役)\s*((?:[\d零壹貳參肆伍陸柒捌玖拾佰仟]+\s*年)?(?:[\d零壹貳參肆伍陸柒捌玖拾佰仟]+\s*月)?(?:[\d零壹貳參肆伍陸柒捌玖拾佰仟]+\s*日)?)',
        r'處(?:.*?)(?:有期徒刑|拘役)\s*((?:[\d零壹貳參肆伍陸柒捌玖拾佰仟]+\s*年)?(?:[\d零壹貳參肆伍陸柒捌玖拾佰仟]+\s*月)?(?:[\d零壹貳參肆伍陸柒捌玖拾佰仟]+\s*日)?)'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            last_match = matches[-1].strip()
            parts = re.split(r'\s+', last_match)
            sentence_parts = []
            for part in parts:
                num = convert_chinese_to_arabic(re.sub(r'[年月日]', '', part))
                if '年' in part:
                    sentence_parts.append(f"{num}年")
                elif '月' in part:
                    sentence_parts.append(f"{num}月")
                elif '日' in part:
                    sentence_parts.append(f"{num}日")
            extracted = '; '.join(sentence_parts)
            logging.info(f"成功提取刑期: {extracted}")
            return extracted
    logging.warning(f"無法從內容提取刑期: {content}")
    return '未知'

def process_csv_files(input_folder):
    """處理資料夾中的CSV檔案"""
    current_date = datetime.now()
    processed_data = []

    for file_name in os.listdir(input_folder):
        if file_name.endswith('.csv'):
            file_path = os.path.join(input_folder, file_name)
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except Exception as e:
                logging.error(f"無法讀取檔案 {file_path}: {e}")
                continue

            if '裁判日期' in df.columns:
                df['裁判日期'] = df['裁判日期'].apply(parse_judgment_date)
                df = df.dropna(subset=['裁判日期'])

                df['權重'] = df['裁判日期'].apply(lambda x: calculate_weight(x, current_date))

                if '刑期' in df.columns:
                    if '原始內容' in df.columns:
                        df['刑期'] = df['原始內容'].apply(extract_sentence_from_content)
                    df['刑期(天)'] = df['刑期'].apply(convert_sentence_to_days)

                processed_data.append(df)
            else:
                print(f"跳過無'裁判日期'欄位的檔案：{file_name}")
                logging.warning(f"檔案缺少'裁判日期'欄位: {file_name}")

    if processed_data:
        combined_df = pd.concat(processed_data, ignore_index=True)
        return combined_df
    else:
        print("無有效的CSV檔案被處理。")
        return pd.DataFrame()

# 主執行流程
input_folder = 'C:/Users/李/Desktop/數據分析/importantcsv'
output_file = 'C:/Users/李/Desktop/數據分析/outputarea/Tovector.csv'

os.makedirs(os.path.dirname(output_file), exist_ok=True)

processed_df = process_csv_files(input_folder)
if not processed_df.empty:
    processed_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"處理後的資料已儲存至 {output_file}")
else:
    print("無資料可儲存。")