import urllib
from requests_oauthlib import OAuth1Session, OAuth1
import requests
import os, sys
import datetime

def main(arg):

    # APIの秘密鍵
    CK = os.environ['TW_CONSUMER_KEY'] # コンシューマーキー
    CKS = os.environ['TW_CONSUMER_SECRET'] # コンシューマーシークレット
    AT = os.environ['TW_ACCESS_TOKEN_KEY'] # アクセストークン
    ATS = os.environ['TW_ACCESS_TOKEN_SECRET'] # アクセストークンシークレット
 
    # ツイートID
    tweet_id = arg
    # tweet_id = '1456870396553170945' # str型で指定
 
    # 検索時のパラメーター
    count = 100 # 一回あたりの検索数(最大100/デフォルトは15)
    range = 180 # 検索回数の上限値(最大180/15分でリセット)
    lmitdays = 3 # 元ツイートから3日後までのツイートを検索する

    #出力用配列
    sp_tweets = []

    #階層レベル
    level = 0

    #初回１回目

    # 文字列設定
    param = 'max_id:'+tweet_id
    param = urllib.parse.quote_plus(param)

    # リクエスト
    url = "https://api.twitter.com/1.1/search/tweets.json?lang=ja&q="+param+"&count=1&tweet_mode=extended"
    auth = OAuth1(CK, CKS, AT, ATS)
    response = requests.get(url, auth=auth)
    try:
        data = response.json()['statuses']
    except KeyError: # リクエスト回数が上限に達した場合のデータのエラー処理
        print('リクエスト回数が上限に達しました')
        sys.exit(11)
    
    if len(data) == 0:  #元データがない
        sys.exit(1)

    sp_tweets.append('\n')  # 空行
    sp_tweets.append('■■■■■'+tweet_id+'■■■■■'+data[0]['id_str']+'■■■■■'+str(level)+'\n')  # デリミタ
    sp_tweets.append('\n')  # 空行
    sp_tweets.append(data[0]['user']['name']+'@'+data[0]['user']['screen_name']+'\n')  # 表示名
    created_at = datetime.datetime.strptime(data[0]['created_at'], '%a %b %d %H:%M:%S %z %Y')
    created_at_jst = created_at + datetime.timedelta(hours=9) # JST
    created_at_str = created_at_jst.strftime('%Y-%m-%d %H:%M:%S')
    sp_tweets.append(created_at_str+'\n')  # ツイート日時
    sp_tweets.append('\n')  # 空行
    sp_tweets.append(data[0]['full_text']+'\n')  # ツイート内容

    date_max = created_at + datetime.timedelta(days=lmitdays) # 元ツイートから3日後までのツイートを検索する
    date_max_str = date_max.strftime('%Y-%m-%d')

    #リツイート元
    if data[0]['is_quote_status']:
        sp_tweets.append('\n')  # 空行
        sp_tweets.append('▲▲▲▲▲'+tweet_id+'▲▲▲▲▲'+data[0]['quoted_status']['id_str']+'▲▲▲▲▲'+str(level)+'\n')
        sp_tweets.append('\n')  # 空行
        sp_tweets.append(data[0]['quoted_status']['user']['name']+'@'+data[0]['quoted_status']['user']['screen_name']+'\n')
        created_at = datetime.datetime.strptime(data[0]['quoted_status']['created_at'], '%a %b %d %H:%M:%S %z %Y')
        created_at_jst = created_at + datetime.timedelta(hours=9) # JST
        created_at_str = created_at_jst.strftime('%Y-%m-%d %H:%M:%S')
        sp_tweets.append(created_at_str+'\n')
        sp_tweets.append('\n')
        sp_tweets.append(data[0]['quoted_status']['full_text']+'\n')

    user_id = '@'+data[0]['user']['screen_name']  #元ツイートのユーザー名

    # ツイート検索・リプライの抽出
    #tweets = sp_tweets
    search_specific_tweets(sp_tweets, level, auth, tweet_id, user_id, count, range, date_max_str)
    sp_tweets.append('\n')  # 空行
    
    # 抽出結果を表示
    # print(sp_tweets[0:100])
    for tweet in sp_tweets:
        print(tweet)

    #ファイル出力
    path = os.getcwd()
    dt_now = datetime.datetime.now()
    dt = dt_now.strftime('%Y%m%d%H%M%S')
    fn = path+'\TwitterAPISerchID_'+dt+'.txt'
    f = open(fn,'a', encoding='UTF-8')
    f.writelines(sp_tweets)
    f.close()
    print("filename : "+fn)

def search_specific_tweets(sp_tweets, level, auth, tweet_id, user_id, count, range, date_max_str):

    level += 1

    # 返信を得る

    cnt = 0
    reply_cnt = 0

    param = 'to:'+user_id+' since_id:'+tweet_id+' until:'+date_max_str #元ツイートのユーザー名に返信したもの
    param = urllib.parse.quote_plus(param)

    url = "https://api.twitter.com/1.1/search/tweets.json?lang=ja&q="+param+"&count="+str(count)+"&tweet_mode=extended"
    response = requests.get(url, auth=auth)
    try:
        data = response.json()['statuses']
    except KeyError: # リクエスト回数が上限に達した場合のデータのエラー処理
        print('リクエスト回数が上限に達しました')
        sys.exit(11)

    if len(data) != 0:
        cnt += 1
        if cnt > range:
            sys.exit(12)
        for tweet in data:
            if tweet['in_reply_to_status_id_str'] == tweet_id  and same_tweet_not_exist(sp_tweets, tweet['id_str']): # 返信先がツイートIDに一致するものを抽出
                user_id = '@'+tweet['user']['screen_name']
                sp_tweets.append('\n')  # 空行
                sp_tweets.append('▼▼▼▼▼'+tweet_id+'▼▼▼▼▼'+tweet['id_str']+'▼▼▼▼▼'+str(level)+'\n')  # デリミタ
                sp_tweets.append('\n')  # 空行
                sp_tweets.append(tweet['user']['name']+user_id+'\n')  # 表示名
                created_at = datetime.datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S %z %Y')
                created_at_jst = created_at + datetime.timedelta(hours=9) # JST
                created_at_str = created_at_jst.strftime('%Y-%m-%d %H:%M:%S')
                sp_tweets.append(created_at_str+'\n')  # ツイート日時
                sp_tweets.append('\n')  # 空行
                sp_tweets.append(tweet['full_text']+'\n')  # ツイート内容
                level_s = level
                search_specific_tweets(sp_tweets, level_s, auth, tweet['id_str'], user_id, count, range, date_max_str) #再帰呼び出し
                reply_cnt += 1
        
        print('ID : '+tweet_id+', リプライ数 : ', reply_cnt)
    
    # リツイートを得る

    cnt = 0
    retweet_cnt = 0

    param = 'url:'+tweet_id+' -filter:retweets'+' until:'+date_max_str  #元ツイートへのリツイートの検索条件
    param = urllib.parse.quote_plus(param)

    url = "https://api.twitter.com/1.1/search/tweets.json?lang=ja&q="+param+"&count="+str(count)+"&tweet_mode=extended"
    response = requests.get(url, auth=auth)
    try:
        data = response.json()['statuses']
    except KeyError: # リクエスト回数が上限に達した場合のデータのエラー処理
        print('リクエスト回数が上限に達しました')
        sys.exit(11)

    if len(data) != 0:
        cnt += 1
        if cnt > range:
            sys.exit(12)
        for tweet in data:
            # 引用リツイート先がツイートIDに一致するものを抽出
            if tweet['is_quote_status'] and  tweet['quoted_status']['id_str'] == tweet_id and same_tweet_not_exist(sp_tweets, tweet['id_str']): 
                user_id = '@'+tweet['user']['screen_name']
                sp_tweets.append('\n')  # 空行
                sp_tweets.append('▽▽▽▽▽'+tweet_id+'▽▽▽▽▽'+tweet['id_str']+'▽▽▽▽▽'+str(level)+'\n')  # デリミタ
                sp_tweets.append('\n')  # 空行
                sp_tweets.append(tweet['user']['name']+user_id+'\n')  # 表示名
                created_at = datetime.datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S %z %Y')
                created_at_jst = created_at + datetime.timedelta(hours=9) # JST
                created_at_str = created_at_jst.strftime('%Y-%m-%d %H:%M:%S')
                sp_tweets.append(created_at_str+'\n')  # ツイート日時
                sp_tweets.append('\n')  # 空行
                sp_tweets.append(tweet['full_text']+'\n')  # ツイート内容
                level_s = level
                search_specific_tweets(sp_tweets, level_s, auth, tweet['id_str'], user_id, count, range, date_max_str) #再帰呼び出し
                retweet_cnt += 1
        
        print('ID : '+tweet_id+', 引用リツイート数 : ', retweet_cnt)
    
    return sp_tweets

def same_tweet_not_exist(sp_tweets, chkstr):
    rtn = True
    for tweet in sp_tweets:
        if len(tweet) > 52 and tweet[29:48] == chkstr:
            rtn = False
            print("ID : "+chkstr+" はすでにあります")
            break
    return rtn

if __name__ == '__main__':
    args = sys.argv
    if 2<= len(args):
        main(str(args[1]))
    else:
        print('Argument should be Twitter ID')
