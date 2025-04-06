from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.proxy import Proxy, ProxyType

proxy = Proxy()
proxy.proxy_type = ProxyType.MANUAL
proxy.socks_proxy = '127.0.0.1:9050'  # Tor 的 SOCKS5 代理端口
proxy.socks_version = 5  # 使用 SOCKS5 協議

# 配置 ChromeOptions，並將代理設置傳入
options = webdriver.ChromeOptions()
options.add_argument('--proxy-server=socks5://127.0.0.1:9050')  # 設置 SOCKS5 代理
options.add_argument('--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"')
options.headless =True  # 設 True 可隱藏瀏覽器

# 使用 Service 和 ChromeOptions 啟動 Chrome 瀏覽器
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get('http://check.torproject.org')  # 檢查是否通過 Tor 網絡
try:
    # 進入裁判書查詢系統
    driver.get("https://judgment.judicial.gov.tw/FJUD/default.aspx")
    
    # 等待頁面載入
    WebDriverWait(driver, 50).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    # 定位搜尋輸入框，並輸入關鍵字「判決書」
    search_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "txtKW"))
    )
    search_box.clear()
    search_box.send_keys("判決書")
    search_box.send_keys(Keys.RETURN)
    
    # 等待搜尋結果頁面載入
    time.sleep(5)  # 等待幾秒鐘以確保搜尋結果載入完成
    
    idx = 0  # 初始化索引
    idxx= 267
    
    while True:
        try:
            # 切換到 iframe
            iframe = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "iframe-data"))
            )
            driver.switch_to.frame(iframe)
            time.sleep(2)
            # 抓取所有裁判書連結
            case_links = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "hlTitle_scroll"))
            )
            
            # 判斷是否還有未處理的裁判書
            if idx >= len(case_links):
                print("沒有更多裁判書可處理")
                ###
                try:
                    # 滾動到頁面底部以觸發翻頁
                    driver.switch_to.default_content()
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # 等待滾動完成
                    
                    # 等待 iframe 載入完成並切換
                    iframe = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.ID, "iframe-data"))
                    )
                    driver.switch_to.frame(iframe)
                    time.sleep(2)  
                    # 等待並定位下一頁按鈕
                    next_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.ID, "hlNext"))
                    )
                    
                    # 滾動到按鈕並點擊
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)  # 確保滾動完成
                    # 使用 JavaScript 點擊按鈕避免攔截問題
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)
                    driver.switch_to.default_content()  # 切換回主內容 #這行看起來可以註解看看
                    time.sleep(2)
                    '''iframe = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.ID, "iframe-data"))
                    )
                    driver.switch_to.frame(iframe)
                    time.sleep(2)
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "hlTitle_scroll"))
                    )
                    case_links = driver.find_elements(By.CLASS_NAME, "hlTitle_scroll")'''
                    print(f"翻頁成功，獲取到 {len(case_links)} 筆新裁判書")
                    idx=0
                    print("翻頁成功")
                    continue
                except Exception as e:
                    print(f"翻頁時發生錯誤: {e}")
                    break
                
            
            # 處理當前索引的裁判書
            link = case_links[idx]
            title = link.text.strip()  # 裁判書標題
            href = link.get_attribute("href")  # 取得連結的 href 屬性
            print(f"第 {idxx} 筆裁判書: {title}")
            print(f"連結: {href}\n")
            
            # 點擊該連結
            link.click()
            
            # 等待新頁面載入
            time.sleep(5)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # 抓取詳細頁面的內容
            with open(f"case_{idxx}_detail.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            
            # 返回搜尋結果頁面
            driver.back()
            
            # 等待回到結果頁面並保證結果已重新載入
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "iframe-data"))
            )
            
            driver.switch_to.default_content()  # 返回主頁面
            
            idx += 1  # 處理下一筆裁判書
            idxx+= 1
           
        except Exception as e:
            print(f"處理第 {idx+1} 筆裁判書時發生錯誤: {e}")
            break
            
finally:
    print()
    driver.quit()

   