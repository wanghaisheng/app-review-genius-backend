>两年前就做过关于capcut的评论抓取，https://github.com/wanghaisheng/scrape-app-reviews-without-coding


好几年前有个大神说多关注榜单，拖拖拖一直到今天，花了一天的时间把这个ios app每日top100弄好了，因为是用github action，睡觉时间就给你整理了，没啥工作量，每天醒来批阅奏折就行了，还让gpt写了一个历史数据挖掘insight的脚本，但还没有测试和改进，就放在那里，过几天有了数据再看，我本身是医疗行业出身，现在一直想做的也是游戏+医疗这个方向，所以优先选了health这个品类


# how to build  app review dataset in 5 minutes without coding 


## from keyword to apps

use keyword to search app ids and scrape all app reviews

## from developer to apps

use developer profile link to detect app ids and scrape all app reviews


## from category to top 100 apps


run this daily to track top 100 ios app under health category
>get-top100-app-daily.py


https://github.com/glennfang/apple-app-reviews-scraper




# anaylsis 

Categorization: Leverages GPT-4 to categorize reviews into various feedback types (e.g., feature requests, UI issues).--> not included in the live demo



https://github.com/Kiddie-1410/tiktok_review_playstore/blob/main/en_review.ipynb
