import json

# 创建数据
frames = 2854
data = {
    "total_frames": frames,
    "score": []
}

# 生成从0到2854帧的得分，得分等于帧号（便于分辨）
for frame in range(frames):  # 0到2854共2855个帧

    score_value = float(frame)  # 得分等于帧号，便于分辨
    
    data["score"].append({str(frame): score_value})

# 保存到文件
with open('frame_scores_clear.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# print("JSON文件已生成: frame_scores_clear.json")
# print(f"总帧数: {data['total_frames']}")
# print(f"生成的得分数量: {len(data['score'])}")

# # 显示前几行和最后几行作为验证
# print("\n前5帧的得分：")
# for i in range(5):
#     print(f"  帧 {i}: {data['score'][i]}")

# print("\n最后5帧的得分：")
# for i in range(-5, 0):
#     print(f"  帧 {list(data['score'][i].keys())[0]}: {data['score'][i]}")