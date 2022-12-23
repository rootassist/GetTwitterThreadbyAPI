import urllib
from requests_oauthlib import OAuth1
from time import sleep
import requests
import datetime
import pandas as pd
import os, sys, time


class ParamValues:
    
    # 検索時のパラメーター
    find_number = 100 # 一回あたりの検索数(最大100/デフォルトは15)
    lmitdays = 4 # 元ツイートから4日後までのツイートを検索する（遅レスを除いて検索数を減らす）
    
    #認証情報
    authtw = None
  

class CounterValues:
    
    #ツイート数
    tweet_cnt = 0
    #要求数
    request_cnt = 0


class TweetInfo:

    # 元ツイートのID
    basetweet_id = ''
    #出力用配列
    # tweets_stock = []
    tweets_output = []
    #出力用DataFrame
    df_tweets = []
    #応答格納用
    dic_statuses = []
    
    
def main(tweet_id, CK, CKS, AT, ATS):

    # 認証情報
    ParamValues.authtw = OAuth1(CK, CKS, AT, ATS)

    # ツイートID
    TweetInfo.basetweet_id = tweet_id

    #階層レベル
    level = 0

    #元ツイートを取得

    param_str = 'max_id:'+tweet_id

    data_statuses = twitter_api(param_str, '<BaseTweet>', 1)

    # 取得した応答を追加

    if len(data_statuses) != 0:  #取得したデータがあるなら
        TweetInfo.dic_statuses += [dict(**{'res_key': '<BaseTweet>'},**row) for row in data_statuses]

    tweet_type= 'OriginalTweet'

    TweetInfo.df_tweets = pd.DataFrame([[
        tweet_type,
        tweet_id,
        data_statuses[0]['user']['name'],
        '@'+data_statuses[0]['user']['screen_name'],
        level,
        datetime_jst(data_statuses[0]['created_at']),
        data_statuses[0]['full_text']]],
        columns=['tweet_type','ref_tweet_id','user_name','user_id','level','created_at','tweet_text'],
        index=[data_statuses[0]['id_str']]
    )

    CounterValues.tweet_cnt += 1

    #検索期間の設定

    created_at = datetime.datetime.strptime(data_statuses[0]['created_at'], '%a %b %d %H:%M:%S %z %Y')
    data_min_str = created_at.strftime('%Y-%m-%d')
    date_max = created_at + datetime.timedelta(days=ParamValues.lmitdays)
    date_max_str = date_max.strftime('%Y-%m-%d')

    #リツイートの場合、その元ツイートを得る

    if data_statuses[0]['is_quote_status']:

        tweet_type= 'QuoteRetweetFrom'

        TweetInfo.df_tweets.loc[data_statuses[0]['quoted_status']['id_str']]=[
                tweet_type,
                tweet_id,
                data_statuses[0]['quoted_status']['user']['name'],
                '@'+data_statuses[0]['quoted_status']['user']['screen_name'],
                level,
                datetime_jst(data_statuses[0]['quoted_status']['created_at']),
                data_statuses[0]['quoted_status']['full_text']
        ]

        CounterValues.tweet_cnt += 1

    user_id = '@'+data_statuses[0]['user']['screen_name']  #元ツイートのユーザー名

    # ツイート検索・リプライの抽出

    search_tweet(level, tweet_id, user_id, data_min_str, date_max_str)

    #結果出力

    print('ツイート数 : %d' % CounterValues.tweet_cnt)
    tweets_stock_output()


def search_tweet(level, tweet_id, user_id, data_min_str, date_max_str):

    level += 1

    # 元ツイートへの返信を得る

    reply_cnt = 0

    param_str = 'to:'+user_id+' until:'+date_max_str +' since_id:'+TweetInfo.basetweet_id

    # すでに同じUser_idで検索結果を得ているときにはそれを流用する
    # なければTwitter APIを呼び出し

    if user_id in [row['res_key'] for row in TweetInfo.dic_statuses]:
        data_statuses = [row for row in TweetInfo.dic_statuses if row['res_key'] == user_id]

    else:
        data_statuses = twitter_api(param_str, user_id, ParamValues.find_number)

        # 取得した応答を追加

        if len(data_statuses) != 0:  #取得したデータがあるなら
            TweetInfo.dic_statuses += [dict(**{'res_key': user_id},**row) for row in data_statuses]

    for tweet in data_statuses:
        if tweet['in_reply_to_status_id_str'] == tweet_id \
                and same_tweet_not_exist(tweet['id_str']):

            # 返信先が元ツイートのものを抽出する

            user_id = '@'+tweet['user']['screen_name']

            tweet_type= 'Reply'

            TweetInfo.df_tweets.loc[tweet['id_str']]=[
                    tweet_type,
                    tweet_id,
                    tweet['user']['name'],
                    user_id,
                    level,
                    datetime_jst(tweet['created_at']),
                    tweet['full_text']
            ]

            CounterValues.tweet_cnt += 1

            level_s = level
            search_tweet(level_s, tweet['id_str'], user_id, data_min_str, date_max_str) #再帰呼び出し
            reply_cnt += 1

    print('ID : %s, リプライ数 : %d, 要求数 : %d' % (tweet_id, reply_cnt, CounterValues.request_cnt))

    # リツイートを得る

    retweet_cnt = 0

    # 元ツイートへの引用リツイートを検索（元ツイートのツイートIDに対する返信）
    # 期間は元ツイートの作成日+ParamValues.lmitdays まで、ツイートのIDは元ツイートのIDより大きいもの

    param_str = 'url:'+tweet_id+' -filter:retweets'+' until:'+date_max_str +' since_id:'+TweetInfo.basetweet_id

    # すでに同じtweet_idで検索結果を得ているときにはそれを流用する
    # なければTwitter APIを呼び出し

    if tweet_id in [row['res_key'] for row in TweetInfo.dic_statuses]:
        data_statuses = [row for row in TweetInfo.dic_statuses  if row['res_key'] == tweet_id]

    else:
        data_statuses = twitter_api(param_str, user_id, ParamValues.find_number)

        # 取得した応答を追加

        if len(data_statuses) != 0:  #取得したデータがあるなら
            TweetInfo.dic_statuses += [dict(**{'res_key': tweet_id},**row) for row in data_statuses]

    for tweet in data_statuses:

        # 引用リツイート先がツイートIDに一致するものを抽出

        if tweet['is_quote_status'] \
                and  tweet['quoted_status']['id_str'] == tweet_id \
                and same_tweet_not_exist(tweet['id_str']):

            user_id = '@'+tweet['user']['screen_name']

            tweet_type= 'QuoteRetweetTo'

            TweetInfo.df_tweets.loc[tweet['id_str']]=[
                    tweet_type,
                    tweet_id,
                    tweet['user']['name'],
                    user_id,
                    level,
                    datetime_jst(tweet['created_at']),
                    tweet['full_text']
            ]

            CounterValues.tweet_cnt += 1

            level_s = level
            search_tweet(level_s, tweet['id_str'], user_id, \
                data_min_str, date_max_str) #再帰呼び出し
            retweet_cnt += 1

    print('ID : %s, 引用リツイート数 : %d, 要求数 : %d' % (tweet_id, retweet_cnt, CounterValues.request_cnt))


def twitter_api(param_str, user_id, findnumber):

    data_statuses = []
    while True:

        param = urllib.parse.quote_plus(param_str)
        url = 'https://api.twitter.com/1.1/search/tweets.json?lang=ja&q='\
            +param+'&count='+str(findnumber)+'&tweet_mode=extended'
        response = requests.get(url, auth=ParamValues.authtw)
        CounterValues.request_cnt += 1

        if response.status_code == 200:

            data_statuses += response.json()['statuses']

            # 検索結果の続きがあるときにはそれを得る

            if 'next_results' not in response.json()['search_metadata'].keys():
                break

            # ただし検索結果がfindnumber未満のとき、およびfindnumberが1のときには
            # next_resultsの存在を無視して検索を終了する
            # (次に検索しても検索結果が0なので検索回数が無駄になる)

            if len(data_statuses) < findnumber or findnumber == 1:
                break

            next_results = response.json()['search_metadata']['next_results']

            # さらに古いIDのツイートを取得

            param_str += ' max_id:'+urllib.parse.parse_qs(next_results.lstrip('?') )['max_id'][0]

        elif response.status_code == 429:

            #契約プランでの取得限界

            print('APIの制限オーバーです : 要求数 : %d' % CounterValues.request_cnt)
            url = 'https://api.twitter.com/1.1/application/rate_limit_status.json?resources=help,users,search,statuses'
            response = requests.get(url, auth=ParamValues.authtw)
            api_remaining = response.json()['resources']['search']['/search/tweets']['remaining']
            api_limit = datetime.datetime.fromtimestamp(response.json()['resources']['search']['/search/tweets']['reset'])
            print('アクセス可能回数 : %d, アクセスが可能になる日時 : %s' % (api_remaining, api_limit))
            # sys.exit(3)
            seconds = response.json()['resources']['search']['/search/tweets']['reset']  - int(time.mktime(datetime.datetime.now().timetuple()))
            print('%d 秒待ちます' % seconds)

            #スリープ対策として60秒ごとに現在時刻と再開目標時刻と比較する

            targettime = time.time() + seconds + 10
            while True:
                time.sleep(60)
                nowtime = time.time()
                if nowtime > targettime:
                    break
            
        else:

            # それ以外のエラー

            print('APIへの要求が %d で返されました' % response.status_code)
            
            #ここまでの結果を出力して強制終了

            tweets_stock_output()
            sys.exit(1)

    #本文テキストの先頭に返信先のIDがあったら、その後ろに改行を追加する

    data_statuses = add_after_replyid(data_statuses)

    return data_statuses


def add_after_replyid(mydiclist):
    import re

    for mydic in mydiclist:
        full_text = mydic['full_text']

        ptn = r'(^@.+? )(@.+? ){0,}'
        found_str = re.search(ptn, full_text)

        if found_str:
            idstrs = re.finditer(ptn, full_text)
            for idstritem in idstrs:
                idstr = idstritem.group()

            mydic['full_text'] = idstr+'\n\n'+full_text[len(idstr):]

    return mydiclist


def datetime_jst(dt):
    dt = datetime.datetime.strptime(dt, '%a %b %d %H:%M:%S %z %Y')
    dt_jst = dt + datetime.timedelta(hours=9) # JST
    return dt_jst.strftime('%Y-%m-%d %H:%M:%S')


def same_tweet_not_exist(chkstr):

    rtn = True
    if chkstr in TweetInfo.df_tweets:
        rtn = False
        print('ID : %s はすでにあります' % chkstr)

    return rtn


def tweets_stock_output():

    print(TweetInfo.df_tweets)

    df_tweet_output()

    #出力ファイル名

    path = os.getcwd()
    dt_now = datetime.datetime.now()
    dt = dt_now.strftime('%Y%m%d%H%M%S')
    outputfn = path+'\TwitterAPISearchID_'+TweetInfo.basetweet_id+'_'+dt+'.txt'
    outputfnjson = path+'\TwitterAPISearchID_'+TweetInfo.basetweet_id+'_'+dt+'.json'

    #ファイル出力

    f = open(outputfn,'a', encoding='UTF-8')
    f.writelines(TweetInfo.tweets_output)
    f.close()
    print('出力ファイル名 : %s' % outputfn)

    buf = TweetInfo.df_tweets.to_json(force_ascii=False, \
            orient='index', indent=4, double_precision=15)
    with open(outputfnjson, 'wt', encoding='UTF-8') as f:
        f.write(buf)
    print('出力ファイル名 : %s' % outputfnjson)


def df_tweet_output():

    for row in TweetInfo.df_tweets.itertuples():

        if row.tweet_type == 'OriginalTweet':
            delimit_str = '■■■■■'
        elif row.tweet_type == 'QuoteRetweetFrom':
            delimit_str = '▲▲▲▲▲'
        elif row.tweet_type == 'Reply':
            delimit_str = '▼▼▼▼▼'
        elif row.tweet_type == 'QuoteRetweetTo':
            delimit_str = '▽▽▽▽▽'
        else:
            return

        TweetInfo.tweets_output.append('\n')  # 空行
        TweetInfo.tweets_output.append(delimit_str+row.ref_tweet_id+delimit_str+row.Index+delimit_str+str(row.level)+'\n')  # デリミタ
        TweetInfo.tweets_output.append('\n')  # 空行
        TweetInfo.tweets_output.append(row.user_name+row.user_id+'\n')  # 表示名
        TweetInfo.tweets_output.append(row.created_at+'\n')  # ツイート日時
        TweetInfo.tweets_output.append('\n')  # 空行
        TweetInfo.tweets_output.append(row.tweet_text+'\n')  # ツイート内容

    return


if __name__ == '__main__':

    args = sys.argv

    if 2 != len(args):
        print('No argument specified')

    else:
        # 検索するツイッターのID
        argstr = str(args[1])

        # 引数に指定されているのがTwitter IDかURLでなければエラー
        SearchTweetID = ''
        if len(argstr) == 19 and argstr.isdecimal():
            SearchTweetID = argstr
        elif len(argstr) > 19 and argstr[-20] == '/' \
          and argstr[0:4] == 'http' and argstr[-19:].isdecimal():
            SearchTweetID = argstr[-19:]
        if SearchTweetID == '':            
            print('Argument should be Twitter ID or URL')

        else:            
            #SearchTweetID = '' # str型で指定 デバッグ用

            # APIの秘密鍵
            CK = os.environ['TW_CONSUMER_KEY'] # コンシューマーキー
            CKS = os.environ['TW_CONSUMER_SECRET'] # コンシューマーシークレット
            AT = os.environ['TW_ACCESS_TOKEN_KEY'] # アクセストークン
            ATS = os.environ['TW_ACCESS_TOKEN_SECRET'] # アクセストークンシークレット
        
            main(SearchTweetID, CK, CKS, AT, ATS)
