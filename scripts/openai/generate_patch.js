const { OpenAIApi, Configuration } = require("openai");
const fs = require("fs");

// 環境変数からAPIキーやパラメータを取得
const apiKey = process.env.OPENAI_API_KEY;
const issueContent = process.env.ISSUE_CONTENT || "";
const relatedCode = process.env.RELATED_CODE || "";
const commentContent = process.env.COMMENT_CONTENT || "";

// OpenAI APIの設定
const configuration = new Configuration({ apiKey });
const openai = new OpenAIApi(configuration);

// プロンプトを構築
let userPrompt = `以下はリポジトリの関連コード断片です:\n${relatedCode}\n\n`;
if (commentContent) {
  userPrompt += `以下はPRへのコメントです。これを踏まえ、修正を加えてください:\n${commentContent}\n\n`;
} else {
  userPrompt += `以下はIssueで要求されている修正内容です:\n${issueContent}\n\n`;
}

userPrompt += "上記を反映するためのdiffパッチを生成してください。出力は```diffで始まり```で終わるコードブロック内に収めてください。";

// OpenAI APIを呼び出し
(async () => {
  try {
    const response = await openai.createChatCompletion({
      model: "gpt-4",
      messages: [
        { role: "system", content: "You are a code assistant that can produce code patches in diff format." },
        { role: "user", content: userPrompt }
      ],
      temperature: 0,
    });

    // 応答内容を保存
    const content = response.data.choices[0].message.content;
    fs.writeFileSync("patch.txt", content);
    console.log("Patch generated.");
  } catch (error) {
    console.error("Error generating patch:", error);
    process.exit(1);
  }
})();
