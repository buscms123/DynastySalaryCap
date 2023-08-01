# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 10:01:50 2022

@author: senay
"""

import requests
import json
import pandas as pd
from pandasql import sqldf
import numpy as np
import itertools

url='https://api.sleeper.app/v1/players/nfl'
response= requests.get(str(url))
players=response.json()
playersdf=pd.DataFrame.from_dict(players,orient='index')
playersdf.head()

player_map=playersdf[['player_id','full_name']]

league_ids=['785284534815084544','692551563197095936','515573750217351168','434070889605099520']
current_league='956008423521415168'
draft_ids=[]
for league_id in league_ids:
    url="https://api.sleeper.app/v1/league/"+str(league_id)+"/drafts"
    response= requests.get(str(url))
    draft_id=response.json()[0]['draft_id']
    draft_ids.append(draft_id)
    
    
alldraft=pd.DataFrame()
for d in draft_ids:
    url="https://api.sleeper.app/v1/draft/"+str(d)+"/picks"
    response= requests.get(str(url))
    draft_picks=response.json()
    picksdf=pd.DataFrame(draft_picks)
    alldraft=alldraft.append(picksdf)
    
    
    
rosters=pd.DataFrame()

url="https://api.sleeper.app/v1/league/"+str(current_league)+"/rosters"
response= requests.get(str(url))
roster_players=response.json()

current_owner_id=[i["owner_id"] for i in roster_players]
length=[len(i['players'])  for i in roster_players]

data_tuples = list(zip(current_owner_id,length))
own_len=pd.DataFrame(data_tuples, columns=['owner_id','max'])
own_len['index1'] = own_len.index
own_len['Change'] = own_len['max'].cumsum()-1


roster_players2=[i["players"] for i in roster_players]
player_ids= [x for l in roster_players2 for x in l]
player_ids=pd.DataFrame(player_ids)
player_ids.rename(columns={ player_ids.columns[0]: "player_id" }, inplace = True)
player_ids['index1'] = player_ids.index



listo=[]
for x in range(len(own_len)):
    owners=[own_len['owner_id'][x]] * own_len['max'][x]
    listo.append(owners)

ownerlist= [x for l in listo for x in l]


player_ids['owner_id']=ownerlist

player_ids['owner_id'].value_counts()

alldraft=alldraft[['round', 'roster_id', 'player_id', 'picked_by', 'pick_no','is_keeper', 'draft_slot', 'draft_id']]

alldraft.columns
pysqldf = lambda q: sqldf(q, globals())


users=pd.DataFrame()
for d in draft_ids:
    url="https://api.sleeper.app/v1/league/785284534815084544/users"
    response= requests.get(str(url))
    user_json=response.json()
    userdf=pd.DataFrame(user_json)

userdf=userdf[['user_id', 
       'display_name']]

    

## Add player names into all draft picks
q="""
select a.*, b.full_name
from alldraft a
left join player_map b 
on a.player_id=b.player_id
"""

alldraft_names=pysqldf(q)

## add in draft year

conditions=[alldraft_names['draft_id']=='434079151809359872',
                           alldraft_names['draft_id']=='515573750217351169',
                           alldraft_names['draft_id']=='692551563197095937', alldraft_names['draft_id']=='785284534815084545']
    
outputs=['2019','2020','2021','2022']
    
alldraft_names['draft_year']=pd.Series(np.select(conditions,outputs,'None'))

alldraft_names.head()


times_kept = alldraft_names.groupby('player_id')['is_keeper'].sum()

max_draft_year=max(alldraft_names['draft_year'])

current_keepers=alldraft_names.query('is_keeper >0')
current_keepers=current_keepers[current_keepers['draft_year']==max_draft_year]
current_keepers=current_keepers.merge(times_kept,on='player_id',how='left')

current_keepers=current_keepers[['round', 'roster_id', 'player_id', 'picked_by', 'pick_no',
        'draft_slot', 'draft_id', 'full_name','is_keeper_y']]

## add in team display name
current_keepers=current_keepers.rename(columns=({'is_keeper_y':'times_kept'}))
current_keepers=current_keepers.merge(userdf,how='left',left_on='picked_by',right_on='user_id')

current_keepers=current_keepers.sort_values(by=['display_name','times_kept'],ascending=False)


#current_rosters=rosters[['roster_id','player_id','picked_by']]

p="""
select a.*,
b.full_name,
c.times_kept, 
c.pick_no, 
c.draft_slot,
d.display_name
from
player_ids a
left join player_map b
on
a.player_id=b.player_id
left join current_keepers c
on
a.player_id=c.player_id
left join userdf d
on 
a.owner_id=d.user_id
"""

current_rosters=pysqldf(p)




current_rosters['times_kept']=current_rosters['times_kept'].fillna(0)



# Apply Salary cap numbers 


sc_conditions=[current_rosters['times_kept']==0,
                           current_rosters['times_kept']==1,
                           current_rosters['times_kept']==2,
                           current_rosters['times_kept']==3,
                           current_rosters['times_kept']>=4]

sc_outputs=[1,2,4,8,15]

current_rosters['salary']=pd.Series(np.select(sc_conditions,sc_outputs,0))


current_rosters[current_rosters['display_name']=='zjeppesen']

mark=current_rosters[current_rosters['display_name']=='MarkBuffalovin']
zach=current_rosters[current_rosters['display_name']=='zjeppesen']

current_rosters=current_rosters[['display_name','full_name','times_kept','salary']]

current_rosters.to_csv(r'C:\Users\senay\Documents\current_rosters.csv')






