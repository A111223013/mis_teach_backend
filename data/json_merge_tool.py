import json
import os

def merge_dict(base, update):
    """遞迴合併字典，update 內容會覆蓋 base"""
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            merge_dict(base[key], value)
        else:
            base[key] = value
    return base

def main():
    print("=== JSON 合併小工具 ===")
    first_file = input("results.json").strip()
    second_file = input("final_data.json").strip()

    if not os.path.exists(first_file):
        print(f"找不到檔案: {first_file}")
        return
    if not os.path.exists(second_file):
        print(f"找不到檔案: {second_file}")
        return

    # 讀取檔案
    with open(first_file, "r", encoding="utf-8") as f:
        first_data = json.load(f)
    with open(second_file, "r", encoding="utf-8") as f:
        second_data = json.load(f)

    # 合併
    merged_data = merge_dict(first_data, second_data)

    # 輸出
    output_file = "thefinal.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 合併完成，已輸出: {output_file}")

if __name__ == "__main__":
    main()
