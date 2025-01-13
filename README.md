>两年前就做过关于capcut的评论抓取，https://github.com/wanghaisheng/scrape-app-reviews-without-coding


好几年前有个大神说多关注榜单，拖拖拖一直到今天，花了一天的时间把这个ios app每日top100弄好了，因为是用github action，睡觉时间就给你整理了，没啥工作量，每天醒来批阅奏折就行了，还让gpt写了一个历史数据挖掘insight的脚本，但还没有测试和改进，就放在那里，过几天有了数据再看，我本身是医疗行业出身，现在一直想做的也是游戏+医疗这个方向，所以优先选了health这个品类


# how to build ios app review dataset in 5 minutes without coding 

## hunt all apps

### use waybackmachines as a source for historical 

### use google search for continous app 

### use sitemaps for continous app 


### continous search daily apps in google
if app is a new or newly update ,it will show in the google last 24hour serp list 

###

## hunt reviews

for historical reviews, if app has over 100000 reviews, we may not collect them all, but without limit set, we will try to collect as much as we can, it takes 2s sleep to collect 20 review, for one app, take 10-20 minutes for historical collection.

for continious collection we set limit to 2000, it takes 5 minutes.we can set frequecny to daily hourly weekly.



### from keyword to apps

use keyword to search app ids and scrape all app reviews
#### search in app store direct
it typically give a list of 10 apps

#### search in google 

take 'sprunki' as example, there is 800+ apps in google serp

#### search in apps.apple.com/sitemap.xml

for this way, there is over 1m records in sitemap but we can only match keyword in urls. have not tested yet.


### from developer to apps

typically we found a top app ,then click developer, try to find out whether this develop always create a popular app

use developer profile link to detect app ids and scrape all app reviews


### from category to top 100 apps

ios app store contain apps for iphone ,ipad, both have differ category list.
we can track top 100 rank app within each category

run this daily to track top 100 ios app under health category
>get-top100-app-daily.py






## insight and anaylsis 



### top 100 ranks insight


### one app review insight
Categorization: Leverages GPT-4 to categorize reviews into various feedback types (e.g., feature requests, UI issues).--> not included in the live demo

### one developer apps review insight


### one keyword apps review insight

### one category apps review insight



# reference

https://github.com/facundoolano/app-store-scraper?tab=readme-ov-file#readme


https://github.com/futurice/app-store-web-scraper  max 500 per id

https://github.com/glennfang/apple-app-reviews-scraper 


https://github.com/Kiddie-1410/tiktok_review_playstore/blob/main/en_review.ipynb

https://github.com/Junnie13/wildrift-vs-mobilelegends


