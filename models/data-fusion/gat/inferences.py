import numpy as np
import pandas as pd
import json
import argparse
from itertools import combinations
from utils import *
from models import *


def main():
    
    ## parameters
    print('Load Parameters...')
    parser = argparse.ArgumentParser()
    parser.add_argument('parameter_path')
    opt = parser.parse_args()
    
    ## unload parameters
    parameter_path = opt.parameter_path.lower()
    with open(parameter_path) as json_file:
        parameters = json.load(json_file)
    data_path = parameters['data_path']
    batch_size = parameters['batch_size']
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    ## inference
    print('Inferencing...')
    names = ['puma', 'nta']
    supplement_portions = parameters['supplement_portions']
    all_losses = []
    for low_res_name, super_res_name in combinations(names, 2):
        ## load data
        print('===================================')
        print(f'{low_res_name} -> {super_res_name}...')
        print('===================================')
        losses = []

        for supplement_portion in supplement_portions:

            parameters['supplement_portion'] = supplement_portion
            
            ## load data
            dataset_train, _, dataset_test, X_max = load_data(low_res_name, super_res_name, parameters)
            linkage = dataset_train.linkage
            super_adj = dataset_train.adj_super.to(device)
            
            ## load model
            model = GraphSR(linkage, super_adj).to(device)
            criterion = nn.L1Loss().to(device)
            model.load_state_dict(torch.load(f'model_state/graphSR_{low_res_name}_{super_res_name}_{supplement_portion}'))

            ## pred
            loss, _, _, _ = evaluation(model, criterion, device, batch_size, dataset_test)
            losses.append(loss*X_max)
        
        all_losses.append(losses)

    losses = pd.DataFrame(np.array(all_losses),
                          columns=['propotion_0.1', 'propotion_0.5', 'propotion_1'],
                          index=['puma_nta'])
    losses.to_csv('inferences/results.csv')
    
    print('Done...')
    
if __name__ == "__main__":
    main()