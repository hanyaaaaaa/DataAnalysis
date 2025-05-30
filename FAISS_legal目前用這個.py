import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
# 連家妮犯三人以上共同詐欺取財罪，共二罪，測試用
# 讀取數據
try:
    df = pd.read_csv('C:/Users/李/Desktop/數據分析/outputarea/Tovector.csv')
except Exception as e:
    print(f"❌ 無法讀取數據文件: {e}")
    exit()

# 過濾無刑期數據並檢查數據完整性
df_with_sentence = df[df['刑期(天)'] > 0].copy()
df_with_sentence = df_with_sentence.dropna(subset=['刑期(天)'])  # 移除刑期為 NaN 的行
print(f"過濾後數據量: {len(df_with_sentence)} 行")

# 載入原始嵌入模型
try:
    model = SentenceTransformer('DMetaSoul/sbert-chinese-general-v2')
    print("✅ 已載入通用模型：DMetaSoul/sbert-chinese-general-v2")
except Exception as e:
    print(f"❌ 無法載入模型: {e}")
    exit()

# 處理文本向量
try:
    text_embeddings = model.encode(df_with_sentence["原始內容"].tolist()).astype('float32')
except Exception as e:
    print(f"❌ 文本向量化失敗: {e}")
    exit()

# 將數據集分割為訓練集和測試集
train_df, test_df = train_test_split(df_with_sentence, test_size=0.2, random_state=42)
train_embeddings = model.encode(train_df["原始內容"].tolist()).astype('float32')
test_embeddings = model.encode(test_df["原始內容"].tolist()).astype('float32')

# 設置 K-Means 參數
ncentroids = max(2, len(train_df) // 20)  
niter = 50       # 迭代次數
verbose = True   # 顯示訓練過程
print(f"聚類數量 (ncentroids): {ncentroids}")

# 獲取嵌入維度
d = train_embeddings.shape[1]
print(f"維度數量{d}")

# 創建量化器 (quantizer)
quantizer = faiss.IndexFlatL2(d) # 使用 歐式距離 度量

# 創建使用 K-Means 聚類的 IndexIVFFlat 索引
index = faiss.IndexIVFFlat(quantizer, d, ncentroids, faiss.METRIC_L2)

# 訓練 K-Means 模型生成聚類質心
assert not index.is_trained
index.train(train_embeddings)
assert index.is_trained

# 將訓練數據添加到索引
index.add(train_embeddings)

# 保存索引
faiss.write_index(index, "court_index_ivf_optimized.faiss")

# 刑期預測系統
def legal_consult_system(index, train_df, model):
    print("\n== 智能刑期評估系統（使用 K-Means 聚類與優化參數）==")
    while True:
        text = input("\n描述案情（輸入exit退出）: ")
        if text.lower() == 'exit':
            break
        
        try:
            text_vec = model.encode([text]).astype('float32')
            index.nprobe = 75  # 最近鄰的k個質心
            k = 7  # 調整 k 到 7
            distances, indices = index.search(text_vec, k=k)
            
            print("\n★ 相似判例分析:")
            weights = np.exp(-distances[0])  # 使用指數衰減權重
            # 檢查權重是否有效
            if not np.isfinite(weights).all() or weights.sum() == 0:
                print("⚠️ 權重計算異常，使用均勻權重")
                weights = np.ones_like(distances[0]) / len(distances[0])
            else:
                weights /= weights.sum()  # 歸一化權重
            
            for i, idx in enumerate(indices[0]):
                case = train_df.iloc[idx]
                similarity = 1 / (1 + distances[0][i])
                print(f"\n・{case['原始內容'][:50]}...")
                print(f"  實際刑期：{case['刑期(天)']}天 | 相似度：{similarity:.2%}")
            
            similar_sentences = train_df.iloc[indices[0]]['刑期(天)']
            # 檢查刑期數據是否有效
            if not np.isfinite(similar_sentences).all():
                print("⚠️ 相似案例刑期數據中包含無效值，無法計算預估刑期")
                weighted_average_sentence = np.nan
            else:
                weighted_average_sentence = np.average(similar_sentences, weights=weights)
            
            if np.isnan(weighted_average_sentence):
                print("\n基於相似判例，加權預估刑期為: 無法計算（數據異常）")
            else:
                print(f"\n基於相似判例，加權預估刑期為: {weighted_average_sentence:.2f} 天")
        except Exception as e:
            print(f"❌ 輸入錯誤: {e}，請重新輸入")

# 計算多種評估指標
def calculate_metrics(index, test_df, train_df, model):
    predictions = []
    actuals = []
    for idx, row in test_df.iterrows():
        text_vec = model.encode([row["原始內容"]]).astype('float32')
        distances, indices = index.search(text_vec, k=7)  # k=7
        weights = np.exp(-distances[0])  # 使用指數衰減權重
        if not np.isfinite(weights).all() or weights.sum() == 0:
            weights = np.ones_like(distances[0]) / len(distances[0])
        else:
            weights /= weights.sum()
        
        similar_sentences = train_df.iloc[indices[0]]['刑期(天)']
        if not np.isfinite(similar_sentences).all():
            predicted_sentence = np.nan
        else:
            predicted_sentence = np.average(similar_sentences, weights=weights)
        
        predictions.append(predicted_sentence)
        actuals.append(row['刑期(天)'])
    
    # 移除預測值中的 nan
    valid_indices = [i for i, pred in enumerate(predictions) if not np.isnan(pred)]
    predictions = [predictions[i] for i in valid_indices]
    actuals = [actuals[i] for i in valid_indices]
    
    if len(predictions) == 0:
        print("⚠️ 所有預測值均為無效，無法計算評估指標")
        return
    
    mse = mean_squared_error(actuals, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(actuals, predictions)
    r2 = r2_score(actuals, predictions)
    
    print(f"\n=== 模型評估指標（優化後）===")
    print(f"MSE（均方誤差）: {mse:.2f} 天²")
    print(f"RMSE（均方根誤差）: {rmse:.2f} 天")
    print(f"MAE（平均絕對誤差）: {mae:.2f} 天")
    print(f"R² 分數（決定係數）: {r2:.4f}")
    if r2 < 0:
        print("⚠️ R² 為負數，模型預測效果比簡單均值預測還差！")
    else:
        print(f"🎉 R² 為正數，模型已能捕捉 {r2*100:.1f}% 的刑期變異性！")

# 載入索引
try:
    index = faiss.read_index("court_index_ivf_optimized.faiss")
except Exception as e:
    print(f"❌ 請先創建索引，錯誤: {e}")
    exit()

# 啟動系統
legal_consult_system(index, train_df, model)

# 計算並顯示評估指標
calculate_metrics(index, test_df, train_df, model)