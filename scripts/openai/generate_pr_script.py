import os
import requests
import subprocess
from openai import OpenAI

# 環境変数から必要な値を取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPOSITORY = os.getenv("REPOSITORY")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER")
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")

# APIエンドポイント
ISSUE_API_URL = f"https://api.github.com/repos/{REPOSITORY}/issues/{ISSUE_NUMBER}"
PULLS_API_URL = f"https://api.github.com/repos/{REPOSITORY}/pulls"

# Issueの本文を取得
def get_issue_body():
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(ISSUE_API_URL, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue details: {response.status_code}")
    issue_data = response.json()
    return issue_data.get("body", ""), issue_data.get("number")

# OpenAI APIでdiffパッチを生成
def generate_patch(issue_content):
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = (
        f"以下のIssueを解決するために必要なコード修正をdiff形式で生成してください。\n\n"
        f"Issue内容:\n{issue_content}\n\n"
        "出力は以下の形式にしてください:\n"
        "```diff\n"
        "diff形式の修正内容\n"
        "```\n"
    )
    response = openai_client.completions.create(
        model="gpt-3.5-turbo",  # 無料プランで利用可能なモデル
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].text.strip()

# diffパッチを適用
def apply_patch(diff_text):
    # diff部分だけを抽出
    if "```diff" in diff_text:
        diff_text = diff_text.split("```diff")[1].split("```")[0].strip()

    # パッチファイルを作成
    with open("patch.diff", "w") as patch_file:
        patch_file.write(diff_text)

    # git applyでパッチ適用
    result = subprocess.run(["git", "apply", "patch.diff"], check=False)
    if result.returncode != 0:
        raise Exception("Failed to apply the patch. Check the diff format or repository status.")

# 新しいブランチを作成し変更をプッシュ
def create_branch_and_push(issue_number):
    branch_name = f"issue-{issue_number}"
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Fix from Issue #{issue_number}"], check=True)
    subprocess.run(["git", "push", "origin", branch_name], check=True)
    return branch_name

# PRを作成
def create_pull_request(branch_name, issue_number):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": f"Auto Fix from Issue #{issue_number}",
        "head": branch_name,
        "base": BASE_BRANCH,
        "body": f"This PR resolves issue #{issue_number}."
    }
    response = requests.post(PULLS_API_URL, headers=headers, json=data)
    if response.status_code == 201:
        print("Pull request created successfully.")
    else:
        print(f"Failed to create pull request: {response.status_code}, {response.text}")

# メイン関数
def main():
    try:
        # 1. Issue本文を取得
        issue_content, issue_number = get_issue_body()

        if not issue_content:
            print("No issue content found. Exiting...")
            return

        # 2. OpenAI APIでdiffを生成
        diff_text = generate_patch(issue_content)

        if not diff_text or "diff" not in diff_text:
            print("No valid diff found in the response.")
            return

        # 3. パッチを適用
        apply_patch(diff_text)

        # 4. 新しいブランチを作成してプッシュ
        branch_name = create_branch_and_push(issue_number)

        # 5. プルリクエストを作成
        create_pull_request(branch_name, issue_number)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
