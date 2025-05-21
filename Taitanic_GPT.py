# ===== Titanic 80%以上安定テンプレート =====

import pandas as pd
import numpy as np
from sklearn.model_selection import cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBClassifier

# --- データ読み込み ---
train = pd.read_csv("train.csv")
test = pd.read_csv("test.csv")
test_id = test['PassengerId']
df = pd.concat([train, test], sort=False)

# --- 敬称 (Title) 抽出 ---
df['Title'] = df['Name'].str.extract(' ([A-Za-z]+)\.', expand=False)
df['Title'] = df['Title'].replace(['Lady','Countess','Capt','Col','Don','Dr','Major','Rev','Sir','Jonkheer','Dona'], 'Rare')
df['Title'] = df['Title'].replace({'Mlle': 'Miss', 'Ms': 'Miss', 'Mme': 'Mrs'})

# --- Surname & FamilyGroup ---
df['Surname'] = df['Name'].str.split(',').str[0].str.strip()
df['FamilyGroup'] = df.groupby('Surname')['Surname'].transform('count')

# --- Age 補完（RF回帰） ---
age_df = df[['Age','Pclass','Sex','Parch','SibSp']]
age_df = pd.get_dummies(age_df)
known_age = age_df[age_df.Age.notnull()].values
unknown_age = age_df[age_df.Age.isnull()].values
X_age = known_age[:, 1:]
y_age = known_age[:, 0]
rfr = RandomForestRegressor(random_state=0, n_estimators=100, n_jobs=-1)
rfr.fit(X_age, y_age)
df.loc[df['Age'].isnull(), 'Age'] = rfr.predict(unknown_age[:, 1:])

# --- Embarked / Fare 補完 ---
df['Embarked'] = df['Embarked'].fillna('S')
fare_median = df[(df['Embarked'] == 'S') & (df['Pclass'] == 3)]['Fare'].median()
df['Fare'] = df['Fare'].fillna(fare_median)

# --- Cabin ラベル化 ---
df['Cabin_label'] = df['Cabin'].apply(lambda x: 0 if pd.isnull(x) else 1)

# --- IsAlone, FamilySize ---
df['FamilySize'] = df['SibSp'] + df['Parch']
df['IsAlone'] = (df['FamilySize'] == 0).astype(int)

# --- Ticket グループ化 ---
ticket_counts = df['Ticket'].value_counts()
df['TicketGroup'] = df['Ticket'].map(ticket_counts)
df['Ticket_label'] = 1
df.loc[(df['TicketGroup'] >= 2) & (df['TicketGroup'] <= 4), 'Ticket_label'] = 2
df.loc[df['TicketGroup'] >= 5, 'Ticket_label'] = 0

# --- Survived/Dead グループ反映 ---
train = df[df['Survived'].notnull()]
test = df[df['Survived'].isnull()]
female_child = train[(train['Sex'] == 'female') & (train['Age'] <= 16) & (train['FamilyGroup'] >= 2)]
male_adult = train[(train['Sex'] == 'male') & (train['Age'] > 16) & (train['FamilyGroup'] >= 2)]
Survived_list = female_child.groupby('Surname')['Survived'].mean()[lambda x: x==1.0].index
Dead_list = male_adult.groupby('Surname')['Survived'].mean()[lambda x: x==0.0].index
df.loc[(df['Surname'].isin(Survived_list)) & (df['Survived'].isnull()), ['Sex','Age','Title']] = ['female', 5, 'Miss']
df.loc[(df['Surname'].isin(Dead_list)) & (df['Survived'].isnull()), ['Sex','Age','Title']] = ['male', 28, 'Mr']

# --- 特徴量選択 ---
df = df[['Survived','Pclass','Sex','Age','Fare','Embarked','Title','Cabin_label','IsAlone','Ticket_label']]
df = pd.get_dummies(df)

# --- train / test 分割 ---
train = df[df['Survived'].notnull()]
test = df[df['Survived'].isnull()].drop('Survived', axis=1)
X = train.drop('Survived', axis=1).values
y = train['Survived'].astype(int).values
test_x = test.values

# --- モデル構築（XGBoost） ---
clf = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.05,
    random_state=10,
    use_label_encoder=False,
    eval_metric='logloss'
)
pipeline = make_pipeline(clf)
pipeline.fit(X, y)

# --- 評価（CVスコア） ---
cv = cross_validate(pipeline, X, y, cv=10)
print('CV mean score:', np.mean(cv['test_score']))

# --- 予測・提出ファイル作成 ---
pred = pipeline.predict(test_x).astype(int)
submission = pd.DataFrame({'PassengerId': test_id, 'Survived': pred})
submission.to_csv('submission_80plus.csv', index=False)
