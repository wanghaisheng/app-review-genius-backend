>两年前就做过关于capcut的评论抓取，https://github.com/wanghaisheng/scrape-app-reviews-without-coding


好几年前有个大神说多关注榜单，拖拖拖一直到今天，花了一天的时间把这个ios app每日top100弄好了，因为是用github action，睡觉时间就给你整理了，没啥工作量，每天醒来批阅奏折就行了，还让gpt写了一个历史数据挖掘insight的脚本，但还没有测试和改进，就放在那里，过几天有了数据再看，我本身是医疗行业出身，现在一直想做的也是游戏+医疗这个方向，所以优先选了health这个品类


# how to build ios app review dataset in 5 minutes without coding 

## hunt all apps

### use waybackmachines as a source for historical 

### use google search for continous app 

### use sitemaps for continous app 

### app basic info
#### from app page info

#### from itune api

* releasedate
* developerid
* genres
* screenshot

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

## related app 

from keyword to extend keyword for inspirations


feed all keywords to full ids list

per id ,app basic info

per id, also bought ids




### top 100 ranks insight


### one app review insight
Categorization: Leverages GPT-4 to categorize reviews into various feedback types (e.g., feature requests, UI issues).--> not included in the live demo

### one developer apps review insight


### one keyword apps review insight

### one category apps review insight



# reference


https://github.com/facundoolano/app-store-scraper?tab=readme-ov-file#readme  
https://github.com/jbigman/app-store-scraper
* max 500 review per id

*  from appid to more basicinfo:

```
{ id: 553834731,
  appId: 'com.midasplayer.apps.candycrushsaga',
  title: 'Candy Crush Saga',
  url: 'https://itunes.apple.com/us/app/candy-crush-saga/id553834731?mt=8&uo=4',
  description: 'Candy Crush Saga, from the makers of Candy Crush ...',
  icon: 'http://is5.mzstatic.com/image/thumb/Purple30/v4/7a/e4/a9/7ae4a9a9-ff68-cbe4-eed6-fe0a246e625d/source/512x512bb.jpg',
  genres: [ 'Games', 'Entertainment', 'Puzzle', 'Arcade' ],
  genreIds: [ '6014', '6016', '7012', '7003' ],
  primaryGenre: 'Games',
  primaryGenreId: 6014,
  contentRating: '4+',
  languages: [ 'EN', 'JA' ],
  size: '73974859',
  requiredOsVersion: '5.1.1',
  released: '2012-11-14T14:41:32Z',
  updated: '2016-05-31T06:39:52Z',
  releaseNotes: 'We are back with a tasty Candy Crush Saga update ...',
  version: '1.76.1',
  price: 0,
  currency: 'USD',
  free: true,
  developerId: 526656015,
  developer: 'King',
  developerUrl: 'https://itunes.apple.com/us/developer/king/id526656015?uo=4',
  developerWebsite: undefined,
  score: 4,
  reviews: 818816,
  currentVersionScore: 4.5,
  currentVersionReviews: 1323,
  screenshots:
   [ 'http://a3.mzstatic.com/us/r30/Purple49/v4/7a/8a/a0/7a8aa0ec-976d-801f-0bd9-7b753fdaf93c/screen1136x1136.jpeg',
     ... ],
  ipadScreenshots:
   [ 'http://a1.mzstatic.com/us/r30/Purple49/v4/db/45/cf/db45cff9-bdb6-0832-157f-ac3f14565aef/screen480x480.jpeg',
     ... ],
  appletvScreenshots: [],
  supportedDevices:
   [ 'iPhone-3GS',
     'iPadWifi',
     ... ]}
```

* suggest-> extend keyword

Given a string returns up to 50 suggestions to complete a search query term. A priority index is also returned which goes from 0 for terms with low traffic to 10000 for the most searched terms.

* similar-> also bought apps
* 




https://github.com/futurice/app-store-web-scraper  max 500 per id

https://github.com/glennfang/apple-app-reviews-scraper 


https://github.com/Kiddie-1410/tiktok_review_playstore/blob/main/en_review.ipynb

https://github.com/Junnie13/wildrift-vs-mobilelegends


