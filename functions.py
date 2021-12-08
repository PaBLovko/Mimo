# -*- coding: utf-8 -*-

import requests
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
import seaborn as sns
import os
import datetime
import json


def get_key():
    with open("key.json", "r") as key_file:
        key = json.load(key_file)
    api_key = key["api_key_5"]
    return api_key

error_message = {200: 'OK', 400 : 'ERROR - Bad Request', 401 : 'ERROR - Unauthorised', 403 : 'ERROR - Forbidden',
                 404 : 'ERROR - Not Found', 405 : 'ERROR - Method Not Allowed', 500 : 'ERROR - Internal Server Error'}

def parameter_def(post_code, rad, min_beds, max_beds, search_type):
    """ search_type can only take two possible strings, 'sale' and 'rent'.
    It uses this to define the appropriate parameters for Zoopla.
    The aim is to make one API call per bedroom type, so this will create a list of parameters"""
    api_key = get_key()
    parameters = [ {'api_key' : api_key, 'postcode' : post_code, 'include_sold' : "yes", 'include_rented' : "yes",
                    'radius' : rad, 'listing_status' : search_type, 'minimum_beds' : i, 'maximum_beds' : i,
                    'summarised' : "yes", 'page_size' : 100} for i in range(min_beds, max_beds+1,1)]
    return parameters

def data_load(website, parameters, min_beds, max_beds, search_type):
    """ this uses the parameters dictionary defined in parameter_Def to make an API call to Zoopla.
    This then parses the json into a dataframe file """
    frames = []
    bedrooms = [i for i in range(min_beds, max_beds+1,1 )]
    for dic in parameters:
        dic_val = dict(dic)
        api_response = requests.get(website, dic_val)
        status_code = api_response.status_code
        if status_code != 200:
            print(error_message[status_code])
            break
        else:
            zoopla_json = api_response.json()
            json_data = zoopla_json['listing']
            data_frame = pd.DataFrame(json_data, list(range(1, len(json_data)+1)))
            try:
                data_frame = data_frame.loc[~(data_frame['price']==0)]
                data_frame = data_frame.apply(pd.to_numeric, errors='ignore')
                frames.append(data_frame)
            except KeyError:
                print("No ", search_type, " comps found for ", bedrooms[parameters.index(dic)])
    data_frame = frames[0]
    for i in range(1,len(frames),1):
        data_frame = pd.concat([data_frame, frames[i]], axis=0, ignore_index=True)
    return data_frame

def filter_bounds(dataframe):
    """ creates a Nx2 list of the upper and lower bounds, to be used in the automated filtering. """
    groups = dataframe.groupby('num_bedrooms')
    medians = groups['price'].quantile(0.5)
    q1s = groups['price'].quantile(0.25)
    q3s = groups['price'].quantile(0.75)
    IQRs = q3s - q1s
    ubs = medians + IQRs
    lbs = medians - IQRs
    bounds = list(zip(ubs,lbs))
    return bounds


def automatic_filter(dataframe, bounds, filter_flag,min_beds, max_beds):
    """This uses the earlier defined dataframe and bounds to automatically filter the data.
    Filter_flag is used to determine whether the user determines if a property is dropped or not"""
    upper_bounds = [val[0] for val in bounds]
    lower_bounds = [val[-1] for val in bounds]
    bedrooms = [i for i in range(min_beds, max_beds+1,1 )]
    i = 0
    j = 0
#    print(filter_flag)
    if filter_flag == "N":
        for index, row in dataframe.iterrows():
            bedroom_index = bedrooms.index(row['num_bedrooms'])
            if row['price'] > upper_bounds[bedroom_index]:
                i += 1 
                print("Anomalous high value found - showing information")
                print('Address - {address}, Price £{price} ,{beds} beds, Property Type: '
                      '{ptype}, Described as: {description}'.format(address = row['displayable_address'],
                                                                    price = row['price'],
                                                                    beds = row['num_bedrooms'],
                                                                    ptype = row['property_type'],
                                                                    description = row['description']))
                print('Do you want to keep this value?')
                var = input("Y/N: ")
                if var == 'N':
                    j += 1
                    dataframe.drop(index, inplace=True)
            elif row['price'] < lower_bounds[bedroom_index]:         
                i += 1 
                print("Anomalous low value found - showing information")
                print('Address - {address}, Price £{price} ,{beds} beds, Property Type: {ptype}, '
                      'Described as: {description}'.format(address = row['displayable_address'],
                                                           price = row['price'],
                                                           beds = row['num_bedrooms'],
                                                           ptype = row['property_type'],
                                                           description = row['description']))
                print('Do you want to keep this value?')
                var = input("Y/N: ")
                if var == 'N':
                    j += 1
                    dataframe.drop(index, inplace=True)
        if i == 0:            
            print('Filtering for sales complete, no anomalies found')
        else:
            print('Filtering complete. {i} anomalies found and {j} anomalies removed'.format( i=i, j=j))
    else:
        for index, row in dataframe.iterrows():
            bedroom_index = bedrooms.index(row['num_bedrooms'])
            if row['price'] > upper_bounds[bedroom_index]:
                i += 1 
                dataframe.drop(index, inplace=True)
            elif row['price'] < lower_bounds[bedroom_index]:         
                i += 1 
                dataframe.drop(index, inplace=True)        
        if i == 0:
            print('Filtering for sales complete, no anomalies found')
        else:
#                print(i)
#                print(j)
            print('Filtering complete. {i} anomalies removed'.format( i=i))    
    return dataframe

def mu_sigma(dataframe):
    """ This will return the means and the standard deviation for the different bedroom types for each dataset """
    group = dataframe.groupby('num_bedrooms')
    means = group['price'].mean()
    stds = group['price'].std()
    mu_sig = list(zip(means, stds))
    return mu_sig

def comps_values(mu_sigma, percentile):
    """This uses the mu_sigma list to create the comps values for all the different bedroom types"""
    comp_values = [round((norm.ppf(percentile, loc=val[0], scale=val[-1]))) for val in mu_sigma]                     
    return comp_values

def plot_title(post_code, radius, min_beds, max_beds, search_type):
    comps_flag = "Sales" if search_type == "sale" else "Rental"
    title = "{} Comps Analysis for {}-{} bedroom properties within a {} mile radius of {} {}".format(
        comps_flag, min_beds, max_beds, radius, post_code[:-3].upper(), post_code[-3:].upper())
    return title

def plot_boxwhisker(dataframe, title_string, search_type, post_code, mkdir_output, save_flag, current):
    values = dataframe.loc[:,['num_bedrooms', 'price']]
    plt.figure()
    sns.set(color_codes=True)
    sns.set_style("dark")
    sns.boxplot(x=values['price'], y=values['num_bedrooms'], orient="h", palette="Set2")
    xlabel = "Sales Value (£)" if search_type == "sale" else "Weekly Rent (£)"
    plt.xlabel(xlabel)
    plt.ylabel('Bedrooms')
    plt.title(title_string)
    ax = plt.gca()
    ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
#    ax.get_xaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    path_name = mkdir_output[0]
    plot_type = "BW_" + search_type + path_name
    if save_flag == "Y":
        save_plots(post_code, plot_type,mkdir_output, current)
    return

def plot_seaborn_dist(dataframe,minimum_beds, maximum_beds, title_string, search_type, post_code, mkdir_output,
                      save_flag, current):
    values = dataframe.loc[:,['num_bedrooms', 'price']]
    bedrooms = [i for i in range(minimum_beds, maximum_beds+1,1 )]
    bedroom_values = [values.loc[lambda values: values['num_bedrooms'] == i,:] for i in bedrooms]
    plt.figure()
    for vals in bedroom_values:
#        sns.kdeplot(vals, shade=False)
#        plt.plot(vals)
        sns.distplot(vals['price'], hist = False, kde= True, kde_kws = {'shade' : True, 'linewidth': 3})
#        print(type(vals))
#        print(len(vals))
#        print(type(vals[-1]))
    xlabel = "Sales Value (£)" if search_type == "sale" else "Weekly Rent (£)"
    plt.xlabel(xlabel)
    plt.ylabel('Bedrooms')
    plt.legend(bedrooms)
    plt.title(title_string)
    ax = plt.gca()
    ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    ax.axes.get_yaxis().set_visible(False)
    path_name = mkdir_output[0]
    plot_type = "Dist_" + search_type + path_name
    if save_flag == "Y":
        save_plots(post_code, plot_type, mkdir_output, current)
    return

def make_dirs(post_code):
    # print("The current working directory is {}".format(os.getcwd()))
    os.chdir("../Mimo")
    # print("The new working directory is {}".format(os.getcwd()))
    path_name = post_code[:-3].upper() + "_" + post_code[-3:].upper() + "_Comps"
    try:
        os.mkdir(path_name)
    except FileExistsError:
        pass
    os.chdir(path_name)
    date_string = date_str()
    try:    
        os.mkdir(date_string)
    except FileExistsError:
        pass
    os.chdir(date_string)
    try:
        os.mkdir("Scripts")
    except FileExistsError:
        pass
    os.chdir("Scripts")
    return path_name, date_string 

def date_str():
    now = datetime.datetime.now()
    date_str = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[now.month-1] + "_" + str(now.year)[-2:]
    return date_str
    
def save_plots(post_code, plot_type, mkdir_outputs, current):
    os.chdir(r''+current)
    os.chdir("../Mimo")
    os.chdir(mkdir_outputs[0])
    os.chdir(mkdir_outputs[1])
    title_string = plot_type + ".png"
    plt.savefig(title_string)
    os.chdir("Scripts")
    return 

def full_comps_calc(website, post_code, radius, minimum_beds, maximum_beds, comps_type, percentile, filter_flag,
                    save_flag):
    """This will run the full comps calculation, and plot it. """
    parameters = parameter_def(post_code, radius, minimum_beds, maximum_beds, comps_type)
    data_frame = data_load(website, parameters, minimum_beds, maximum_beds, comps_type)
    bounds = filter_bounds(data_frame)
    filtered_data_frame = automatic_filter(data_frame, bounds, filter_flag, minimum_beds, maximum_beds)
    mean_std = mu_sigma(filtered_data_frame)
    comps = comps_values(mean_std, percentile)
    time_multiplier = 1 if comps_type == "sale" else 4  #time change - weekly -> monthly
    digit_flag = -4 if comps_type == "sale" else -1     # rounding 
    comps = ["{:,}".format(int(round(time_multiplier*val,digit_flag))) for val in comps]  #giving the monthly rental, rounding it and adding commas 
    print('The {} comps are:'.format(comps_type), comps) 
    title = plot_title(post_code, radius, minimum_beds, maximum_beds, comps_type)
    current = os.getcwd()
    mkdir_outs = make_dirs(post_code)
    plot_boxwhisker(filtered_data_frame, title, comps_type, post_code, mkdir_outs, save_flag, current)
    plot_seaborn_dist(filtered_data_frame, minimum_beds, maximum_beds, title, comps_type, post_code, mkdir_outs,
                      save_flag, current)
    if save_flag == "Y":
        save_to_csv(filtered_data_frame, comps_type, mkdir_outs, current)
    return comps

def save_to_csv(dataframe, search_type, mkdir_output, current):
    path_name = mkdir_output[0]
    date_string = mkdir_output[1]
    os.chdir(r''+current)
    os.chdir("../Mimo/"+path_name)
    os.chdir(date_string)
    os.chdir("Scripts")
    title_string = "Comps_" + search_type + ".csv"
    dataframe.to_csv(title_string, encoding='utf-8', index=False)    
    return
