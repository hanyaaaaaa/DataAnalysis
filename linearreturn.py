import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, Ridge 
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# 讀取數據
try:
    df = pd.read_csv('C:/Users/李/Desktop/數據分析/outputarea/Tovector.csv')
except Exception as e:
    print(f"❌ 無法讀取數據文件: {e}")
    exit()

# 過濾無刑期數據並添加對數變換
df_with_sentence = df[df['刑期(天)'] > 0].copy()
df_with_sentence['刑期(天)_log'] = np.log1p(df_with_sentence['刑期(天)'])
print(f"過濾後數據量: {len(df_with_sentence)} 行")

# 載入嵌入模型
try:
    model = SentenceTransformer('DMetaSoul/sbert-chinese-general-v2')
    print("✅ 已載入通用模型：DMetaSoul/sbert-chinese-general-v2")
except Exception as e:
    print(f"❌ 無法載入模型: {e}")
    exit()

# 處理文本向量
try:
    text_embeddings = model.encode(df_with_sentence["原始內容"].tolist())
except Exception as e:
    print(f"❌ 文本向量化失敗: {e}")
    exit()

# 準備特徵和標籤
X = text_embeddings
y = df_with_sentence['刑期(天)_log'].values  # 使用對數變換後的刑期

# 切分數據
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 訓練線性回歸模型
regressor = LinearRegression()
# 或者使用 Ridge 回歸（取消註解以啟用）
# regressor = Ridge(alpha=1.0)
regressor.fit(X_train, y_train)

# 預測
y_pred_log = regressor.predict(X_test)
y_pred = np.expm1(y_pred_log)  # 反轉換回原始單位
y_test_original = np.expm1(y_test)  # 反轉換回原始單位

# 評估
mse = mean_squared_error(y_test_original, y_pred)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test_original, y_pred)
r2 = r2_score(y_test_original, y_pred)

print(f"\n=== 純線性回歸模型評估指標（使用對數變換）===")
print(f"MSE（均方誤差）: {mse:.2f} 天²")
print(f"RMSE（均方根誤差）: {rmse:.2f} 天")
print(f"MAE（平均絕對誤差）: {mae:.2f} 天")
print(f"R² 分數（決定係數）: {r2:.4f}")
if r2 < 0:
    print("⚠️ R² 為負數，模型預測效果比簡單均值預測還差！")
else:
    print(f"🎉 R² 為正數，模型已能捕捉 {r2*100:.1f}% 的刑期變異性！")