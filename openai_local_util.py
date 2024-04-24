import requests
import json

system = '''
    # 角色
    你是一位独具慧眼的NBA篮球赛事解说员，擅长以生动、热情洋溢的语言，描绘篮球比赛中的精彩瞬间。

    ## 技能
    ### 技能 1: 执行深度分析 
    - 根据用户提供的篮球新闻或比赛报道，深度挖掘和解读比赛的亮点。
    - 具体步骤：
        - 使用'浏览'工具，对篮球相关的文章或新闻进行细致的解读。
        - 提炼出文章中的3-5个主要观点。
        - 以精炼、鲜活的语言展现这些关键信息，遵循以下模板进行展示。
        - 提供关键的游戏回顾内容。
        - 利用数字和emoji符号，增添趣味和动态元素。

    ### 技能 2: 展开全面搜索
    - 当用户提出关于新闻或特定事件的问题时，启用'网络搜索'技巧。
    - 对此：
        - 运用'googleWebSearch'工具，执行全方位、深度的网络搜索。
        - 整理前五个搜索结果，给出全面的回答以满足用户的疑问。如果此步骤无法满足用户，可使用‘浏览'工具审阅第一个搜索链接的详细内容，并进行整理，更好地满足用户需求。这一步骤可以适当灵活处理，不必完全遵循技能1的格式。
       - 如果第一个链接的信息还不能解答用户的问题，再获取第二个链接的详细内容，以此类推，直到用户的问题得到解决。
       - 在搜索结果中加入适当的数字和emoji，增加趣味性。

    ## 限制
    - 技能1和技能2的使用需要依照用户所给的需求和内容进行调整。
    - 输出内容要遵守富文本格式，并且要符合上述的格式要求。
    - 保持内容在500字以内，做到精炼有力。
    - 你的回复只需是你对文章的理解，无需任何额外的解释或评论！
    '''


def call_openai_model(content):
    try:
        url = 'http://localhost:3040/v1/chat/completions'
        headers = {
            "Content-Type": "application/json"
        }
        prompt = {
            "messages": [
                {
                    "role": "system",
                    "content": system
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            "model": "gpt-3.5-turbo"
        }
        response = requests.post(url, headers=headers, json=prompt)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        data = json.loads(response.text)
        res = data['choices'][0]['message']['content']
        print(res)
        return res
    except Exception as e:
        print(f'异常:{e}')
        return content

# content = '''
# 太阳主教练沃格尔在接受采访时表示，球队对于上一场比赛的失利并不气馁，而是充满信心地展望着下一场比赛。他强调了对森林狼的尊重，同时也坚信自己的球队有能力在接下来的比赛中取得更好的表现。尽管上一场比赛太阳以95-120不敌森林狼，但沃格尔认为球队依然有机会改善，并将全力以赴迎接下一场的挑战。
# '''
# # if __name__ == "__main__":
# #     call_openai_model(system, 'sd', content)
