import os
import pandas as pd
from datetime import datetime
import re
import logging
def convert_sentence_to_days(sentence):
    """將刑期轉換為天數"""
    if pd.isna(sentence) or sentence == '未知':
        return 0
    total_days = 0
    for part in str(sentence).split(';'):  # 以分號分隔
        part = part.strip()
        if '年' in part:
            years = int(part.replace('年', '').strip())
            total_days += years * 365
        elif '月' in part:
            months = int(part.replace('月', '').strip())
            total_days += months * 30
        elif '日' in part:
            days = int(part.replace('日', '').strip())
            total_days += days
    return total_days

def calculate_weight(file_date, current_date):
    """根據日期計算權重"""
    days_difference = (current_date - file_date).days
    return max(1 / (1 + days_difference), 0.01)  # 避免除以零，設定最小權重



# 設置日誌，記錄解析問題
logging.basicConfig(filename='date_parsing.log', level=logging.INFO)

def parse_judgment_date(date_str):
    """解析裁判日期，支持只有年份的格式"""
    try:
        # 移除多餘的空格並標準化字符串
        date_str = date_str.strip()
        
        # 匹配完整格式：民國 XXX 年 XX 月 XX 日
        match_full = re.search(r'民國 (\d+) 年 (\d+) 月 (\d+) 日', date_str)
        if match_full:
            year = int(match_full.group(1)) + 1911  # 民國轉西元
            month = int(match_full.group(2))
            day = int(match_full.group(3))
            return datetime(year, month, day)
        
        # 匹配只有年份：民國 XXX 年
        match_year = re.search(r'民國 (\d+) 年', date_str)
        if match_year:
            year = int(match_year.group(1)) + 1911
            return datetime(year, 1, 1)  # 默認為 1 月 1 日
        
        # 如果無法解析，記錄並返回 None
        logging.info(f"無法解析的日期: {date_str}")
        return None
    except Exception as e:
        logging.error(f"解析日期時發生錯誤: {e}, 日期: {date_str}")
        return None

# 示例使用
# date = "民國 114 年"
# parsed_date = parse_judgment_date(date)
# print(parsed_date)  # 應輸出 2025-01-01 00:00:00

def process_csv_files(input_folder):
    """處理資料夾中的CSV檔案"""
    current_date = datetime.now()
    processed_data = []

    for file_name in os.listdir(input_folder):
        if file_name.endswith('.csv'):
            file_path = os.path.join(input_folder, file_name)
            df = pd.read_csv(file_path)

            # 解析裁判日期
            if '裁判日期' in df.columns:
                df['裁判日期'] = df['裁判日期'].apply(parse_judgment_date)
                df = df.dropna(subset=['裁判日期'])  # 移除無效日期的行

                # 根據裁判日期計算權重
                df['權重'] = df['裁判日期'].apply(lambda x: calculate_weight(x, current_date))

                # 如果有刑期欄位，轉換為天數
                if '刑期' in df.columns:
                    df['刑期(天)'] = df['刑期'].apply(convert_sentence_to_days)

                processed_data.append(df)
            else:
                print(f"跳過無'裁判日期'欄位的檔案：{file_name}")

    # 合併所有處理過的資料
    if processed_data:
        combined_df = pd.concat(processed_data, ignore_index=True)
        return combined_df
    else:
        print("無有效的CSV檔案被處理。")
        return pd.DataFrame()

# 主執行流程
input_folder = 'C:/Users/李/Desktop/數據分析/importantcsv'  # 輸入資料夾路徑
output_file = 'C:/Users/李/Desktop/數據分析/outputarea/Tovector.csv'  # 輸出檔案路徑

processed_df = process_csv_files(input_folder)
if not processed_df.empty:
    processed_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"處理後的資料已儲存至 {output_file}")
else:
    print("無資料可儲存。")