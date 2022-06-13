#pip install chart_studio

import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import math, time
from statsbombpy import sb
from PIL import Image
from fpdf import FPDF
from mplsoccer.pitch import Pitch, VerticalPitch
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from imblearn.over_sampling import SMOTE
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from tempfile import NamedTemporaryFile
import base64

#from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
#import chart_studio.plotly as py
#import cufflinks as cf

#%matplotlib inline


#st. set_page_config(layout="wide")


def app():

        
        image = Image.open('teamPage.jpg')
        
        col1, col2 = st.columns(2)
        
        col1.title("Team Shot Analysis")
        
        col2.image(image)
        
        
        #st.write("Raw Data")
        #Code to retrieve the data from statsbomb
        
        #season_id = st.selectbox(
         #   "Chose the Season", Teams)
        
        #download the competition and season data from statsbomb
        df = sb.matches(competition_id=37, season_id=4)
        Teams = df['home_team'].sort_values(ascending=True)
        Teams = Teams.unique()
        

        
        #select the team for analysis
        teamSelect = st.selectbox(
            "Choose the Team:", Teams)
        
        
        crest = Image.open(f'FA_WSL/{teamSelect}.png')
        col1.image(crest)
        
                
        teamdf = df[(df.home_team == teamSelect ) | (df.away_team == teamSelect)]
        team_match_id = teamdf["match_id"]
        
        @st.cache(allow_output_mutation  = True, suppress_st_warning=True)
        #download the event data for all matches of the season for the seleted team
        def teamEventData(t_match_id):
        
            
            appended_event = []
            st_time = time.time()
            
            for i in t_match_id:
                event = sb.events(match_id = i)
                appended_event.append(event)
            appended_event = pd.concat(appended_event)
            
            et_time = time.time()
            elapsed_time = et_time - st_time
            e_time = str(round(elapsed_time,2))
            st.info(f"data import success in {e_time} seconds " )
            
            return appended_event
        
        final_event_data = teamEventData(team_match_id)
        
        ##PLAYER DATA IMPORT
        
        df_player_data = pd.read_csv('playerdata.csv')
        df_player = df_player_data
        
        df_player= df_player.drop(['playerid','Rk'],axis=1)
        df_team_mins = df_player[df_player["Squad"]== teamSelect]
        
        df_team_mins['player'] = df_team_mins['Player']
        #df_team_mins.rename(columns = {'Player':'player'}, inplace = True)
        df_team_m = df_team_mins
        #df_team_m
        
        df_team_m['player'] = df_team_mins['player'].str.slice(-3)
        #df_team_m
        
        
        ##SHOT DATA PREPARATION
        
        shot_df = final_event_data.loc[(final_event_data['type'] == 'Shot' ) & (final_event_data['team'] == teamSelect)]
        
        shot_df_split_new = shot_df
        
        
        #####MODELLING########
        def xg_model  (shot_df):
        
            #creating new data to use further
            shot_df_split_new = shot_df
            shot_df_split_export = shot_df_split_new
            shot_df_split_new_ex = shot_df_split_new
            ##PREFERENCE FOOT CODE
    
            pref_foot = shot_df_split_new[['player','shot_body_part']].copy()
            
            pref = pref_foot.groupby(["player",'shot_body_part'])["shot_body_part"].count()
            abc =pref.unstack(level=1)
            
            abc = abc.reset_index(level=0)
            abc = abc.replace(np.nan, 0)
            
            abc["player_pref_foot"] = 0
            for i in range(len(abc)) :
                if float(abc.iloc[i,2]) >  float(abc.iloc[i,3]) :
                    abc.iloc[i,4] = 'Left'
                else:
                    abc.iloc[i,4] = 'Right'
            
                    
            pref_foot_player = abc[['player','player_pref_foot']].copy()
            shot_df_split_ex=shot_df_split_new_ex.merge(pref_foot_player,left_on="player",right_on="player")
            
            player_pref_foot = shot_df_split_ex["player_pref_foot"]
            
            abc = player_pref_foot.to_frame()
            
            shot_df_split_new["player_pref_foot"] = 0
            for i in range(len(shot_df_split_new)) :
                shot_df_split_new.iloc[i,-1] =  abc.iloc[i,0]
            
            
            shot_df_split_new[['x', 'y']] = shot_df['location'].apply(pd.Series)
            shot_df_split_new['y'] = 80-shot_df_split_new['y']
            shot_df_split_new[['endx', 'endy', 'endz']] = shot_df['shot_end_location'].apply(pd.Series)
            shot_df_split_new['endy'] = 80-shot_df_split_new['endy']
    
            shot_df_split_new['distance'] =  ((120 - shot_df_split_new['x'] )**2 + (40 - shot_df_split_new['y'] )**2)**0.5
            #shot_df_split_new
            
            for i in range(len(shot_df_split_new)) :
                if shot_df_split_new.iloc[i,-1] ==0 and shot_df_split_new.iloc[i,-1] <=5.5  :
                    shot_df_split_new.iloc[i,-1] = 'Close Range'
                elif shot_df_split_new.iloc[i,-1] > 5.5 and shot_df_split_new.iloc[i,-1] <=16.5  :
                    shot_df_split_new.iloc[i,-1] = 'Penalty Box'
                elif shot_df_split_new.iloc[i,-1] > 16.5 and shot_df_split_new.iloc[i,-1] <=21  :
                    shot_df_split_new.iloc[i,-1] = 'Outside Box'
                elif shot_df_split_new.iloc[i,-1] > 21 and shot_df_split_new.iloc[i,-1] <=32  :
                    shot_df_split_new.iloc[i,-1] = 'Long Range'
                else:
                    shot_df_split_new.iloc[i,-1] ='more_35yd'

    
                        
            shotDistance = {'Close Range':4, 
                'Penalty Box':3, 
                'Outside Box':2, 
                'Long Range':1, 
                'more_35yd':0.5}
            shot_df_split_new['distance'] = shot_df_split_new.distance.map(shotDistance)
            
            
            #FOR END location DISTANCE
            #for i in range(len(shot_df_split_new)) :
            #    if shot_df_split_new.iloc[i,114] ==0 and shot_df_split_new.iloc[i,113] <=5.5  :
            #        shot_df_split_new.iloc[i,114] = 'Very Close'
            #    elif shot_df_split_new.iloc[i,114] > 5.5 and shot_df_split_new.iloc[i,113] <=16.5  :
            #        shot_df_split_new.iloc[i,114] = ''
            #    elif shot_df_split_new.iloc[i,114] > 16.5 and shot_df_split_new.iloc[i,113] <=21  :
            #        shot_df_split_new.iloc[i,114] = 'Outside Box'
            #    elif shot_df_split_new.iloc[i,114] > 21 and shot_df_split_new.iloc[i,113] <=32  :
            #        shot_df_split_new.iloc[i,114] = 'Long Range'
            #    else:
            #        shot_df_split_new.iloc[i,114] ='more_35yd'
    
            
            
            shot_df_split_new.loc[(shot_df_split_new.shot_first_time) == True, 'shot_first_time'] = 1
            shot_df_split_new.loc[(shot_df_split_new.shot_first_time).isna(), 'shot_first_time'] = 0
                    
            shot_df_split_new.loc[(shot_df_split_new.shot_one_on_one) == True, 'shot_one_on_one'] = 1
            shot_df_split_new.loc[(shot_df_split_new.shot_one_on_one).isna(), 'shot_one_on_one'] = 0

            shot_df_split_new.loc[(shot_df_split_new.under_pressure) == True, 'under_pressure'] = 1
            shot_df_split_new.loc[(shot_df_split_new.under_pressure).isna(), 'under_pressure'] = 0
            
            shot_df_split_new.loc[(shot_df_split_new.shot_open_goal) == True, 'shot_open_goal'] = 1
            shot_df_split_new.loc[(shot_df_split_new.shot_open_goal).isna(), 'shot_open_goal'] = 0
            
            num = shot_df_split_new.columns.get_loc("shot_outcome")
            shot_df_split_new['outcome_shot'] = 0
                        
            for i in range(len(shot_df_split_new)) :
                #print(shot_df_split_new.iloc[i,num])
                if shot_df_split_new.iloc[i,num] == 'Goal':
                    shot_df_split_new.iloc[i,-1] = 'On Target'
                elif shot_df_split_new.iloc[i,num] == 'Saved':
                    shot_df_split_new.iloc[i,-1] = 'On Target'
                elif shot_df_split_new.iloc[i,num] == 'Off T':
                    shot_df_split_new.iloc[i,-1] = 'Off Target'
                elif shot_df_split_new.iloc[i,num] == 'Wayward':
                    shot_df_split_new.iloc[i,-1] = 'Off Target'
                elif shot_df_split_new.iloc[i,num] == 'Post':
                    shot_df_split_new.iloc[i,-1] = 'Post'
                else:
                    shot_df_split_new.iloc[i,-1] = 'Blocked'
                    
            shotOutcome = {'Off Target':0, 
            'Blocked':.2, 
            'Post':.4, 
            'On Target':.7}
            shot_df_split_new['outcome_shot'] = shot_df_split_new.outcome_shot.map(shotOutcome)
            
            
            dataraw = shot_df_split_new[['distance','player_pref_foot','shot_body_part','shot_type','shot_technique','outcome_shot','shot_first_time','shot_one_on_one','under_pressure','shot_open_goal']].copy()
            #dataraw = shot_df_split_new[['distance','player_pref_foot','shot_body_part','shot_type','shot_technique','shot_first_time','shot_one_on_one','under_pressure','shot_open_goal']].copy()
            #dataraw        
            
            #data = pd.get_dummies(dataraw, columns=['distance','player_pref_foot', 'shot_body_part','shot_type', 'shot_technique'])
            data = pd.get_dummies(dataraw, columns=['player_pref_foot', 'shot_body_part','shot_type', 'shot_technique'])
            #data
            
            
            num = shot_df_split_new.columns.get_loc("shot_outcome")
            shot_df_split_new['is_goal'] = 0
            
            for i in range(len(shot_df_split_new)) :
                if shot_df_split_new.iloc[i,num] == 'Goal':
                    shot_df_split_new.iloc[i,-1] =1
                else:
                    shot_df_split_new.iloc[i,-1] =0
                        
            data['is_goal'] = shot_df_split_new['is_goal']
            #data
            datatest = data
            
            #train_test_split
    
            X = datatest.iloc[:,:-1]
            y = datatest.iloc[:,-1]
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.35, random_state=1)
            
            #SMOTE
            smote = SMOTE()
            X_train, y_train = smote.fit_resample(X_train, y_train)
            #X_train
            
            #from sklearn.linear_model import LogisticRegression
            model = LogisticRegression()
            model.fit(X_train, y_train)
            
            st.write('The test set contains {} examples (shots) of which {} are positive (goals).'.format(len(y_test), y_test.sum()))
            st.write('The accuracy of classifying whether a shot is goal or not is {}%.'.format(round(model.score(X_test, y_test)*100),2))
            
            
            #from sklearn.metrics import confusion_matrix
            #print(confusion_matrix(y_test,model.predict(X_test)))
            #
            #from sklearn.metrics import classification_report
            #print(classification_report(y_test,model.predict(X_test)))
    
    
            prob = model.predict_proba(X)
            
            data['xg'] = prob.tolist() 
            
            data[['xg_0', 'xg_1']] = data['xg'].apply(pd.Series)
            
            shot_df_split_new['xg_0'] = data['xg_0']
            shot_df_split_new['xg_1'] = data['xg_1']
            #shot_df_split_export['distance'] = data['distance']
            
            shot_df_split_out = shot_df_split_new[['player','location','shot_end_location','player_pref_foot','distance','shot_outcome','is_goal','shot_statsbomb_xg','xg_1']].copy()
            
            AgGrid(shot_df_split_out.head(20))
            
            return shot_df_split_export
        #####################33
        
        
        
        
        
        run_model = st.button("Run xG Model")
        st.markdown("_____________________________________________________________________________")
        try:
            if run_model:
                xg_df = xg_model(shot_df)
        except IndexError:
                st.info(f"Model not available for {teamSelect} data set hence using Statbomb xG.")        
            
        except ValueError:
                st.info("Model not available for {teamSelect} data set hence using Statbomb xG.")        
        
        except KeyError:
                st.info("Model not available for {teamSelect} data set hence using Statbomb xG.")        
        
        
        goal_df = shot_df_split_new[(shot_df_split_new['shot_outcome'] == 'Goal' )]
        #goal_df
        for i in range(len(goal_df)) :
            if goal_df.iloc[i,68] == 'Goal' :
                goal_df['Goal'] =1
            else:
                goal_df['Goal'] =0
        
        totalGoals = len(goal_df)
        
        goal_df_player = goal_df[['player','Goal']].copy()
        
        goal_df_player = goal_df_player.groupby(["player",'Goal'])["Goal"].count()
        goal_df_player = goal_df_player.to_frame()
        abc = goal_df_player.reset_index(level=0)
        goal_df_player = abc.reset_index(drop=True)
        goal_df_player = goal_df_player.sort_values("Goal", ascending=False)
        #goal_df_player
        goal_df_player_m = goal_df_player
        goal_df_player_m['player'] = goal_df_player['player'].str.slice(-3)
        #goal_df_player_m
        
        
        
        #XG DF
        

        xg_df_player = shot_df_split_new[['player','shot_statsbomb_xg']].copy()
        xg_df_player = xg_df_player.groupby(["player"])["shot_statsbomb_xg"].sum()
        xg_df_player = xg_df_player.to_frame()  ####
        ab = xg_df_player.reset_index(level=0)
        xg_df_player = ab.reset_index(drop=True)
        
        xg_df_player = xg_df_player.sort_values("shot_statsbomb_xg", ascending=False)
        #goal_df_player
        xg_df_player_m = xg_df_player
        xg_df_player_m['player'] = xg_df_player['player'].str.slice(-3)
        #xg_df_player_m
        
        mergedPlayer_df = pd.merge(goal_df_player_m, df_team_m,on="player")
        #mergedPlayer_df
        mergedPlayer_df['G_90'] = mergedPlayer_df.Goal/mergedPlayer_df['90s']
        
        mergedPlayer_finaldf = pd.merge(mergedPlayer_df, xg_df_player_m,on="player")
        
        mergedPlayer_finaldf['xg_90'] = mergedPlayer_finaldf.shot_statsbomb_xg/mergedPlayer_df['90s']
        
        mergedPlayer_finaldf.rename(columns = {'shot_statsbomb_xg':'xG'}, inplace = True)
        
        
        
        ##Descriptive for Overview

        goals_for= 0
        goals_against= 0
        
        
        #Calculate Goals Against      
                
        for i in range(len(teamdf)) :
            if teamdf.iloc[i,5]== teamSelect:
                goals_against=goals_against+int(teamdf.iloc[i, 8])
            else:
                goals_against=goals_against+int(teamdf.iloc[i, 7])
        
        goalDiff = totalGoals-goals_against        
        
        
        h_wins= 0
        h_draws= 0
        h_losses= 0
        a_wins= 0
        a_draws= 0
        a_losses= 0
        
        for i in range(len(df)) :
            if df.iloc[i,5]== teamSelect :
                if (df.iloc[i,7] > df.iloc[i,8]) : 
                    h_wins=h_wins+1
                if (df.iloc[i,7] == df.iloc[i,8]) :
                    h_draws=h_draws+1
                if (df.iloc[i,7] < df.iloc[i,8]) :
                    h_losses=h_losses+1
                else :  
                    h_wins=h_wins+0
            if df.iloc[i,6]== teamSelect :
                if (df.iloc[i,8] > df.iloc[i,7]) :
                    a_wins=a_wins+1
                if (df.iloc[i,8] == df.iloc[i,7]) :
                    a_draws=a_draws+1
                if (df.iloc[i,8] < df.iloc[i,7]) :
                    a_losses=a_losses+1
                else :  
                    a_wins=a_wins+0
        
        wins= (h_wins + a_wins)
        draws= (h_draws + a_draws)
        losses= (h_losses + a_losses)
        points= (wins*3+draws*1+losses*0)
        
        
        cola, colb, colc, cold, cole, colf, colg = st.columns(7)
        st.markdown("_____________________________________________________________________________")
        
        #cola.write(f"Wins 👟  {wins}")
        cola.metric("Wins 🏆", wins )
        colb.metric("Draw 🤝", draws)
        colc.metric("Losses 🚫", losses)
        cold.metric("Points 💯 ",points)
        cole.metric("Goals ⚽",totalGoals)
        colf.metric("Goals Against 🥅",goals_against)
        colg.metric("Goal Difference ➕➖",goalDiff)
        
        
        
        ################### DATA PREPARATION #################################
        
        ##Code to create location coordinates
        
        
        shot_df_split_new[['x', 'y']] = shot_df['location'].apply(pd.Series)
        shot_df_split_new['y'] = 80-shot_df_split_new['y']
        shot_df_split_new[['endx', 'endy', 'endz']] = shot_df['shot_end_location'].apply(pd.Series)
        shot_df_split_new['endy'] = 80-shot_df_split_new['endy']
        
        
        
        figs = []
               
        
        ##SHOT OUTCOME
        shots = shot_df[shot_df.type=='Shot']
        
        pie = shots[['shot_outcome', 'id']].groupby('shot_outcome').count().reset_index().rename(columns={'id': 'count'})
        
        #Shot outcomes
        fig1, ax1= plt.subplots(figsize=[8,8])
        labels1 = pie['shot_outcome']
        lenX = len(pie['count'])
        colors1 = ['#ff9999','#99ff99','#66b3ff','#ffcc99','#e0b0ff', 'red', 'grey', 'yellow']
        plt.pie(x=pie['count'], autopct='%.1f%%', explode=[0.04]*lenX,pctdistance=0.8,colors=colors1, \
            textprops=dict(fontsize=16))
        my_circle=plt.Circle( (0,0), 0.7, color='white')
        p=plt.gcf()
        p.gca().add_artist(my_circle)
        circle = plt.Circle( (0,0), 0.7, color='white')
        plt.legend(labels1,loc="center left",bbox_to_anchor=(1,0, 5, 1))
        plt.title(f"{teamSelect} Shot Outcomes", fontsize=16, fontfamily='serif')
        plt.tight_layout()
        #plt.show()
         

        fig = sns.jointplot(data=mergedPlayer_finaldf, x="G_90", y="xg_90", hue = 'Player')
        fig.fig.suptitle("Individual xG p/90 v. Goals p/90", fontsize=12, fontfamily='serif')
        fig.set_axis_labels('x', 'y', fontsize=10)
        fig.ax_joint.set_xlabel('Goals p/90')
        fig.ax_joint.set_ylabel('xG p/90')
        
        
        col6, col7 = st.columns(2)
        col6.pyplot(fig)  
        figs.append(fig)
        col6.markdown("The scatter plot above allows one to assess the normalized goal scoring performance of all players in a given squad who scored a goal during the season.")
        col6.markdown("_________________________________________________________________________")
        col6.markdown("The bar chart below allows one to analyze which players are over or under performing their expected goals metric within a squad.")
        col7.pyplot(fig1)
        figs.append(fig1)
        col7.markdown("The donut chart above includes a cumulative breakdown of a team’s shot outcome.")
        
        
        goal_dist = mergedPlayer_finaldf['Goal'] - mergedPlayer_finaldf['xG'] 
        
        fig2, ax = plt.subplots(figsize=[8,8])
        ax = sns.barplot(x=mergedPlayer_finaldf['Goal'] - mergedPlayer_finaldf['xG'], y='Player', data=mergedPlayer_finaldf, ax=ax)
        ax.set(xlabel='xG Difference')
        plt.title("xG Difference from Expectation", fontsize=16, fontfamily='serif')
        figs.append(fig2)
        
        
        #####SHOT MAP
        
        shotOutcomesVal = shot_df_split_new['shot_outcome'].unique()
        
        shotOutcomeOption = np.insert(shotOutcomesVal,0,'All')
        
        col7.markdown("_____________________________________________________________________________")
        col7.markdown("This map below allows one to visualize shot outcomes in relation to shot location for the squad.")
        
        shotOutcomeOption = col7.selectbox("Choose shot Type", shotOutcomeOption)
        
        def shotOutcomeGraph(shotOut):
        
            if shotOut == 'All':
            
                pitch_st = Pitch(pitch_type='statsbomb', half = True, pitch_color='#c7d5cc', line_color='white')
                fig_st, ax_st = pitch_st.draw(figsize=(8, 8), constrained_layout=True, tight_layout=False)
                
                plt.scatter(shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal']['x'],shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal']['y'],
                s =np.sqrt(shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal']["shot_statsbomb_xg"])*100 , marker = 'o', facecolor='orange',edgecolor='black', alpha=0.9, label = 'Goal')
                plt.title(f"{teamSelect} Shot Map")
                
                pitch_st.scatter(shot_df_split_new[shot_df_split_new['shot_outcome']!='Goal']['x'],shot_df_split_new[shot_df_split_new['shot_outcome']!='Goal']['y'], 
                s=np.sqrt(shot_df_split_new[shot_df_split_new['shot_outcome']!='Goal']['shot_statsbomb_xg'])*100, marker='o', alpha=0.6,label = 'Shots', edgecolor='black', facecolor='grey', ax=ax_st)
                ax_st.legend(loc='lower right')
                ax_st.text(63,70,'Goals : '+str(len(shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal'])), weight='bold', size=15)
                ax_st.text(63,74,f"xG : {round(sum(shot_df_split_new['shot_statsbomb_xg']),2)}", weight='bold', size=15)
                ax_st.text(63,78,'Total Shots : '+str(len(shot_df_split_new)), weight='bold', size=15)
                col9.pyplot(fig_st)
                return fig_st
            
            
        
            elif shotOut == 'Goal':
                
                pitch_st = Pitch(pitch_type='statsbomb', half = True, pitch_color='#c7d5cc', line_color='white')
                fig_st, ax_st = pitch_st.draw(figsize=(8, 8), constrained_layout=True, tight_layout=False)
                
                plt.scatter(shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal']['x'],shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal']['y'],
                s =np.sqrt(shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal']["shot_statsbomb_xg"])*100 , marker = 'o', facecolor='orange',edgecolor='black', alpha=0.9, label = 'Goal')
                
                plt.title(f"{teamSelect} Shot Map")
                ax_st.legend(loc='lower right')
                ax_st.text(63,70,'Goals : '+str(len(shot_df_split_new[shot_df_split_new['shot_outcome']=='Goal'])), weight='bold', size=15)
                #ax_st.text(63,74,f"xG : {round(sum(shot_df_split_new['shot_statsbomb_xg']),2)}", weight='bold', size=15)
                ax_st.text(63,78,'Total Shots : '+str(len(shot_df_split_new)), weight='bold', size=15)
                col9.pyplot(fig_st)
                return fig_st
        
            
            else:
            
                pitch_st = Pitch(pitch_type='statsbomb', half = True, pitch_color='#c7d5cc', line_color='white')
                fig_st, ax_st = pitch_st.draw(figsize=(8, 8), constrained_layout=True, tight_layout=False)
                
                plt.scatter(shot_df_split_new[shot_df_split_new['shot_outcome']==f'{shotOut}']['x'],shot_df_split_new[shot_df_split_new['shot_outcome']==f'{shotOut}']['y'], 
                s=np.sqrt(shot_df_split_new[shot_df_split_new['shot_outcome']==f'{shotOut}']['shot_statsbomb_xg'])*100, marker='o', facecolor='grey' ,edgecolor='black', alpha=0.6,label = 'Shots' )
                
                plt.title(f"{teamSelect} Shot Map")
                ax_st.legend(loc='lower right')
                ax_st.text(63,70,f'{shotOut} Shots : '+str(len(shot_df_split_new[shot_df_split_new['shot_outcome']==f'{shotOut}'])), weight='bold', size=15)
                #ax_st.text(63,74,f"xG : {round(sum(shot_df_split_new['shot_statsbomb_xg']),2)}", weight='bold', size=15)
                ax_st.text(63,78,'Total Shots : '+str(len(shot_df_split_new)), weight='bold', size=15)
                col9.pyplot(fig_st)
                return fig_st
           
        col8, col9 = st.columns((2))
        
        #col9.markdown("The below map allows one to visualize shot outcomes in relation to shot location for the squad.")
        fig_shotmap = shotOutcomeGraph(shotOutcomeOption)
            
        col8.pyplot(fig2)
        #figs.append(fig2)
        figs.append(fig_shotmap)
        
        
        
        #### PLAYER STATS TABLE
        
        
                
        col8.markdown("**Shot Performance Overview**")
        col8.markdown("This table provides users with the general shooting statistics of a squad throughout the 2018/19 season.")
        
        top_goal_df = shot_df_split_new[(shot_df_split_new['shot_outcome'] == 'Goal' )] 

        num1 = shot_df_split_new.columns.get_loc("shot_outcome")
        
        for i in range(len(top_goal_df)) :
            if goal_df.iloc[i,num1] == 'Goal' :
                        top_goal_df['Goal'] =1
            else:
                top_goal_df['Goal'] =0        
        
        player_goals = top_goal_df.groupby(['player'])['Goal'].sum()
        player_goals = player_goals.to_frame().reset_index()
        player_goals = player_goals.sort_values('Goal', ascending =False)
        
        
        player_xg = shot_df_split_new.groupby(['player'])['shot_statsbomb_xg'].sum()
        player_xg = player_xg.to_frame().reset_index()
        player_xg = player_xg.sort_values('shot_statsbomb_xg', ascending =False)
        
        player_stats_df = pd.merge(player_xg,player_goals, on="player",  how='left')
        player_stats_df = player_stats_df.fillna(0)
        player_stats_df['shot_statsbomb_xg'] = round(player_stats_df.shot_statsbomb_xg,2)
                
        player_stats_df['Goal p/90'] = round(mergedPlayer_df.Goal/mergedPlayer_df['90s'],2)
        
        player_stats_df['xG p/90'] = round(player_stats_df.shot_statsbomb_xg/mergedPlayer_df['90s'],2)
        
        player_stats_df['xG Difference'] = round(mergedPlayer_df.Goal- player_stats_df.shot_statsbomb_xg,2)
        
        player_stats_df = player_stats_df.fillna(0)        

        
        total_shot_df = shot_df_split_new 
        
        
        for i in range(len(total_shot_df)):
            total_shot_df['shots'] =1
                
        
        total_shot_df = total_shot_df.groupby(['player'])['shots'].sum()
        total_shot_df = total_shot_df.to_frame().reset_index()
        total_shot_df = total_shot_df.sort_values('shots', ascending =False)
        
        player_stats_df = pd.merge(player_stats_df,total_shot_df, on="player",  how='left')
        player_stats_df = player_stats_df.fillna(0)
        
        player_stats_df["Conversion Rate%"] = round((player_stats_df["Goal"]/player_stats_df["shots"])*100,2)
        
        onT_df = shot_df_split_new[(shot_df_split_new['shot_outcome'] == 'Goal' ) | (shot_df_split_new['shot_outcome'] == 'Saved')  | (shot_df_split_new['shot_outcome'] == 'Saved to Post') ]
        
        for i in range(len(onT_df)) :
            onT_df["Shots on Target"] = 1
        
        onT_df = onT_df.groupby(['player'])['Shots on Target'].sum()
        onT_df = onT_df.to_frame().reset_index()
        onT_df = onT_df.sort_values('Shots on Target', ascending =False)
        
        player_stats_df = pd.merge(player_stats_df,onT_df, on="player",  how='left')
        player_stats_df = player_stats_df.fillna(0)        
        
        player_stats_df["SoT %"] = round((player_stats_df["Shots on Target"]/player_stats_df["shots"])*100,2)
        #player_stats_df = player_stats_df.drop(['Shots on Target'], axis=1)
        
        AgGrid(player_stats_df)
        
        
        
        
        
        
        ##EXPORT PDF 
        
        st.markdown("**Export Visualisations as Report**")
        export_as_pdf = st.button("Export as pdf")
            
        def create_download_link(val, filename):
            b64 = base64.b64encode(val)  # val looks like b'...'
            return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download file</a>'
        
        

        if export_as_pdf:
            pdf = FPDF()
            for fig in figs:
                pdf.add_page()
                with NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                    fig.savefig(tmpfile.name)
                    pdf.image(tmpfile.name, 10, 10, 200, 100)
            html = create_download_link(pdf.output(dest="S").encode("latin-1"), "report")
            st.markdown(html, unsafe_allow_html=True)
            
        
        
        #col9.pyplot(fig_st)
        
