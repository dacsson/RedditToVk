import requests
import vk_api
import json
import urllib.request
import praw
import pandas as pd
import time
from bs4 import BeautifulSoup
from vk_api.upload import VkUpload
from urllib.request import (Request, urlopen, urlretrieve)
from deep_translator import GoogleTranslator

def download_image(url, file_path, file_name):
    full_path = "../" + file_path + file_name
    urllib.request.urlretrieve(url, full_path)

def write_json(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

def GetUploadServerImager(token, group_id):
    y = requests.get("https://api.vk.com/method/photos.getWallUploadServer", 
                     params={'access_token': token,'group_id': group_id, 
                             'v':"5.81"}).json()   
    print(y)
    return y['response']['upload_url'] 

def UploadPostImage(quote, img, token, group_id, owner_id_group, vk, subreddit):

    upload_url = GetUploadServerImager(token, group_id)             
    
    file_name = "photo.jpg"                                         

    download_image(img, 'res/', file_name)

    file = {'photo': open('../res/photo.jpg', 'rb')}          

    ur = requests.post(upload_url, files=file).json()   

    write_json(ur, 'upload_photos.json')                

    photo_saved = requests.get('https://api.vk.com/method/photos.saveWallPhoto', params={'access_token': token,
                                                                                     'group_id': group_id,
                                                                                     'photo': ur['photo'],
                                                                                     'server': ur['server'],
                                                                                     'hash': ur['hash'],
                                                                                     'v':"5.81"}).json() 

    write_json(photo_saved, 'upload_photos_result.json')

    attachments = 'photo' + str(photo_saved["response"][0]['owner_id']) + '_' + str(photo_saved["response"][0]['id'])

    quote = GoogleTranslator(source='auto', target='ru').translate(quote) + "\n//\n" + quote + "\n\n#" + str(subreddit)

    vk.wall.post(
        owner_id = owner_id_group,
        from_group = 1,
        message = quote,
        attachment = attachments
    )

def GetUploadServerVideo(title, token, group_id):
    title = GoogleTranslator(source='auto', target='ru').translate(title)
    y = requests.get("https://api.vk.com/method/video.save", 
                     params={'access_token': token,'group_id': group_id, 'name' : title,
                             'v':"5.81"}).json()   
    print(y)
    return y['response']['upload_url'] 

def UploadPostWithVideo(quote, token, group_id, owner_id_group, vk, subreddit):
    
    upload_url = GetUploadServerVideo(quote, token, group_id)     

    file = {'video_file': open('../res/video.mp4', 'rb')}          

    ur = requests.post(upload_url, files=file).json()   

    write_json(ur, 'upload_video.json')

    attachment = 'video' + str(ur['owner_id']) + '_' + str(ur['video_id'])

    quote = GoogleTranslator(source='auto', target='ru').translate(quote) + "\n//\n" + quote + "\n\n#" + str(subreddit)

    vk.wall.post(
        owner_id = owner_id_group,
        from_group = 1,
        message = quote,
        attachment = attachment
    )

# - Разобраться с потом (main отличие это пост с картинкой или с видео тогда отличаются фукнции постинга в группу)
def HandlePost(reddit_read_only, subreddit, hot_posts, n, token, group_id, owner_id_group, vk):
    post = hot_posts[n]
    link = post.permalink
    quote = post.title 

    print('\nPost link: ', link, '\n')

    # - Медиа у поста будет в случае если прикреплено видео
    if(post.media):
        url = post.media['reddit_video']['fallback_url']
        url = url.split("?")[0]
        name = "../res/video.mp4"
        time.sleep(5)
        urllib.request.urlretrieve(url, name)
        time.sleep(5)

        UploadPostWithVideo(quote, token, group_id, owner_id_group, vk, subreddit)
    
    # - Пост с картинкой
    else:
        post_full_url = 'https://www.reddit.com' + link[:-1] + '.json'                      
        req = Request(post_full_url)
        try:
            imgs_json = json.loads(urlopen(req).read())
        except:
            time.sleep(15)
            imgs_json = json.loads(urlopen(req).read())
        try:
            img_url = imgs_json[0]['data']['children'][0]['data']['url_overridden_by_dest']
            print(img_url)

            UploadPostImage(quote, img_url, token, group_id, owner_id_group, vk, subreddit)

        # - Если в посте нет ни картинки ни видео то переходим к следующему посту из массива
        except:
            n+=1
            HandlePost(reddit_read_only, subreddit, hot_posts, n, token, group_id, owner_id_group, vk)

# - Мейн функшион
def main():

    # - PRAW
    reddit_read_only = praw.Reddit( client_id="UhsZdMdh0U4-qkxLwhwX9g",                     # your client id
                                    client_secret="FSkyKaVS3FQu9LfieF7pDW974hwT4Q",         # your client secret
                                    user_agent="RandomToVK")                                # your user agent

    with open('E:/RedditLogInfo.json', 'r') as reddits_json:
        subreddits = json.load(reddits_json)

    for i in range(5):
        
        # - Вытаскиваем из жисона информацию для vk и какой сабреддит будем скрапить
        # - Получил токен тут: https://oauth.vk.com/authorize?client_id=<app_id>&redirect_uri=https://oauth.vk.com/blank.html&display=page&scope=wall,photos,video,offline&response_type=token&v=5.130
        #   надо создать приложение (для каждого паблика своё), в котором указать сообщество и вставить в ссылку его айди 

        subreddit = reddit_read_only.subreddit(subreddits[str(i)]['sub_name'])
        token = subreddits[str(i)]['token']
        application_id = int(subreddits[str(i)]['application_id'])
        group_id = int(subreddits[str(i)]['group_id'])
        owner_id_group = int(subreddits[str(i)]['owner_id_group'])

        vk_session = vk_api.VkApi(token=token)                                      # - Авторизируемся в вк
        vk = vk_session.get_api()                                                   # - Чтобы легче обращаться к функциям апи
        upload = VkUpload(vk_session)                                               # - Чтобы леге использовать аплоад функ

        hot_posts = []

        # - Собираем несколько горячих постов с реддита (чтобы если пост без контента можно было запостить следующий с картинокой/видео)
        for post in subreddit.hot(limit=5):
            hot_posts.append(post)
        
        HandlePost(reddit_read_only, subreddit, hot_posts, 0, token, group_id, owner_id_group, vk)

if __name__=="__main__":
    main()