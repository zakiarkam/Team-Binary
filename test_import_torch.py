import torch

print("torch imported")

import numpy as np

import xgboost

X = np.random.rand(100,20)
y = np.random.randint(0,5,100)

model = xgboost.XGBClassifier(
    objective="multi:softprob",
    num_class=5,
    n_estimators=20,
)

print("before fit")

model.fit(X,y)

print("after fit")