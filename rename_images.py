import os

folder = r"C:\Users\29858\Desktop\dataset\Heathy"   # 改成你的路径
start = 805

files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
files.sort()

# 第一步：先改成临时名（避免冲突）
for i, f in enumerate(files):
    os.rename(
        os.path.join(folder, f),
        os.path.join(folder, f"temp_{i}.jpg")
    )

# 第二步：再改成目标编号
temp_files = [f for f in os.listdir(folder) if f.startswith("temp_")]
temp_files.sort()

for i, f in enumerate(temp_files):
    new_name = f"{start + i}.jpg"
    os.rename(
        os.path.join(folder, f),
        os.path.join(folder, new_name)
    )

print("重命名完成！")