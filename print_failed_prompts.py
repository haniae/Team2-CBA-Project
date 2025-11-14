import json

def main():
    with open("ml_patterns_test_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    failed = [r for r in data.get("results", []) if not r.get("passed")]
    print(f"Failed Prompts: {len(failed)}")
    for r in failed:
        prompt = r.get("prompt", "N/A")
        print(f"- {prompt}")
        quality = r.get("quality", {})
        issues = quality.get("issues")
        if issues:
            print("  Issues:", ", ".join(issues))
        elif quality.get("error"):
            print("  Error:", quality.get("error"))
        else:
            print("  Issues: Unknown")

if __name__ == "__main__":
    main()

