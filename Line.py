from fastapi import FastAPI, Request
import cohere
from linebot import WebhookParser, LineBotApi
from linebot.models import TextSendMessage

import re
bill_state: dict[str, dict] = {}

from dotenv import load_dotenv  # python-dotenv をインストールしておく
import os

load_dotenv()  # .env を読み込んで環境変数に設定  [oai_citation:8‡PyPI](https://pypi.org/project/python-dotenv/?utm_source=chatgpt.com)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY)
OPENAI_CHARACTER_PROFILE = '''
これから会話を行います。以下の条件を絶対に守って回答してください。
あなたは週末の自炊のアシスタントです。僕たちの週末の料理をサポートしてください。
あなたは料理名から、人数に対するメニューを言われます。その時に
レシピと、人数分の材料を答えること。
'''

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
line_parser = WebhookParser(LINE_CHANNEL_SECRET)

def handle_other_tasks(user_id: str, message: str) -> str:
    state = bill_state.setdefault(user_id, {})

    # 参加人数の設定
    if '参加' in message and '人' in message:
        m = re.search(r'(\d+)人', message)
        if m:
            state['count'] = int(m.group(1))
            return f"{state['count']}人参加ですね。了解です！"
        else:
            return "参加人数が認識できませんでした。数字で教えてください。"

    # 支払い情報の処理
    if re.search(r'(\d+)人.*?(\d+)円.*?払いました', message):
        m = re.search(r'(\d+)人.*?(\d+)円.*?払いました', message)
        if m:
            count = int(m.group(1))
            total = int(m.group(2))
            name_match = re.search(r'購入者は(.*?)です', message)
            purchaser = name_match.group(1).strip() if name_match else "誰か"
            share = total // count
            # 状態をクリア
            del bill_state[user_id]
            return (
                f"今回{count}人で割り勘し、一人当たり{share}円です。\n"
                f"{purchaser}さんが購入者なので、他の人は{purchaser}さんに{share}円ずつ支払ってください。"
            )
        else:
            return (
                "支払い情報のフォーマットが正しくありません。"
                "例:合計の料金は3000円で、石原さんが払いました。"
            )

    # 自然文から人数と料理名を抽出し、Cohereでレシピを生成
    if 'レシピ' in message and re.search(r'(\d+)人.*?(?:で|が).*?(.+?)を作りたい', message):
        match = re.search(r'(\d+)人.*?(?:で|が).*?(.+?)を作りたい', message)
        if match:
            people = int(match.group(1))
            dish = match.group(2).strip()

            prompt = f"""
{people}人分の{dish}を作りたいです。
レシピと材料の分量を教えてください。
出力形式は以下の通りにしてください：

【材料】
- 食材名: 数量（単位）

【作り方】
- 手順1
- 手順2
"""

            response = co.generate(
                model='command-r-plus',
                prompt=prompt,
                max_tokens=500,
                temperature=0.7,
            )
            return response.generations[0].text.strip()

    return "申し訳ありません、そのご要望には対応していません。"


app = FastAPI()

@app.post('/')
async def ai_talk(request: Request):
    signature = request.headers.get('X-Line-Signature', '')
    events = line_parser.parse((await request.body()).decode('utf-8'), signature)
    
    for event in events:
        if event.type != 'message' or event.message.type != 'text':
            continue
        
        line_user_id = event.source.user_id
        line_message = event.message.text

        ai_message = handle_other_tasks(line_user_id, line_message)

        line_bot_api.push_message(line_user_id, TextSendMessage(ai_message))
    
    return 'ok'
