import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim.lr_scheduler import StepLR
from torch.nn.parameter import Parameter
from torch.nn.modules.module import Module
from sklearn.model_selection import train_test_split
from tqdm import tqdm

class taxi_data(torch.utils.data.Dataset):
    
    """
    Prepare taxi data
    """
    
    def __init__(self, 
                 att_low, 
                 att_super, 
                 adj_low,
                 adj_super,
                 linkage):
        super(taxi_data, self).__init__()
        self.att_low = att_low
        self.att_super = att_super
        self.adj_low = adj_low
        self.adj_super = adj_super
        self.linkage = linkage
        
    def __getitem__(self, index):
        
        ## batch attributes
        batch_att_low = self.att_low[index]
        batch_att_super = self.att_super[index]
        
        return batch_att_low, batch_att_super, self.adj_low, self.adj_super, self.linkage

    def __len__(self):
        return len(self.att_low)
    


def load_data(low_res_name, super_res_name, parameters):
    
    """
    Function to load datasets
    
    Arg:
        - parameters: parameter json file
    """
    
    ## data path
    data_path = parameters['data_path']
    att_low_res_path = data_path+'attributes/'+low_res_name+'.npy'
    adj_low_res_path = data_path+'adjacencies/'+low_res_name+'.npy'
    att_super_res_path = data_path+'attributes/'+super_res_name+'.npy'
    adj_super_res_path = data_path+'adjacencies/'+super_res_name+'.npy'
    linkage_path = data_path+'linkages/'+low_res_name+'_'+super_res_name+'.npy'
    
    ## load data
    X_low = torch.from_numpy(np.load(att_low_res_path)).float()
    X_super = torch.from_numpy(np.load(att_super_res_path)).float()
    A_low = torch.from_numpy(np.load(adj_low_res_path)).float()
    A_super = torch.from_numpy(np.load(adj_super_res_path)).float()
    linkage = torch.from_numpy(np.load(linkage_path)).float()
    
    ## min-max normalization: min=0
    X_max = torch.max(torch.max(X_low), torch.max(X_super))
    X_low = X_low/X_max
    X_low = X_low[:,:,None]
    X_super = X_super/X_max
    X_super = X_super[:,:,None]

    ## split train, val & test
    X_low_train, X_low_test, X_super_train, X_super_test = train_test_split(X_low, 
                                                                            X_super, 
                                                                            test_size=0.2, 
                                                                            random_state=1)
    X_low_train, X_low_val, X_super_train, X_super_val = train_test_split(X_low_train, 
                                                                          X_super_train, 
                                                                          test_size=0.1, 
                                                                          random_state=1)
    ## prepare data
    dataset_train = taxi_data(X_low_train, X_super_train, A_low, A_super, linkage)
    dataset_val = taxi_data(X_low_val, X_super_val, A_low, A_super, linkage)
    dataset_test = taxi_data(X_low_test, X_super_test, A_low, A_super, linkage)
    
    return dataset_train, dataset_val, dataset_test, X_max


def train(model, 
          criterion, 
          optimizer,
          device,
          batch_size, 
          dataset):
    
    """
    Function to train the model
    
    Arg:
        - model
        - criterion: loss function
        - optimizer
        - scheduler: learing rate updater
        - batch_size
        - dataset: training dataset
        
    """
    
    ## training  
    ## iterate through training dataset
    for i in range(0, len(dataset), batch_size):
        
        ## batch data
        indices = range(i, min(len(dataset), i+batch_size))        
        X_batch_low, X_batch_super, A_low, A_super, linkage = zip(*[dataset[i] for i in indices])
        X_batch_low = torch.stack(X_batch_low).to(device)
        X_batch_super = torch.stack(X_batch_super).to(device)
        A_low = A_low[0].to(device)
        A_super = A_super[0].to(device)
        linkage = linkage[0].to(device)
        
        ## prediction
        pred = model(X_batch_low)
        
        ## loss
        loss = criterion(X_batch_super, pred)
        
        ## back propogration
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

            
def evaluation(model, 
               criterion, 
               device,
               batch_size, 
               dataset):
    
        
    """
    Function to evaluate the model
    
    Arg:
        - model
        - criterion: loss function
        - batch_size
        - dataset: validation/test dataset
        
    """
    
    ## evaluation
    pred_super = []
    gt_super = []
    gt_low = []
    
    for i in range(0, len(dataset), batch_size):
        indices = range(i, min(len(dataset), i+batch_size))        
        X_batch_low, X_batch_super, A_low, A_super, linkage = zip(*[dataset[i] for i in indices])
        X_batch_low = torch.stack(X_batch_low).to(device)
        X_batch_super = torch.stack(X_batch_super).to(device)
        A_low = A_low[0].to(device)
        A_super = A_super[0].to(device)
        linkage = linkage[0].to(device)
        with torch.no_grad():
            pred = model(X_batch_low)
        pred_super.append(pred)
        gt_super.append(X_batch_super)
        gt_low.append(X_batch_low)
        
    pred_super = torch.cat(pred_super)
    gt_super = torch.cat(gt_super)
    gt_low = torch.cat(gt_low)
    loss = criterion(pred_super, gt_super).cpu().item()
    
    return loss, pred_super, gt_super, gt_low
    