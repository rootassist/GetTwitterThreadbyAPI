import urllib
from requests_oauthlib import OAuth1
import requests
import os, sys
import datetime
import pandas as pd
from time import sleep

class cv:
    # 検索時のパラメーター
    find_number = 100 # 一回あたりの検索数(最大100/デフォルトは15)
    lmitdays = 3 # 元ツイートから3日後までのツイートを検索する（遅レスを除く）
    #出力用配列
    tweets_stock = []
    #応答格納用
    dic_statuses = []
    #ツイート数
    tweet_cnt = 0
    #要求数
    request_cnt = 0
    #認証情報
    authtw = None

def main(arg):

    # APIの秘密鍵
    CK = os.environ['TW_CONSUMER_KEY'] # コンシューマーキー
    CKS = os.environ['TW_CONSUMER_SECRET'] # コンシューマーシークレット
    AT = os.environ['TW_ACCESS_TOKEN_KEY'] # アクセストークン
    ATS = os.environ['TW_ACCESS_TOKEN_SECRET'] # アクセストークンシークレット
    cv.authtw = OAuth1(CK, CKS, AT, ATS)
 
    # ツイートID
    tweet_id = arg
    # tweet_id = '1456473170014203911' # str型で指定
 
    #出力ファイル
    path = os.getcwd()
    dt_now = datetime.datetime.now()
    dt = dt_now.strftime('%Y%m%d%H%M%S')
    outputfn = path+'\TwitterAPISerchID_'+dt+'.txt'

    #階層レベル
    level = 0

    #元ツイートを取得

    param_str = 'max_id:'+tweet_id
    param = urllib.parse.quote_plus(param_str)

    url = 'https://api.twitter.com/1.1/search/tweets.json?lang=ja&q='+param+'&count=1&tweet_mode=extended'
    response = requests.get(url, auth=cv.authtw)
    cv.request_cnt += 1
    if response.status_code == 200:
        data_statuses = response.json()['statuses']
    elif response.status_code == 429:
        print('APIの制限オーバーです : 要求数 : %d' % cv.request_cnt)
        url = 'https://api.twitter.com/1.1/application/rate_limit_status.json?resources=help,users,search,statuses'
        response = requests.get(url, auth=cv.authtw)
        api_remaining = response.json()['resources']['search']['/search/tweets']['remaining']
        api_limit = response.json()['resources']['search']['/search/tweets']['limit']
        print('アクセス可能回数 : %d, アクセスが可能になるまでの秒数 : %d' % (api_remaining, api_limit))
        sys.exit(3)
        # print('15分待ちます')
        # sleep(15*60) 
        # request_cnt = 0
    else:
        print('APIへの要求が %d で返されました' % response.status_code)
        sys.exit(1)

    if len(data_statuses) == 0:  #元データがない
        print('元のツイートのデータがありません')
        sys.exit(2)
    else:
        #応答を格納する
        cv.dic_statuses += [dict(**{'res_key': '<BaseTweet>'},**row) for row in data_statuses]

    tweet_type= 'OriginalTweet'
    tweet_stock_append(tweet_type, tweet_id, data_statuses[0]['id_str'], \
        data_statuses[0]['user']['name'], data_statuses[0]['user']['screen_name'], \
        level, data_statuses[0]['created_at'], data_statuses[0]['full_text'])
    cv.tweet_cnt += 1

    # df = pd.DataFrame({
    #     'tweet_type':tweet_type,
    #     'ref_tweet_id':tweet_id,
    #     'user_name':data[0]['user']['name'],
    #     'user_id':data[0]['user']['screen_name'], 
    #     'level':level,
    #     'created_at':data[0]['created_at'], 
    #     'tweet_text':data[0]['full_text']},
    #     index=tweet_id
    # )
    
    #検索期間の設定
    created_at = datetime.datetime.strptime(data_statuses[0]['created_at'], '%a %b %d %H:%M:%S %z %Y')
    data_min_str = created_at.strftime('%Y-%m-%d')
    date_max = created_at + datetime.timedelta(days=cv.lmitdays) 
    date_max_str = date_max.strftime('%Y-%m-%d')

    #リツイート元
    if data_statuses[0]['is_quote_status']:

        tweet_type= 'QuoteRetweetFrom'
        tweet_stock_append(tweet_type, tweet_id, data_statuses[0]['quoted_status']['id_str'], \
            data_statuses[0]['quoted_status']['user']['name'], data_statuses[0]['quoted_status']['user']['screen_name'], \
            level, data_statuses[0]['quoted_status']['created_at'], data_statuses[0]['quoted_status']['full_text'])
        cv.tweet_cnt += 1

    user_id = '@'+data_statuses[0]['user']['screen_name']  #元ツイートのユーザー名

    # ツイート検索・リプライの抽出
    #tweets = cv.tweets_stock
    search_tweet(level, tweet_id, user_id, data_min_str, date_max_str)
    cv.tweets_stock.append('\n')  # 空行
    
    print('ツイート数 : %d' % cv.tweet_cnt)

    tweets_stock_output(outputfn)


def search_tweet(level, tweet_id, user_id, data_min_str, date_max_str):

    level += 1

    # 返信を得る

    reply_cnt = 0

    #元ツイートのユーザーへの返信を得る
    param_str = 'to:'+user_id+' since:'+data_min_str+' until:'+date_max_str \
        +' since_id:'+tweet_id 

    #すでに同じUser_idで応答があるときには過去の取得データを利用する
    if user_id in [row['res_key'] for row in cv.dic_statuses]: 
        data_statuses = [row for row in cv.dic_statuses if row['res_key'] == user_id]

    else:
        data_statuses = []
        while True:
            param = urllib.parse.quote_plus(param_str)
            url = 'https://api.twitter.com/1.1/search/tweets.json?lang=ja&q='\
                +param+'&count='+str(cv.find_number)+'&tweet_mode=extended'
            response = requests.get(url, auth=cv.authtw)
            cv.request_cnt += 1
            if response.status_code == 200:
                data_statuses += response.json()['statuses']
                if 'next_results' not in response.json()['search_metadata'].keys(): #検索結果の続きがあるときにはそれを得る
                    break
                next_results = response.json()['search_metadata']['next_results']
                param_str = 'to:'+user_id+' since:'+data_min_str+' until:'+date_max_str \
                    +' max_id:'+urllib.parse.parse_qs(next_results.lstrip('?') )['max_id'][0] # さらに古いものを取得
            elif response.status_code == 429:
                print('APIの制限オーバーです : 要求数 : %d' % cv.request_cnt)
                sys.exit(3)
                # print('15分待ちます')
                # sleep(15*60) 
                # request_cnt = 0
            else:
                print('APIへの要求が %d で返されました' % response.status_code)
                sys.exit(1)
        
        #取得した応答を追加
        if len(data_statuses) != 0:  #取得したデータがあるなら
            cv.dic_statuses += [dict(**{'res_key': user_id},**row) for row in data_statuses]

    for tweet in data_statuses:
        if tweet['in_reply_to_status_id_str'] == tweet_id \
                and same_tweet_not_exist(tweet['id_str']): # 返信先がツイートIDに一致するものを抽出
            user_id = '@'+tweet['user']['screen_name']

            tweet_type= 'Reply'
            tweet_stock_append(tweet_type, tweet_id, tweet['id_str'], \
                tweet['user']['name'], user_id, level, tweet['created_at'], tweet['full_text'])
            cv.tweet_cnt += 1

            level_s = level
            search_tweet(level_s, tweet['id_str'], user_id, data_min_str, date_max_str) #再帰呼び出し
            reply_cnt += 1
    
    print('ID : %s, リプライ数 : %d, 要求数 : %d' % (tweet_id, reply_cnt, cv.request_cnt))
    
    # リツイートを得る

    retweet_cnt = 0

    #元ツイートへの引用リツイートを検索
    param_str = 'url:'+tweet_id+' -filter:retweets'+' since:'+data_min_str+' until:'+date_max_str \
            +' since_id:'+tweet_id 

    #すでに同じtweet_idで応答があるときには過去の取得データを利用する
    if tweet_id in [row['res_key'] for row in cv.dic_statuses]: 
        data_statuses = [row for row in cv.dic_statuses  if row['res_key'] == tweet_id]
    
    else:
        data_statuses = []
        while True:
            param = urllib.parse.quote_plus(param_str)
            url = 'https://api.twitter.com/1.1/search/tweets.json?lang=ja&q='\
                +param+'&count='+str(cv.find_number)+'&tweet_mode=extended'
            response = requests.get(url, auth=cv.authtw)
            cv.request_cnt += 1
            if response.status_code == 200:
                data_statuses += response.json()['statuses']
                #検索結果の続きがあるときにはそれを得る
                if 'next_results' not in response.json()['search_metadata'].keys(): 
                    break
                next_results = response.json()['search_metadata']['next_results']
                param_str = 'url:'+tweet_id+' -filter:retweets'+' since:'+data_min_str+' until:'+date_max_str \
                    +' max_id:'+urllib.parse.parse_qs(next_results.lstrip('?') )['max_id'][0] # さらに古いものを取得
            elif response.status_code == 429:
                print('APIの制限オーバーです : 要求数 : %d' % cv.request_cnt)
                sys.exit(3)
                # print('15分待ちます')
                # sleep(15*60) 
                # request_cnt = 0
            else:
                print('APIへの要求が %d で返されました' % response.status_code)
                sys.exit(1)

            #取得した応答を追加
            if len(data_statuses) != 0:  #取得したデータがあるなら
                cv.dic_statuses += [dict(**{'res_key': tweet_id},**row) for row in data_statuses]

    for tweet in data_statuses:
        # 引用リツイート先がツイートIDに一致するものを抽出
        if tweet['is_quote_status'] \
                and  tweet['quoted_status']['id_str'] == tweet_id \
                and same_tweet_not_exist(tweet['id_str']): 
            user_id = '@'+tweet['user']['screen_name']
            
            tweet_type= 'QuoteRetweetTo'
            tweet_stock_append(tweet_type, tweet_id, tweet['id_str'], \
                tweet['user']['name'], user_id, \
                level, tweet['created_at'], tweet['full_text'])
            cv.tweet_cnt += 1

            level_s = level
            search_tweet(level_s, tweet['id_str'], user_id, \
                data_min_str, date_max_str) #再帰呼び出し
            retweet_cnt += 1
    
    print('ID : %s, 引用リツイート数 : %d, 要求数 : %d' % (tweet_id, retweet_cnt, cv.request_cnt))

def tweet_stock_append(tweet_type, ref_tweet_id, tweet_id, \
        user_name, user_id, level, created_at, tweet_text):
    if tweet_type == 'OriginalTweet':
        delimit_str = '■■■■■'
    elif tweet_type == 'QuoteRetweetFrom':
        delimit_str = '▲▲▲▲▲'
    elif tweet_type == 'Reply':
        delimit_str = '▼▼▼▼▼'
    elif tweet_type == 'QuoteRetweetTo':
        delimit_str = '▽▽▽▽▽'
    else:
        return
    
    cv.tweets_stock.append('\n')  # 空行
    cv.tweets_stock.append(delimit_str+ref_tweet_id+delimit_str+tweet_id+delimit_str+str(level)+'\n')  # デリミタ
    cv.tweets_stock.append('\n')  # 空行
    cv.tweets_stock.append(user_name+user_id+'\n')  # 表示名
    created_at = datetime.datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
    created_at_jst = created_at + datetime.timedelta(hours=9) # JST
    created_at_str = created_at_jst.strftime('%Y-%m-%d %H:%M:%S')
    cv.tweets_stock.append(created_at_str+'\n')  # ツイート日時
    cv.tweets_stock.append('\n')  # 空行
    cv.tweets_stock.append(tweet_text+'\n')  # ツイート内容

def same_tweet_not_exist(chkstr):
    rtn = True
    for tweet in cv.tweets_stock:
        if len(tweet) > 52 and tweet[29:48] == chkstr:
            rtn = False
            print('ID : %s はすでにあります' % chkstr)
            break
    return rtn

def tweets_stock_output(outputfn):
    for tweet in cv.tweets_stock:
        print(tweet)

    #ファイル出力
    f = open(outputfn,'a', encoding='UTF-8')
    f.writelines(cv.tweets_stock)
    f.close()
    print('出力ファイル名 : %s' % outputfn)

if __name__ == '__main__':
    args = sys.argv
    if 2<= len(args):
        main(str(args[1]))
    else:
        print('Argument should be Twitter ID')
