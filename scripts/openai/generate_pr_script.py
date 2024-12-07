import os
import requests
import json
import subprocess

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPOSITORY = os.getenv("REPOSITORY")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER")
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")

# Issue API URL
ISSUE_API_URL = f'https://api.github.com/repos/{REPOSITORY}/issues/{ISSUE_NUMBER}'
# PR作成用URL
PULLS_API_URL = f'https://api.github.com/repos/{REPOSITORY}/pulls'

# 1. Issueの内容を取得
def get_issue_body():
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.get(ISSUE_API_URL, headers=headers)
    issue_data = response.json()
    return issue_data.get('body', ''), issue_data.get('number')

# 2. OpenAI APIでコード修正案(diff)を生成
def get_patch_from_openai(issue_content):
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = (
        f"以下はIssueの要求内容です:\n{issue_content}\n\n"
        "このIssueを解決するためのコード修正パッチをdiff形式で生成してください。\n"
        "```diff\n"
        "# 以下に修正のdiffを記載\n"
        "```"
    )

    # OpenAI Chat Completion呼び出し（モデル名は適宜変更）
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4-1106-preview",
        temperature=0,
    )

    content = chat_completion.choices[0].message.content
    return content

# 3. patch.txtに書き込み＆適用
def apply_patch(diff_text):
    # diff_textから```diff ...``````を抽出する処理が必要な場合あり
    # ここでは単純化しているため適宜正規表現などで抽出することを想定
    with open("patch.txt", "w") as f:
        f.write(diff_text)

    # patchを適用
    # diffブロックだけを抽出するなどの処理が必要な場合あり
    subprocess.run(["git", "apply", "patch.txt"], check=True)

# 4. 新規ブランチを作ってコミット＆プッシュ
def create_branch_and_push(issue_number):
    branch_name = f"issue-{issue_number}"
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    subprocess.run(["git", "add", "."], check=True)
    commit_msg = f"Fix from Issue #{issue_number}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    subprocess.run(["git", "push", "origin", branch_name], check=True)
    return branch_name

# 5. PRを作成
def create_pull_request(branch_name, issue_number):
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {
        'title': f"Auto Fix from Issue #{issue_number}",
        'head': branch_name,
        'base': BASE_BRANCH,
        'body': f"This PR fixes the issue #{issue_number} automatically."
    }
    response = requests.post(PULLS_API_URL, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print("Pull Request created successfully!")
    else:
        print("Failed to create Pull Request:", response.text)


def main():
    issue_content, issue_number = get_issue_body()
    if not issue_content:
        print("No issue content found, exiting...")
        return

    diff_text = get_patch_from_openai(issue_content)
    if "diff" not in diff_text:
        print("No diff found in the response. Please check the prompt or OpenAI output.")
        return

    apply_patch(diff_text)
    branch_name = create_branch_and_push(issue_number)
    create_pull_request(branch_name, issue_number)

if __name__ == "__main__":
    main()
