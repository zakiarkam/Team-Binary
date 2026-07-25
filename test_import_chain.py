import numpy as np

print("1")

import xgboost

print("2")

X = np.random.rand(100,20)
y = np.random.randint(0,5,100)

model = xgboost.XGBClassifier(
    objective="multi:softprob",
    num_class=5,
    n_estimators=20,
)

print("3")

model.fit(X,y)

print("4")