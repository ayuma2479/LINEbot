import pandas as pd
import numpy as np



train = pd.read_csv("train.csv")
test = pd.read_csv("test.csv")

train.head(20)

test.describe()
train.describe()

train_isnull = train.isnull()
train_isnull.sum()

def kesson_hyou(df):
    null_sum = df.isnull().sum()
    percent = 100 * null_sum / len(df)
    kesson_table = pd.concat([null_sum,percent],axis=1)
    kesson_code = kesson_table.rename(columns = {0:'欠損数', 1:'%'})
    return kesson_code


kesson_hyou(train)

train['Age'] = train['Age'].fillna(train['Age'].median())
train['Embarked'] = train['Embarked'].fillna("S")
test['Age'] = test['Age'].fillna(test['Age'].median())
test.Fare[152] = test.Fare.median()

kesson_hyou(test)

train['Sex'][train['Sex'] == "male"] = 0
train['Sex'][train['Sex'] == "female"] = 1
train['Embarked'][train['Embarked'] == "S" ] = 0
train['Embarked'][train['Embarked'] == "C" ] = 1
train['Embarked'][train['Embarked'] == "Q"] = 2

train.head(10)

test['Sex'][test['Sex'] == "male"] = 0
test['Sex'][test['Sex'] == "female"] = 1
test['Embarked'][test['Embarked'] == "S" ] = 0
test['Embarked'][test['Embarked'] == "C" ] = 1
test['Embarked'][test['Embarked'] == "Q"] = 2

train.head(10)

from sklearn import tree

# 「train」の目的変数と説明変数の値を取得
target = train["Survived"].values
featuers = train[["Pclass","Age","Sex","Fare", "SibSp", "Parch", "Embarked"]].values

#ランダムフォレスト
max_depth = 10
min_sample_split = 5
my_tree = tree.DecisionTreeClassifier(max_depth = max_depth, min_samples_split = min_sample_split, random_state = 1)
my_tree = my_tree.fit(featuers,target)


test_featuers = test[["Pclass","Age","Sex","Fare", "SibSp", "Parch", "Embarked"]].values

my_prediction_tree = my_tree.predict(test_featuers)
PassengerID = np.array(test["PassengerId"]).astype(int)
my_solution_tree = pd.DataFrame(my_prediction_tree, PassengerID, columns = ['Survived'])
my_solution_tree.to_csv("my_tree_1.csv", index_label = ["PassengerID"])

#files.download("my_tree_1.csv")