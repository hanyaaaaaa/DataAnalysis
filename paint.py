import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv('C:/Users/李/Desktop/數據分析/outputarea/Tovector.csv')

df = df[df['刑期(天)'] != '未知']
df['刑期(天)'] = pd.to_numeric(df['刑期(天)'], errors='coerce')
df = df[df['刑期(天)'] > 0]
df = df.dropna(subset=['刑期(天)'])

median = np.median(df['刑期(天)'])
mean = np.mean(df['刑期(天)'])

print(f"刑期的中位數: {median} 天")
print(f"刑期的平均數: {mean:.2f} 天")

plt.figure(figsize=(10, 6))
plt.boxplot(df['刑期(天)'], vert=False)
plt.title("Sentence(day) line box diagram", fontsize=20)
plt.xlabel("day", fontsize=14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.show()