# -*- coding: utf-8 -*-
"""2020320078_컴퓨터학과 한지상.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1T58m97h_ilBmC3ZGttqT9bPCr49OzZa8
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import torchvision
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re
import os

import nltk
from nltk.tokenize import word_tokenize
from nltk import PorterStemmer
from nltk import WordNetLemmatizer
from nltk.corpus import stopwords

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split

from tqdm import tqdm_notebook as tqdm

data = pd.read_csv('./data/train.csv')
test = pd.read_csv('./data/test.csv')
print(data.shape, test.shape)

data.dropna(inplace=True)
test.dropna(inplace=True)

remove_non_alphabets =lambda x: re.sub(r'[^a-zA-Z]',' ',x)

tokenize = lambda x: word_tokenize(x)

ps = PorterStemmer()
stem = lambda w: [ ps.stem(x) for x in w ]

lemmatizer = WordNetLemmatizer()
leammtizer = lambda x: [ lemmatizer.lemmatize(word) for word in x ]

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
data['mail'] = data['mail'].apply(remove_non_alphabets)
test['mail'] = test['mail'].apply(remove_non_alphabets)

data['mail'] = data['mail'].apply(tokenize)
test['mail'] = test['mail'].apply(tokenize)

data['mail'] = data['mail'].apply(stem)
test['mail'] = test['mail'].apply(stem)

data['mail'] = data['mail'].apply(leammtizer)
test['mail'] = test['mail'].apply(leammtizer)

data['mail'] = data['mail'].apply(lambda x: ' '.join(x))
test['mail'] = test['mail'].apply(lambda x: ' '.join(x))    

#data.head()
#test.head()

max_words = 40000
#cv = CountVectorizer(max_features=max_words, stop_words='english')
from sklearn.feature_extraction.text import TfidfVectorizer
cv = TfidfVectorizer(max_features=max_words, stop_words='english', ngram_range=(1,2))

train_vectors = cv.fit_transform(data['mail']).toarray()
test_vectors = cv.transform(test['mail']).toarray()

print(train_vectors.shape)
print(test_vectors.shape)

x_train, x_test, y_train, y_test = train_test_split(train_vectors, np.array(data['label']))

class Classifier(nn.Module):
    def __init__(self):
        super(Classifier, self).__init__()
        self.linear1 = nn.Linear(40000, 10000)
        self.linear2 = nn.Linear(10000, 100)
        self.linear3 = nn.Linear(100, 10)
        self.linear4 = nn.Linear(10, 2)
        
    def forward(self, x):
        x = F.relu(self.linear1(x))
        x = F.relu(self.linear2(x))
        x = F.relu(self.linear3(x))
        x = self.linear4(x)
        return x

model = Classifier().cuda()

class EarlyStopping:
    def __init__(self, patience=7, verbose=False, delta=0, path='checkpoint.pt'):
        self.patience = patience
        self.verbose = verbose
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.val_loss_min = np.Inf
        self.delta = delta
        self.path = path

    def __call__(self, val_loss, model):

        score = -val_loss

        if self.best_score is None:
            self.best_score = score
            self.save_checkpoint(val_loss, model)
        elif score < self.best_score + self.delta:
            self.counter += 1
            print(f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.save_checkpoint(val_loss, model)
            self.counter = 0

    def save_checkpoint(self, val_loss, model):
        if self.verbose:
            print(f'Validation loss decreased ({self.val_loss_min:.6f} --> {val_loss:.6f}).  Saving model ...')
        torch.save(model.state_dict(), self.path)
        self.val_loss_min = val_loss

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(params=model.parameters() , lr=0.01)

x_train = Variable(torch.from_numpy(x_train)).float()
y_train = Variable(torch.from_numpy(y_train)).long()
x_test = Variable(torch.from_numpy(x_test)).float()
y_test = Variable(torch.from_numpy(y_test)).long()

epochs = 100
model.train()
# loss_values = []
x_train = x_train.cuda()
y_train = y_train.cuda()
x_test = x_test.cuda()
y_test = y_test.cuda()

def train_model(model, x_train, y_train, x_test, y_test, criterion, optimizer, epochs):
    loss_values = []
    early_stopping = EarlyStopping(patience = 20, verbose = True)
    flag = 0

    for epoch in tqdm(range(epochs)):
        if flag == 1:
            break
        print('Epoch {}/{}'.format(epoch+1, epochs))
        print('---------------------------')
        
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()
            
            epoch_loss = 0.0
            epoch_corrects = 0
            
            if(epoch == 0) and (phase == 'train'):
                continue
            
            optimizer.zero_grad()
            
            with torch.set_grad_enabled(phase=='train'):
                if(phase == 'train'):
                    output = model(x_train)
                    loss = criterion(output, y_train)
                    loss.backward()
                    optimizer.step()
                    
                    pred = torch.max(output, 1)[1].eq(y_train).sum()
                    acc = (pred * 100.0 / len(x_train)).cpu()
                    print('{} Loss: {:f} Acc: {:f}'.format(phase, loss.item(), acc.numpy()))
                    
                else:
                    output = model(x_test)
                    loss = criterion(output, y_test)
                    loss_values.append(loss.item())
                    
                    pred = torch.max(output, 1)[1].eq(y_test).sum()
                    acc = (pred * 100.0 / len(x_test)).cpu()
                    print('{} Loss: {:f} Acc: {:f}'.format(phase, loss.item(), acc.numpy()))
                    early_stopping(loss.item(), model)

                    if early_stopping.early_stop:
                        print("Early stopping")
                        flag = 1
                        break

    model.load_state_dict(torch.load('checkpoint.pt'))
    return model, loss_values

model, loss_values = train_model(model, x_train, y_train, x_test, y_test, criterion, optimizer, epochs)

plt.plot(loss_values)
plt.title('Val Loss vs Epochs')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend(['Loss'])
plt.show()
print(loss_values)

# model.load_state_dict(torch.load('tfidf40000_state.pt')) 

model.eval()
x_test = x_test.cuda()
y_test = y_test.cuda()
with torch.no_grad():
    y_pred = model(x_test)
    loss = criterion(y_pred, y_test)
    pred = torch.max(y_pred, 1)[1].eq(y_test).sum()
    print ("Accuracy : {}%".format(100*pred/len(x_test)))
loss

# f1 score, accuracy_score, precision_score, recall_score, confusion_matrix
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score, confusion_matrix
print("f1_score : {}" .format(f1_score(y_test.cpu(), torch.max(y_pred, 1)[1].cpu())))
print("accuracy_score : {}" .format(accuracy_score(y_test.cpu(), torch.max(y_pred, 1)[1].cpu())))
print("precision_score : {}" .format(precision_score(y_test.cpu(), torch.max(y_pred, 1)[1].cpu())))
print("recall_score : {}" .format(recall_score(y_test.cpu(), torch.max(y_pred, 1)[1].cpu())))
print("confusion_matrix : {}" .format(confusion_matrix(y_test.cpu(), torch.max(y_pred, 1)[1].cpu())))

from sklearn.metrics import classification_report
print(classification_report(y_test.cpu(), torch.max(y_pred, 1)[1].cpu()))

x_pred = Variable(torch.from_numpy(test_vectors)).float()

model.eval()
x_pred=x_pred.cuda()
with torch.no_grad():
    y_pred = model(x_pred)

#y_pred

result = torch.max(y_pred, 1)[1]

print(result)

result = result.tolist()

f = open("./onground.csv", "w")
f.write("id"+','+"label"+'\n')
for id, label in enumerate(result):
    f.write(str(id)+','+str(label)+'\n')
    

f.close()



