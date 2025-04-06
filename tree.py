import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# 數據載入與嵌入
df = pd.read_csv('C:/Users/李/Desktop/數據分析/outputarea/Tovector.csv')
model = SentenceTransformer('DMetaSoul/sbert-chinese-general-v2')
text_embeddings = model.encode(df["原始內容"].tolist())

# 準備特徵和標籤
X = text_embeddings
y = df["刑期(天)"].values

# 切分數據
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 訓練隨機森林模型
regressor = RandomForestRegressor(n_estimators=100, random_state=42)
regressor.fit(X_train, y_train)

# 預測
y_pred = regressor.predict(X_test)

# 評估
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"均方誤差（MSE）: {mse}")
print(f"均方根誤差（RMSE）: {rmse}")
print(f"平均絕對誤差（MAE）: {mae}")
print(f"R² 分數: {r2}")

# 新案情預測
new_text = "侯智文所犯如附表所示各罪，所處如附表所載之有期徒刑，應執行有期徒刑2月，如易科罰金，以新臺幣1千元折算1日"
new_text_vec = model.encode([new_text])
predicted_days = regressor.predict(new_text_vec)
print(f"預測刑期: {max(0, predicted_days[0]):.2f} 天")