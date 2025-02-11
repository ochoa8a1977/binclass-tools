#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd

from sklearn.metrics import roc_curve, auc, precision_recall_curve, fbeta_score, confusion_matrix

import plotly.graph_objects as go
import plotly.express as px 
from plotly.subplots import make_subplots

from .utilities import _get_amount_matrix, _get_cost_matrix, _get_density_curve_data
from .utilities import get_amount_cost_df, get_invariant_metrics_df, get_confusion_matrix_and_metrics_df

from .thresholds import get_optimized_thresholds_df

def curve_PR_plot(true_y, predicted_proba, beta = 1, title = "Precision Recall Curve", show_display_modebar = True):
    
    """
    - Plots interactive Precision-Recall curve with plotly 
      displayng area under the PR curve value and ISO-Fbeta curves  
    - Returns the value of area under the PR curve
    
    Plot is constituted by: 
    - a linechart of the the Precision-Recall curve, 
    - a dashed baseline (representing the PR curve of a random classifier) 
    - four ISO-f1 curve 

    Parameters
    ----------
    true_y: sequence of ints
        True labels 
    predicted_proba: sequence of floats
        predicted probabilities for class 1
        (e.g. output from model.predict_proba(data)[:,1]) 
    beta: float > 0, default=1
        Determines the weight of recall in the combined f-score (used for Iso-Fbeta curves)
    title: str, default="Precision Recall Curve"
        The main title of the plot.
    show_display_modebar: bool, default=True
        Determines wether plotly displayModeBar will be shown
    
    Returns
    ----------   
    area_under_PR_curve: float
        value of area under the PR curve
    """
    main_title = f"<b>{title}</b>"
    
    if beta < 0:
        raise ValueError("beta should be >=0 in the F-beta score") 

    precision, recall, thresholds = precision_recall_curve(true_y, predicted_proba)
       
    listTr = thresholds.tolist()
    
    listFbeta = []
    
    for threshold in listTr:
        y_pred = [int(x >= threshold) for x in predicted_proba]
        F_beta_score = fbeta_score(true_y, y_pred, beta=beta, zero_division=0)
        listFbeta.append(F_beta_score)
        
    listTr.append(None)
    listFbeta.append(0)
    
    area_under_pr_curve = auc(recall, precision)
    
    baseline = len(true_y[true_y==1]) / len(true_y)
    
    curve_df = pd.DataFrame({"Thresholds": listTr,
                             "Recall":recall.tolist(),
                             "Precision":precision.tolist(),
                             "Fbeta":listFbeta})
    
    full_fig=px.line(curve_df, x="Recall", y="Precision", hover_data=["Thresholds", "Fbeta"], title=main_title)
    
    fbeta_hover_str = ' <br>F' + str(beta) +' score: %{customdata[1]:.4f} '
    
    full_fig.update_traces(hovertemplate='Threshold: %{customdata[0]:.4f} <br>Precision: %{y:.4f} <br>Recall: %{x:.4f} ' + fbeta_hover_str + '<extra></extra>')
    
    full_fig.update_traces(textposition="top center", name = f'PR Curve (AUC={area_under_pr_curve:.2f})') 

    f_scores = np.linspace(0.2, 0.8, num=4)
    
    for f_score in f_scores:
        x = np.linspace(0.01, 1)
        y = f_score * x / (x + beta * beta * (x - f_score))
        X = x[y >= 0]
        listX = X.tolist()
        Y = y[y >= 0]
        listY = Y.tolist()
        
        recall_precision_df=pd.DataFrame({'recall':listX,
                                          'precision':listY})
               
        iso_fig=px.line(recall_precision_df, x="recall", y="precision")
        
        iso_fig.update_traces(hovertemplate=[]) # no hover info displayed but keeps dashed lines
        iso_fig.update_traces(line_color='#4C78A8', line=dict(dash='dot'), line_width=0.8, 
                              legendgroup = 'iso_curves', name = 'ISO-f' + str(beta) + ' Curves',
                              showlegend  = False)
        
        full_fig.add_annotation(x=0.90, y=y[45] + 0.01, text="f"+ str(beta) + "={0:0.1f}".format(f_score),
                                showarrow=False,yshift=10)       

        full_fig.add_traces(list(iso_fig.select_traces()))
            
    #add baseline
    full_fig.add_trace(go.Scatter(line=dict(dash='dash', color = '#20313e'), 
                                  x=[-1, 2], y=[baseline, baseline], 
                                  mode='lines', name = 'Baseline'))
 
    full_fig.update_xaxes(range=[0.0, 1.03])
    full_fig.update_yaxes(range=[0.0, 1.03])
    
    full_fig['data'][0]['showlegend']= True  #pr curve
    full_fig['data'][1]['showlegend']= True  #first iso curve
    full_fig['data'][-1]['showlegend']= True #baseline
    
    full_fig.update_layout(legend=dict(yanchor="top", y=0.18, xanchor="left", x=0.03),
                           legend_font_size=9, 
                           width=550, height=550)
    
    full_fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))
    full_fig.show(config = dict(displayModeBar = show_display_modebar))
    
    return area_under_pr_curve

def curve_ROC_plot(true_y, predicted_proba, title = "Receiver Operating Characteristic Curve",  show_display_modebar = True):
    
    """
    - Plots interactive ROC curve with plotly 
      displayng area under the ROC curve value    
    - Returns the value of area under the ROC curve
    
    Plot is constituted by: 
    a linechart of the the ROC curve (true positive rate, or recall, against false positive rate) 
    and a dashed baseline (representing the ROC curve of a random classifier)

    Parameters
    ----------
    true_y: sequence of ints
        True labels 
    predicted_proba: sequence of floats
        predicted probabilities for class 1
        (e.g. output from model.predict_proba(data)[:,1]) 
    title: str, default="Receiver Operating Characteristic Curve"
        The main title of the plot.
    show_display_modebar: bool, default=True
        Determines wether plotly displayModeBar will be shown

    Returns
    ----------   
    area_under_ROC_curve: float
        value of area under the ROC curve
    """
    main_title = f"<b>{title}</b>"
    
    fpr, tpr, thresholds = roc_curve(true_y, predicted_proba)
    
    area_under_ROC_curve = auc(fpr, tpr)
    
    curve_df = pd.DataFrame({"Thresholds": thresholds.tolist(),
                             "False Positive Rate":fpr.tolist(),
                             "True Positive Rate":tpr.tolist()})
    
    fig = px.line(curve_df, 
                  x="False Positive Rate", 
                  y="True Positive Rate",
                  title=main_title,
                  hover_data=["Thresholds"],
                  width=550, height=550)
    
    fig.update_traces(textposition = "top center",
                      name = f"ROC Curve (AUC={area_under_ROC_curve:.3f})")
    fig.update_traces(hovertemplate='Threshold: %{customdata:.4f} <br>False Positive Rate: %{x:.4f} <br>True Positive Rate: %{y:.4f}<extra></extra>')
    
    #add baseline
    fig.add_trace(go.Scatter(line=dict(dash='dash', color = '#20313e'), 
                                  x=[-1, 2], y=[-1, 2], 
                                  mode='lines', name = 'Baseline'))
    
    fig["data"][0]["showlegend"]= True
    fig["data"][1]["showlegend"]= True
    
    fig.update_layout(legend = dict(yanchor="top", y=0.18, xanchor="right", x=0.97), 
                      legend_font_size=9,
                      width=550, height=550) 
    
    fig.update_yaxes(range=[0.0, 1.03])
    fig.update_xaxes(range=[-0.03, 1.0]) 
    
    fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))

    fig.show(config = dict(displayModeBar = show_display_modebar))
    
    return area_under_ROC_curve

def predicted_proba_violin_plot(true_y, predicted_proba, threshold_step = 0.01, marker_size = 3, 
                                title = "Interactive Probabilities Violin Plot", show_display_modebar = True):
    
    """
    Plots interactive and customized violin plots of predicted probabilties with plotly, 
    one for each true class (0, 1), 
    displayng the distribution of each "confusion class" (TN, FP, FN, TP) for the selected threshold

    Plot is constituted by: 
    - two violin plots, one for each class (0, 1), that represent the distribution of the predicted probabilties
    - for each threshold, the distribution of the predicted probabilties for each "confusion class" (TN, FP, FN, TP)
    - slider that allows to select the threshold 

    Parameters
    ----------
    true_y: sequence of ints (0 or 1)
        True labels 
    predicted_proba: sequence of floats
        predicted probabilities for class 1
        (e.g. output from model.predict_proba(data)[:,1]) 
    threshold_step: float, default=0.01
        step between each classification threshold (ranging from 0 to 1) below which prediction label is 0, 1 otherwise
        each value will have a corresponding slider step
    marker_size: int, default=3
        Size of the points to be plotted
    title: str, default='Interactive Probabilities Violin Plot'
        The main title of the plot.
    show_display_modebar: bool, default=True
        Determines wether plotly displayModeBar will be shown
    """
    np.random.seed(11)
    
    data_df=pd.DataFrame({'class': true_y,
                          'pred': predicted_proba}).sort_values('pred')
    
    try:
        n_of_decimals = len(str(threshold_step).rsplit('.')[1])
    except:
        n_of_decimals = 4
    
    threshold_values = list(np.arange(0, 1 + threshold_step, threshold_step))
    
    main_title = f"<b>{title}</b><br>"
    
    # VIOLIN PLOT 
    full_fig=go.Figure(data=go.Violin(y=data_df['pred'], x=data_df['class'], line_color='#0D2A63', 
                                     meanline_visible=True, points=False, fillcolor=None, opacity=0.3, box=None,
                                     scalemode='count', showlegend = False))
    
    length_fig_list=[] # saves lenghts of strip figure data (can contain 1,2,3,4 classes)
    titles = {}
    
    choices = ['TN', 'FP', 'FN', 'TP']
    
    # STRIP PLOT
    for threshold in threshold_values:
        
        threshold_string = "thresh_" + str(round(threshold, n_of_decimals))
        
        
        conditions = [(data_df['class'] == 0) & (data_df['pred'] < threshold), 
                      (data_df['class'] == 0) & (data_df['pred'] >= threshold),
                      (data_df['class'] == 1) & (data_df['pred'] < threshold),
                      (data_df['class'] == 1) & (data_df['pred'] >= threshold)]
                                            
        data_df[threshold_string] = np.select(conditions, choices)
        
        count_class = data_df[threshold_string].value_counts()
        
        titles[threshold] = ''
        for x in count_class.index:
            titles[threshold] += x + ": " + str(count_class[x]) + ",  "
        
        titles[threshold] = titles[threshold][:-3] #removes last 3 char (2 spaces and comma)
                            
        # NOTE: px strip generates n plots, one for each color class (TN, FP, FN, TP) it finds)
        strip_points_fig = px.strip(data_df, x='class', y='pred', color=threshold_string, 
                                    color_discrete_map = {'FN':'#EF71D9', 'FP':'#EF553B',
                                                          'TP':'#00CC96', 'TN':'#636EFA'},
                                    log_y=True, width=550, height=550, hover_data = [data_df.index])
            
        strip_points_fig.update_traces(hovertemplate = 'Idx = %{customdata}<br>Class = %{x}<br>Pred = %{y}', jitter = 1, marker_size=marker_size)
        
        length_fig_list.append(len(strip_points_fig.data))
        
        for i in range(len(strip_points_fig.data)):
            strip_points_fig.data[i].visible=False
        
        full_fig.add_traces(list(strip_points_fig.select_traces()))
                
    full_fig.update_layout(legend_font_size=9.5, legend_itemsizing='constant', legend_traceorder='grouped', 
                           title=dict(text = main_title + '<span style="font-size: 13px;">' \
                                      + titles[threshold_values[0]] + '</span>',
                                      y = 0.965, yanchor = 'bottom'), 
                           width=550, height=550)
    
    full_fig.update_layout(margin=dict(l=40, r=40, t=60, b=40))
       
    # makes visible the first strip points figure
    for j in range(length_fig_list[0]):
        full_fig.data[j+1].visible = True #j+1 becouse figure 0 is the violin plot

    # STEPS AND SLIDER
    # Create and add slider
    steps = []
    idx = 1 # saves number of strip plots plotted
    
    for i in range(len(threshold_values)): 
        
        step = dict(
            method="update",
            args=[{"visible": [False] * len(full_fig.data)},
                  {"title": dict(text = main_title + '<span style="font-size: 13px;">' \
                                 + titles[threshold_values[i]] + '</span>',
                                 y = 0.965, yanchor = 'bottom')
                  },
                  #{"title": dict(text = main_title + '<span style="font-size: 13px;">' \
                   #                           + subtitle + titles[threshold] + '</span>', 
                   #                      y = 0.965, yanchor = 'bottom')}
                  {"value": "set "}],
            label = str(round(threshold_values[i], n_of_decimals)),
        )
            
        n_of_strip_plots = length_fig_list[i]
        step["args"][0]["visible"][0]= True  # Toggle first trace to "visible" (violin plots)

        for j in range(idx, idx+n_of_strip_plots):
            step["args"][0]["visible"][j] = True  # Toggle j'th trace to "visible"

        idx += n_of_strip_plots

        steps.append(step)

    sliders = [dict(
        active=0,
        currentvalue={"prefix": "Threshold: "},
        pad={"t": 50},
        steps=steps
    )]

    full_fig.update_layout(
        sliders=sliders
    )
            
    full_fig.update_xaxes(title_text = "True class")
    full_fig.update_yaxes(title_text = "Predicted probabilties")
    full_fig.show(config = dict(displayModeBar = show_display_modebar))
    
def predicted_proba_density_curve_plot(true_y, predicted_proba, 
                                       threshold_step = 0.01,  
                                       curve_type = 'kde',
                                       title = "Interactive Probabilities Density Plot", show_display_modebar = True):
    
    """
    Plots interactive and customized density curve of predicted probabilties with plotly, 
    one for each true class (0, 1), 
    with different colours for each "confusion class" (TN, FP, FN, TP) for the selected threshold

    Plot is constituted by: 
    - two kde density curves (or normal distribution curves, depending on the curve_type parameter), 
      one for each class (0, 1), that represent the distribution of the predicted probabilties.
      Colors of the curves will change depending on threshold, to underly each "confusion class" (TN, FP, FN, TP)
    - slider that allows to select the threshold 

    Parameters
    ----------
    true_y: sequence of ints (0 or 1)
        True labels 
    predicted_proba: sequence of floats
        predicted probabilities for class 1
        (e.g. output from model.predict_proba(data)[:,1]) 
    threshold_step: float, default=0.01
        step between each classification threshold (ranging from 0 to 1) below which prediction label is 0, 1 otherwise
        each value will have a corresponding slider step
    curve_type: {'kde', 'normal'},  default=kde 
        type of curve, either kernel density estimation or normal curve
    title: str, default="Interactive Probabilities Density Plot"
        The main title of the plot.
    show_display_modebar: bool, default=True
        Determines wether plotly displayModeBar will be shown
    """
    predicted_proba = np.array(predicted_proba)
    true_y = np.array(true_y)

    try:
        n_of_decimals = len(str(threshold_step).rsplit('.')[1])
    except:
        n_of_decimals = 4

    threshold_values = list(np.arange(0, 1+threshold_step, threshold_step)) #define thresholds array  
    main_title = f"<b>{title}</b><br>"

    # get density curve data
    x_N,  y_N = _get_density_curve_data([predicted_proba[true_y==0]], curve_type = curve_type)
    x_P,  y_P = _get_density_curve_data([predicted_proba[true_y==1]], curve_type = curve_type)

    # initialize figure
    fig = make_subplots(rows=2, cols=1,
                        vertical_spacing=0.05,
                        shared_xaxes = True)
    annotations={}
    titles = {}

    for threshold in threshold_values:

        y_pred = [int(x >= threshold) for x in predicted_proba]
        cf_matrix = confusion_matrix(true_y, y_pred)
        titles[threshold] = "TN: {0}, FP: {1}, FN: {2}, TP: {3}".format(*cf_matrix.ravel())

        # Select data for each confusion class
        first_idx_N = np.searchsorted(x_N, threshold)
        x_TN = x_N[:first_idx_N]
        y_TN = y_N[:first_idx_N]
        x_FP = x_N[first_idx_N:]
        y_FP = y_N[first_idx_N:]

        first_idx_P = np.searchsorted(x_P, threshold)
        x_FN = x_P[:first_idx_P]
        y_FN = y_P[:first_idx_P]
        x_TP = x_P[first_idx_P:]
        y_TP = y_P[first_idx_P:]

        # Add 4 density curves
        fig.add_trace(go.Scatter(x=x_TN, y=y_TN,
                                 mode='lines',
                                 name='TN',
                                 legendgroup = 'Negative',
                                 legendgrouptitle_text = 'Negative class',
                                 marker= {'color': '#636EFA'},
                                 fill = 'tozeroy',
                                 hovertemplate = "Probability: %{x:.4~}<br>Count: " + str(cf_matrix[0][0]),
                                 visible=False
                                ), row=1, col = 1
                     )

        fig.add_trace(go.Scatter(x=x_FP, y=y_FP,
                                 mode='lines',
                                 name='FP',
                                 legendgroup = 'Negative',
                                 legendgrouptitle_text = 'Negative class',
                                 marker= {'color': '#EF553B'},
                                 fill = 'tozeroy',
                                 hovertemplate = "Probability: %{x:.4~}<br>Count: " + str(cf_matrix[0][1]),
                                 visible=False
                                ), row=1, col = 1
                     )

        fig.add_trace(go.Scatter(x=x_FN, y=y_FN,
                                 mode='lines',
                                 name='FN',
                                 legendgroup = 'Positive',
                                 legendgrouptitle_text = 'Positive class',
                                 marker= {'color': '#EF71D9'},
                                 fill = 'tozeroy',
                                 hovertemplate = "Probability: %{x:.4~}<br>Count: " + str(cf_matrix[1][0]),
                                 visible=False
                                ), row=2, col = 1
                     )

        fig.add_trace(go.Scatter(x=x_TP, y=y_TP,
                                 mode='lines',
                                 name='TP',
                                 legendgroup = 'Positive',
                                 legendgrouptitle_text = 'Positive class',
                                 marker= {'color': '#00CC96'},
                                 fill = 'tozeroy',
                                 hovertemplate = "Probability: %{x:.4~}<br>Count: " + str(cf_matrix[1][1]),
                                 visible=False
                                ), row=2, col = 1
                     )

        max_y = max(list(y_N) + list(y_P)) # needed to set y axis domain

        # Add 2 threshold dotted line 
        fig.add_trace(go.Scatter(line=dict(dash='dash', color = '#20313e'), 
                                 x=[threshold, threshold], y=[-1, max_y*1.1],
                                 mode='lines + text', name = 'Threshold', 
                                 visible=False,
                                 legendgroup = 'threshold', showlegend = False), 
                      row = 'all', col = 1) #N.B: SINCE row = 'all' THIS WILL CREATE TWO SCATTER PLOTS (TWO FIG.DATA ENTRIES)

        fig['data'][-1]['showlegend'] = True 

        # Create annotation that will slide with threshold line
        annotations[threshold] = go.layout.Annotation(text="Predicted Negative        Predicted Positive",
                                                      y=0.5,
                                                      yref = "paper",
                                                      x=threshold,
                                                      visible=True,
                                                      font=dict(size=14),
                                                      showarrow=False) 


    # Create label for each quadrant
    TN_annotation = go.layout.Annotation(text="TN",
                                         y=0.97, yref = "y domain", x=0.025,
                                         visible=True,
                                         font=dict(size=14),
                                         showarrow=False) 

    FP_annotation = go.layout.Annotation(text="FP",
                                         y=0.97, yref = "y domain", x=0.975,
                                         visible=True,
                                         font=dict(size=14),
                                         showarrow=False)

    FN_annotation = go.layout.Annotation(text="FN",
                                         y=0.97, yref = "y2 domain", x=0.025,
                                         visible=True,
                                         font=dict(size=14),
                                         showarrow=False) 

    TP_annotation = go.layout.Annotation(text="TP",
                                         y=0.97, yref = "y2 domain",
                                         x=0.975,
                                         visible=True,
                                         font=dict(size=14),
                                         showarrow=False) 

    fig.data[0].visible = True   # first TN density curve
    fig.data[1].visible = True   # first FP density curve
    fig.data[2].visible = True   # first FN density curve
    fig.data[3].visible = True   # first TP density curve
    fig.data[4].visible = True   # first threshold vertical line (positive class subplot)
    fig.data[5].visible = True   # first threshold vertical line (negative class subplot)

    steps = []
    j = 0   # figure.data count

    for threshold in threshold_values:

        # Select annotations to be shown for each step: 
        # the correct annotation relative to the threshold line and the quadrant label (if there is enough space)
        if threshold > 0.96:
            annotation_list = [annotations[threshold], TN_annotation, 
                                                       FN_annotation]
        elif threshold < 0.04:
            annotation_list = [annotations[threshold], FP_annotation, 
                                                       TP_annotation]
        else:
            annotation_list = [annotations[threshold], TN_annotation, FP_annotation, 
                                                       FN_annotation, TP_annotation]    
        # Create slider step
        step = dict(method="update",
                    args=[{"visible": [False] * len(fig.data)},
                          {"title": dict(text = main_title + '<span style="font-size: 13px;">' \
                                                + titles[threshold] + '</span>', 
                                         y = 0.965, yanchor = 'bottom'),
                          "annotations": annotation_list}
                         ],
                    label = str(round(threshold, n_of_decimals))
                   )

        step["args"][0]["visible"][j] = True     # TN density curve
        step["args"][0]["visible"][j+1] = True   # FP density curve
        step["args"][0]["visible"][j+2] = True   # FN density curve
        step["args"][0]["visible"][j+3] = True   # TP density curve
        step["args"][0]["visible"][j+4] = True   # threshold vertical line (positive class subplot)
        step["args"][0]["visible"][j+5] = True   # threshold vertical line (positive class subplot)

        steps.append(step)
        j += 6                                   # add 6 to trace index (4 linechart, 2 threshold lines)

    # Define slider
    sliders = [dict(active=0,
                    currentvalue={"prefix": "Threshold: "},
                    pad=dict(t= 50),
                    steps=steps)]

    fig.update_layout(height=800,
                      margin=dict(t=80),
                      sliders=sliders,
                      annotations = [annotations[threshold_values[0]], FP_annotation, TP_annotation], #first visble annotations
                      title = dict(text = main_title + '<span style="font-size: 13px;">' \
                                          + titles[threshold_values[0]] + '</span>', 
                                   y = 0.965, yanchor = 'bottom'))                                    #first visible title

    # Axis layout
    fig.update_layout(xaxis2_title_text = 'Probabilities',
                      xaxis_range=[0, 1], 
                      yaxis1_title_text = 'Actual Negatives',
                      yaxis2_title_text = 'Actual Positives',
                      yaxis1_range=[0, max_y*1.1], yaxis2_range=[0, max_y*1.1])

    fig.show(config = dict(displayModeBar = show_display_modebar))

def confusion_matrix_plot(true_y, predicted_proba, threshold_step = 0.01, 
                          amounts = None, cost_dict = None, optimize_threshold = None, 
                          N_subsets = 70, subsets_size = 0.2, with_replacement = False,
                          currency = '€', random_state = None, 
                          title = 'Interactive Confusion Matrix', show_display_modebar = True):
    
    """ 
    Plots interactive and customized confusion matrix with plotly, 
    one for each threshold that can be selected with a slider, 
    displaying additional information (metrics, optimized thresholds). 
    
    Returns three dataframes containing: 
    - metrics that depend on threshold 
    - metrics that don't depend on threshold,
    - optimized thresholds (or empty)
    
    Plot is constituted by: 
    - table displaying metrics that vary based on the threshold selected:
      Accuracy, Balanced Acc., F1, Precision, Recall, MCC, Cohen's K
    - table displaying metrics that don't depend on threshold:
      ROC auc, Pecision-Recall auc, Brier score 
    - when optimize_threshold is given:
      table displayng thresholds optimized using GHOST method for any of the following metrics:
      Kohen's Kappa, Matthew's Correlation Coefficient, ROC, F-beta scores (beta = 1, 0.5, 2) 
      and for minimal total cost
    - confusion matrix (annotated heatmap) that varies based on the threshold selected
      displayng for each class (based on given inputs): count and percentage on total, amount and percentage on total, cost 
    - slider that allows to select the threshold 

    Parameters
    ----------
    true_y: sequence of ints (0 or 1)
        True labels 
    predicted_proba: sequence of floats
        predicted probabilities for class 1
        (e.g. output from model.predict_proba(data)[:,1]) 
    threshold_step: float, default=0.01
        step between each classification threshold (ranging from 0 to 1) below which prediction label is 0, 1 otherwise
        each value will have a corresponding slider step
    amounts: sequence of floats, default=None
        amounts associated to each element of data 
        (e.g. fraud detection for online orders: amounts could be the orders' amounts)
    cost_dict: dict, deafult=None
        dict containing costs associated to each class (TN, FP, FN, TP)
        with keys "TN", "FP", "FN", "TP" 
        and values that can be both lists (with coherent lenghts) and/or floats  
        (output from get_cost_dict)
        necessary when optimizing threshold for minimal total costs
    optimize_threshold: {'all', 'ROC', 'MCC', 'Kappa', 'Fscore', 'Cost'} 
                        or list containing allowed values except 'all',  default=None
        metrics for which thresholds will be optimized 
        'all' is equvalent to ['ROC', 'MCC', 'Kappa', 'Fscore'] if cost_dict=None, ['ROC', 'MCC', 'Kappa', 'Fscore', 'Cost'] otherwise
    N_subsets: int, default=70
        Number of subsets used in GHOST optimization process
    subsets_size: float or int, default=0.2
        Size of the subsets used in GHOST optimization process. 
        If float, represents the proportion of the dataset to include in the subsets. 
        If integer, it represents the actual number of instances to include in the subsets. 
    with_replacement: bool, default=False
        If True, the subsets used in GHOST optimization process are drawn randomly with replacement, without otherwise.            
    currency: str, default='€'
        currency symbol to be visualized. For unusual currencies, you can use their HTML code representation
        (eg. Indian rupee: '&#8377;')
    random_state: int, default=None
        Controls the randomness of the bootstrapping of the samples when optimizing thresholds with GHOST method
    title: str, default='Interactive Confusion Matrix'
        The main title of the plot.
    show_display_modebar: bool, default=True
        Determines wether plotly displayModeBar will be shown
    
    """
    if currency == '$': #correct dollar symbol for plotly in its HTML code
        currency = '&#36;'
    
    try:
        n_of_decimals = len(str(threshold_step).rsplit('.')[1])
    except:
        n_of_decimals = 4
        
    threshold_values = list(np.arange(0, 1 + threshold_step, threshold_step)) #define thresholds array  
    n_data = len(true_y)
    main_title = f"<b>{title}</b><br>"
    subtitle = "Total obs: " + '{:,}'.format(n_data)
    
    if amounts is not None:     
        amounts = list(amounts)
        tot_amount = sum(amounts)
        subtitle += "<br>Total amount: " + currency + '{:,.2f}'.format(tot_amount)
    
    # initialize annotation matrix 
    annotations_fixed = np.array([[["TN", "True Negative"], ["FP", "False Positive"]],     
                                  [["FN", "False Negative"], ["TP", "True Positive"]]])
    
    # initialize figure
    fig = make_subplots(rows=2, cols=3,
                        specs=[[{"type": "table"}, {"type": "table"}, {"type": "table"}],
                               [{"type": "heatmap", "colspan" : 3}, None, None]],
                        vertical_spacing=0.0,
                        horizontal_spacing = 0.01)
    
    # compute invariant metrics and create table with invariant metrics:
    constant_metrics_df = get_invariant_metrics_df(true_y, predicted_proba)
    fig.add_trace(
            go.Table(header=dict(values=['Invariant Metric', 'Value']),
                     cells=dict(values=[constant_metrics_df['invariant_metric'], constant_metrics_df['value']])
                    ), row=1, col=2)
    
    # create table with optimized thresholds or empty:
    if optimize_threshold is not None:
        
        # compute optimized thresholds and create dataframe
        optimal_thresholds_df = get_optimized_thresholds_df(optimize_threshold, threshold_values[1:-1], true_y, predicted_proba, 
                                                            cost_dict, random_state)
        fig.add_trace(
                go.Table(header=dict(values=['Optimized Metric', 'Optimal Threshold']),
                         cells=dict(values=[optimal_thresholds_df['optimized_metric'], optimal_thresholds_df['optimal_threshold']])
                        ), row=1, col=3)
    else:
        optimal_thresholds_df = None # needed for return statement
        fig.add_trace(go.Table({}), row=1, col=3) 
        
    # create dynamic titles dictionary (will be empty if cost is not given)
    titles = {}

    # initialize dataframe to store metrics dependent on threshold
    metrics_dep_on_threshold_df = pd.DataFrame() 
    
    for threshold in threshold_values:
        
        titles[threshold] = '' #set empty title
        
        # get confusion matrix and metrics dep. on threshold
        matrix, temp_metrics_df = get_confusion_matrix_and_metrics_df(true_y, predicted_proba, 
                                                                      threshold = threshold, normalize = None)
        # concat to metrics_dep_on_threshold_df
        temp_metrics_df['threshold'] = threshold
        metrics_dep_on_threshold_df = pd.concat([metrics_dep_on_threshold_df, temp_metrics_df])
        
        annotations = np.dstack((annotations_fixed, matrix/n_data)) # add count percentage to annotations matrix 
        
        # define dynamic annotations and hover text  
        template = "%{z} (%{text[2]:.2~%})"       # total count and perc.           

        if amounts or cost_dict:
            annotations_max_index = 2
        
            if amounts:
                amount_matrix = _get_amount_matrix(true_y, predicted_proba, threshold, amounts)
                annotations = np.dstack((annotations, amount_matrix, amount_matrix/tot_amount)) # add amount matrix and perc. matrix
                annotations_max_index += 2
                #add to template "Amount:" total and perc.
                template +=  "<br>Amount: "+ currency + "%{text[3]:~s} (%{text[4]:.2~%})"       

            if cost_dict:
                cost_matrix = _get_cost_matrix(true_y, predicted_proba, threshold, cost_dict)
                total_cost = cost_matrix.sum()
                annotations = np.dstack((annotations, cost_matrix, cost_matrix/total_cost))     # add cost matrix and perc. matrix
                annotations_max_index += 2
                #add to template "Cost:" total and perc.
                template += "<br>Cost: "+ currency +\
                            "%{text[" + str(annotations_max_index-1) +  "]:~s} (%{text[" +str(annotations_max_index)+  "]:.2~%})"                 
                # update title adding total cost
                titles[threshold] += "<br>Total cost: " + currency + '{:,.2f}'.format(cost_matrix.sum())
            
        # invert rows (for plotly.go plots compatibility)
        matrix[[0, 1]] = matrix[[1, 0]] 
        annotations[[0, 1]] = annotations[[1, 0]]
        
        # table with metrics that depend on threshold        
        fig.add_trace(
            go.Table(header=dict(values=['Variable Metric', 'Value']),
                     cells=dict(values=[temp_metrics_df[k].tolist() for k in temp_metrics_df.columns[:-1]]),
                     visible=False
                    ),
            row=1, col=1)
        
        # annotated confusion matrix
        fig.add_trace(go.Heatmap(z = matrix,
                               text = annotations,
                               texttemplate= "<b>%{text[0]}</b><br>" + template,
                               name="threshold: " + str(round(threshold, n_of_decimals)),
                               hovertemplate = "<b>%{text[1]}</b><br>Count: " + template,
                               x=['False', 'True'],
                               y=['True', 'False'],
                               colorscale = 'Blues',
                               showscale = False,
                               visible=False), row=2, col=1)  
    
    # pivot metrics_dep_on_threshold_df 
    name_col = metrics_dep_on_threshold_df.columns[0]
    value_col = metrics_dep_on_threshold_df.columns[1]
    metrics_dep_on_threshold_df = metrics_dep_on_threshold_df.pivot(columns = name_col, values = value_col, index = 'threshold').reset_index('threshold').rename_axis(None, axis=1)    
    
    # fig.data[0] is the constant metrcis table, fig.data[1] is the optimal threshold table, always visible
    fig.data[2].visible = True   # first variable metrics table
    fig.data[3].visible = True   # first confusion matrix
    
    # create and add slider
    steps = []
    j = 2   # skip first and second trace (invariant metric table, opt. thresholds/empty table)
    
    for threshold in threshold_values:
        step = dict(method="update",
                    args=[{"visible": [False] * len(fig.data)},
                          {"title": dict(text = main_title + '<span style="font-size: 13px;">' \
                                              + subtitle + titles[threshold] + '</span>', 
                                         y = 0.965, yanchor = 'bottom')}
                         ],
                    label = str(round(threshold, n_of_decimals))
                   )
        
        step["args"][0]["visible"][0] = True    # constant metric table always visible
        step["args"][0]["visible"][1] = True    # opt. thresholds/empty table always visible
        step["args"][0]["visible"][j] = True    # threshold related confusion matrix 
        step["args"][0]["visible"][j+1] = True  # threshold related variable metrics table
        steps.append(step)
        j += 2                                  # add 2 to trace index (confusion matrix and variable metrics table)
        
    sliders = [dict(active=0,
                    currentvalue={"prefix": "Threshold: "},
                    pad=dict(t= 50),
                    steps=steps)]

    fig.update_layout(height=600,
                      sliders=sliders, 
                      title = dict(text = main_title + '<span style="font-size: 13px;">' \
                                          + subtitle + titles[threshold_values[0]] + '</span>', 
                                   y = 0.965, yanchor = 'bottom')) #first visible title
    
    fig.update_xaxes(title_text = "Predicted")
    fig.update_yaxes(title_text = "Actual")
    fig.show(config = dict(displayModeBar = show_display_modebar))
    
    return metrics_dep_on_threshold_df, constant_metrics_df, optimal_thresholds_df

def confusion_linechart_plot(true_y, predicted_proba, threshold_step = 0.01, 
                             amounts = None, cost_dict = None, currency = '€',
                             title = 'Interactive Confusion Line Chart', show_display_modebar = True):
    
    """
    - Plots interactive and customized line-plots with plotly, one for each "confusion class" (TN, FP, FN, TP), 
      displayng amount and/or cost againts thresholds and additional information (intersection points, total cost)    
    - Returns a dataframe containing, for every threshold and depending on the inputs, 
      the amount and cost associated to each class (TN, FP, FN, TP) and the total cost
    - Returns the value of the total amount

    Plot is constituted by: 
    - four linecharts, one for each class (TN, FP, FN, TP), with thresholds on x axis 
      and amounts and/or costs (depends on the given input) on y axis 
    - slider that moves markers in linecharts based on threshold selected

    Parameters
    ----------
    true_y: sequence of ints (0 or 1)
        True labels 
    predicted_proba: sequence of floats
        predicted probabilities for class 1
        (e.g. output from model.predict_proba(data)[:,1]) 
    threshold_step: float, default=0.01
        step between each classification threshold (ranging from 0 to 1) below which prediction label is 0, 1 otherwise
        each value will have a corresponding slider step
    amounts: sequence of floats, default=None
        amounts associated to each element of data 
        (e.g. fraud detection for online orders: amounts could be the orders' amounts)
    cost_dict: dict, deafult=None
        dict containing costs associated to each class (TN, FP, FN, TP)
        with keys "TN", "FP", "FN", "TP" 
        and values that can be both lists (with coherent lenghts) and/or floats  
        (output from get_cost_dict)
    currency: str, default='€'
        currency symbol to be visualized. For unusual currencies, you can use their HTML code representation
        (eg. Indian rupee: '&#8377;')
    title: str, default='Interactive Confusion Line Chart'
        The main title of the plot.
    show_display_modebar: bool, default=True
        Determines wether plotly displayModeBar will be shown
        
    Returns
    ----------   
    amount_cost_df: pandas dataframe
        Dataframe containing variables: 
        - threshold
        - if amounts is given: amounts relative to each class (TN, FP, FN, TP) 
        - if cost_dict is given: cost relative to each class (TN, FP, FN, TP) and total cost
        
    total_amounts: float
        sum of the amounts (or None if amounts is None)
    """
    
    if currency == '$':
        currency = '&#36;'
    
    try:
        n_of_decimals = len(str(threshold_step).rsplit('.')[1])
    except:
        n_of_decimals = 4
        
    threshold_values = list(np.arange(0, 1 + threshold_step, threshold_step))
    middle_x = (threshold_values[0] + threshold_values[-1])/2  
    n_data = len(true_y)
    main_title = f"<b>{title}</b><br>"
    subtitle = "Total obs: " + '{:,}'.format(n_data)
    
    if amounts is not None:
        amounts = list(amounts)
        tot_amount = sum(amounts)
        subtitle += "<br>Total amount: " + currency + '{:,.2f}'.format(tot_amount)
        
    # Create labels for titles
    label_lst = ["True Negative", "False Positive", "False Negative", "True Positive"]

    # get threshold-amount-cost dataframe (throws error if both cost_dict and amounts are None)
    amount_cost_df = get_amount_cost_df(true_y, predicted_proba, threshold_values, amounts, cost_dict)
    
    # Create figure
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles = label_lst,
        shared_xaxes = True,
        vertical_spacing=0.16,
        specs=[[{"type": "scatter"}, {"type": "scatter"}],
               [{"type": "scatter"}, {"type": "scatter"}]]
    )
    
    for annotation in fig['layout']['annotations']: 
        annotation['y'] = annotation['y'] + 0.04  #move subplots title up 
    
    middle_y_lst = []

    if (amounts is not None) and (cost_dict is not None):
        static_charts_num = 12
        markers_num = 8
        unit_y_lst = []
        
        titles = {threshold: "<br>Total cost: " + currency \
                                 + '{:,.2f}'.format(value) for threshold, value in zip(threshold_values, 
                                                                                       list(amount_cost_df['total_cost']))}
    
        # Create amounts and cost line charts       
        for confusion_index, row_index, col_index, color1, color2 in zip(['TN', 'FP', 'FN', 'TP'],
                                                                         [1, 1, 2, 2],
                                                                         [1, 2, 1, 2],
                                                                         ['blue', 'red', '#EF71D9', '#00CC96'],
                                                                         ['rgb(128, 177, 211)', 'rgb(251, 128, 114)', 
                                                                          'rgb(220, 186, 218)', 'rgb(141, 211, 199)']):
            fig.add_trace(
                go.Scatter(x = amount_cost_df['threshold'],
                           y = amount_cost_df['amount_' + confusion_index],
                           showlegend = False,
                           mode="lines",
                           line=dict(color=color1),
                           hovertemplate = "amount: " + currency + "%{y}<extra></extra>"),
                row=row_index, col=col_index)
            
            fig.add_trace(
                go.Scatter(x = amount_cost_df['threshold'],
                           y = amount_cost_df['cost_' + confusion_index],
                           showlegend = False,
                           mode="lines",
                           line=dict(color=color2),
                           hovertemplate = "cost: " + currency + "%{y}<extra></extra>"),
                row=row_index, col=col_index)
            
            # Save middle points
            middle_y_lst.append((max(fig.data[-2]['y'] + fig.data[-1]['y']) + min(fig.data[-2]['y'] + fig.data[-1]['y']))/2)
            unit_y_lst.append((middle_y_lst[-1] - min(fig.data[-2]['y'] + fig.data[-1]['y']))/4)
                
            x_intersect = []
            y_intersect = []
            diff_cost_amount = list(amount_cost_df['amount_' + confusion_index] - amount_cost_df['cost_' + confusion_index])

            for i in range(len(diff_cost_amount)-1):
                if (diff_cost_amount[i] < 0) & (diff_cost_amount[i+1]>=0):
                    x_intersect.append(amount_cost_df.iloc[i+1]['threshold'])
                    y_intersect.append(amount_cost_df.iloc[i+1]['cost_' + confusion_index])

                elif (diff_cost_amount[i] > 0) & (diff_cost_amount[i+1]<=0):
                    x_intersect.append(amount_cost_df.iloc[i+1]['threshold'])
                    y_intersect.append(amount_cost_df.iloc[i+1]['cost_' + confusion_index])

            fig.add_trace(
                go.Scatter(x=x_intersect, 
                           y=y_intersect, 
                           showlegend = False,
                           mode = "markers",
                           marker_symbol = 'diamond', 
                           marker_size = 8,
                           marker=dict(color='black'),
                           hovertemplate = "%{x}<extra></extra>",
                          ),
                row = row_index, col = col_index)
            
            if x_intersect:
                intercepts_str = 'Swaps: '
                intercepts_str += ", ".join(str(round(x, n_of_decimals)) for x in x_intersect)
                fig.add_annotation(xref="x domain",yref="y domain",x=0.5, y=1.15, showarrow=False, 
                                   text=intercepts_str, row=row_index, col=col_index)
        
        # Create indicator markers
        for threshold in threshold_values:
            amount_cost_row = amount_cost_df.loc[amount_cost_df['threshold'] == threshold]
            
            if threshold > middle_x:
                left_or_right = ' left'
            else:
                left_or_right = ' right'
                
            for confusion_index, row_index, col_index, middle_y, \
                unit_y, color1, color2 in zip(['TN', 'FP', 'FN', 'TP'], 
                                               [1, 1, 2, 2], 
                                               [1, 2, 1, 2],
                                               middle_y_lst, 
                                               unit_y_lst, 
                                               ['blue', 'red', '#EF71D9', '#00CC96'],
                                               ['rgb(128, 177, 211)', 'rgb(251, 128, 114)', 'rgb(220, 186, 218)', 'rgb(141, 211, 199)']):

                y_point_amount, y_point_cost = float(amount_cost_row['amount_' + confusion_index]), float(amount_cost_row['cost_' + confusion_index])     

                if abs(y_point_amount - y_point_cost) < unit_y:

                    if y_point_amount > y_point_cost:
                        textposition_cost = 'bottom' + left_or_right
                        textposition_amount = 'top' + left_or_right

                    else:
                        textposition_cost = 'top' + left_or_right
                        textposition_amount = 'bottom' + left_or_right

                else:

                    if y_point_cost < middle_y:
                        textposition_cost = 'top' + left_or_right
                    else:
                        textposition_cost = 'bottom' + left_or_right

                    if y_point_amount < middle_y:
                        textposition_amount = 'top' + left_or_right
                    else:
                        textposition_amount = 'bottom' + left_or_right

                fig.add_trace(
                    go.Scatter(x = [threshold], 
                               y = [y_point_amount], 
                               showlegend = False,
                               mode = 'markers+text',
                               texttemplate = "amount: " + currency + "%{y}",
                               textposition = [textposition_amount],
                               hoverlabel = dict(bgcolor = 'rgb(68, 68, 68)'),
                               hovertemplate = '%{x:.' + str(n_of_decimals) + 'f}<extra></extra>',
                               marker = dict(color=color1),
                               marker_size = 8,
                               visible=False),
                    row = row_index, col = col_index)
                
                fig.add_trace(
                    go.Scatter(x = [threshold], 
                               y = [y_point_cost], 
                               showlegend = False,
                               mode = 'markers+text',
                               texttemplate = "cost: " + currency + "%{y}",
                               textposition = [textposition_cost],
                               hoverlabel = dict(bgcolor = 'rgb(68, 68, 68)'),
                               hovertemplate = '%{x:.' + str(n_of_decimals) + 'f}<extra></extra>',
                               marker = dict(color=color2),
                               marker_size = 8,
                               visible=False),
                    row = row_index, col = col_index)
                
    else:
        static_charts_num = 4
        markers_num = 4
        if amounts is not None:
            var_to_plot = 'amount'
            titles = {threshold: '' for threshold in threshold_values} # set empty titles dict
        else:
            tot_amount = None
            var_to_plot = 'cost'
            titles = {threshold: "<br>Total cost: " + currency \
                                 + '{:,.2f}'.format(value) for threshold, value in zip(threshold_values, 
                                                                                       list(amount_cost_df['total_cost']))}
        
        for confusion_index, row_index, col_index, color in zip([var_to_plot + '_TN', var_to_plot + '_FP',
                                                                 var_to_plot + '_FN', var_to_plot + '_TP'],
                                                                [1, 1, 2, 2],
                                                                [1, 2, 1, 2],
                                                                ['blue', 'red', 
                                                                 '#EF71D9', '#00CC96']): 
            fig.add_trace(
                go.Scatter(x = amount_cost_df['threshold'],
                           y = amount_cost_df[confusion_index],
                           showlegend = False,
                           mode="lines",
                           line=dict(color=color),
                           hovertemplate = var_to_plot + ": " + currency + "%{y}<extra></extra>"),
                row=row_index, col=col_index)
            
        for i in range(4):
            middle_y_lst.append((max(fig.data[i]['y']) + min(fig.data[i]['y']))/2)
        
        # Create indicator markers
        for threshold in threshold_values:
            
            if threshold > middle_x:
                left_or_right = ' left'
            else:
                left_or_right = ' right'
                
            amount_cost_row = amount_cost_df.loc[amount_cost_df['threshold'] == threshold]     
            
            for confusion_index, row_index, col_index, middle_y, color in zip([var_to_plot + '_TN', var_to_plot + '_FP',
                                                                               var_to_plot + '_FN', var_to_plot + '_TP'],
                                                                              [1, 1, 2, 2],
                                                                              [1, 2, 1, 2],
                                                                              middle_y_lst,
                                                                              ['blue', 'red', '#EF71D9', '#00CC96']):            

                y_point = float(amount_cost_row[confusion_index])
                
                if y_point < middle_y:
                    textposition = 'top' + left_or_right
                else:
                    textposition = 'bottom' + left_or_right
                    
                fig.add_trace(
                    go.Scatter(x = [threshold], 
                               y = [y_point], 
                               showlegend = False,
                               mode = 'markers+text',
                               texttemplate = var_to_plot + ": " + currency + "%{y}",
                               textposition = textposition,
                               hoverlabel = dict(bgcolor = 'rgb(68, 68, 68)'),
                               hovertemplate = '%{x:.' + str(n_of_decimals) + 'f}<extra></extra>',
                               name = str(round(threshold, n_of_decimals)),
                               marker=dict(color=color),
                               marker_size = 8,
                               visible=False),
                row = row_index, col = col_index)

    # if both amounts and cost are given, static_charts_num = 12  
    # (4 linecharts for amount, 4 for cost, 4 for intercepts) from fig.data[0] to fig.data[11]
    # if either amounts or cost is not given, static_charts_num = 4 
    # there are just 4 linecharts from fig.data[0] to fig.data[3]
    # line charts are always visible
    
    # make visible also the first line-chart markers to visualize (associated with the first threshold)
    for i in range(markers_num):
        fig.data[static_charts_num + i].visible = True 

    steps = []
    j = static_charts_num 
    
    for threshold in threshold_values:
        step = dict(
            method="update",
            args=[{"visible": [False] * len(fig.data)},
                  {"title": dict(text = main_title + '<span style="font-size: 13px;">' \
                                          + subtitle + titles[threshold] + '</span>',
                                 y = 0.965, yanchor = 'bottom')}
                 ],
            label = str(round(threshold, n_of_decimals))
        )
        step["args"][0]["visible"][:static_charts_num] = [True]*static_charts_num   # line charts 
        step["args"][0]["visible"][j:j+markers_num] = [True]*markers_num            # line chart markers 
            
        j += markers_num
        steps.append(step)

    sliders = [dict(
        active=0,
        currentvalue={"prefix": "Threshold: "},
        steps=steps,
        pad=dict(t = 50))]

    fig.update_layout(sliders=sliders, 
                      title = dict(text = main_title + '<span style="font-size: 13px;">' \
                                          + subtitle + titles[threshold_values[0]] + '</span>', 
                                   y = 0.965, yanchor = 'bottom'), #first visible title
                      margin={'t': 125},
                     )
    
    fig.update_layout(height=600, hovermode="x")

    # Update xaxis properties
    fig.update_xaxes(title_text="Threshold", title_font_size=12, row=2, col=1)
    fig.update_xaxes(title_text="Threshold", title_font_size=12, row=2, col=2)
    
    # Update yaxis properties
    fig.update_yaxes(title_text="Amount/Cost", title_font_size=12, row=1, col=1)
    fig.update_yaxes(title_text="Amount/Cost", title_font_size=12, row=2, col=1)

    fig.show(config = dict(displayModeBar = show_display_modebar))
    
    try:
        tot_amount = round(tot_amount, 2)
    except:
        tot_amount = None    
        
    return amount_cost_df, tot_amount

def total_amount_cost_plot(true_y, predicted_proba, threshold_step = 0.01,
                           amounts = None, cost_dict = None,
                           amount_classes = 'all', cost_classes = 'all', currency = '€',
                           title = 'Interactive Amount-Cost Line Chart', show_display_modebar = True):
    
    """
    - Plots an interactive and customized line-plot with plotly, 
      displayng total amount and/or total cost for user-selected "confusion classes" (TN, FP, FN, TP) againts thresholds.     
    - Returns a dataframe containing, for every threshold and depending on the inputs, 
      the amount and cost associated to each class (TN, FP, FN, TP) and the total cost
    - Returns the value of the total amount    
    
    Plot is constituted by one linechart with thresholds on x axis 
    and total amounts and/or total costs (depends on the given input) on y axis 

    Parameters
    ----------
    true_y: sequence of ints (0 or 1)
        True labels 
    predicted_proba: sequence of floats
        predicted probabilities for class 1
        (e.g. output from model.predict_proba(data)[:,1]) 
    threshold_step: float, default=0.01
        step between each classification threshold (ranging from 0 to 1) below which prediction label is 0, 1 otherwise
    amounts: sequence of floats, default=None
        amounts associated to each element of data 
        (e.g. fraud detection for online orders: amounts could be the orders' amounts)
    cost_dict: dict, deafult=None
        dict containing costs associated to each class (TN, FP, FN, TP)
        with keys "TN", "FP", "FN", "TP" 
        and values that can be both lists (with coherent lenghts) and/or floats  
        (output from get_cost_dict)
    amount_classes: {'all', 'TN', 'FP', 'FN', 'TP'} 
                    or list containing allowed values except 'all'
        the amount plotted is the sum of the amounts associated to data points belonging to the selected amount_classes   
    cost_classes: {'all', 'TN', 'FP', 'FN', 'TP'} 
                  or list containing allowed values except 'all'
        the total cost plotted is the sum of the costs associated to data points belonging to the selected cost_classes        
    currency: str, default='€'
        currency symbol to be visualized. For unusual currencies, you can use their HTML code representation
        (eg. Indian rupee: '&#8377;')
    title: str, default='Interactive Amount-Cost Line Chart'
        The main title of the plot.
    show_display_modebar: bool, default=True
        Determines wether plotly displayModeBar will be shown

    Returns
    ----------   
    amount_cost_df: pandas dataframe
        Dataframe containing variables: 
        - threshold
        - if amounts/amount_classes are given: amounts relative to the user-selected classes and sum 
        - if cost_dict/cost_classes are given: cost relative to the user-selected classes and sum

    """
    
    if currency == '$':
        currency = '&#36;'
    
    try:
        n_of_decimals = len(str(threshold_step).rsplit('.')[1])
    except:
        n_of_decimals = 4
        
    threshold_values = list(np.arange(0, 1 + threshold_step, threshold_step)) 
    middle_x = (threshold_values[0] + threshold_values[-1])/2  
    
    supported_label = ["TN", "FP", "FN", "TP"]
    
    if amounts is not None:      # if amount_classes not given or 'all', set to ["TN", "FP", "FN", "TP"]
        amounts = list(amounts)
        if (amount_classes is None) or (amount_classes == 'all'):
            amount_classes = supported_label
    elif amount_classes is not None:
        raise TypeError("if amount_classes is given, amounts can't be None.") 
        
    if cost_dict is not None:    # if cost_classes not given or 'all', set to ["TN", "FP", "FN", "TP"]
        if (cost_classes is None) or (cost_classes == 'all'):
            cost_classes = supported_label
    elif cost_classes is not None:
        raise TypeError("if cost_classes is given, cost_dict can't be None.") 
        
    # get threshold-amount-cost dataframe (throws error if both cost_dict and amounts are None)
    amount_cost_df = get_amount_cost_df(true_y, predicted_proba, threshold_values, amounts, cost_dict)
    
    # Create figure
    fig = go.Figure()
    
    var_num = 0
    subtitle = ""
    col_lst = []
        
    if amount_classes is not None:
        var_num += 1
            
        if isinstance(amount_classes, str):
            amount_classes = [amount_classes]
        
        amount_col_lst = ['amount_' + amount_class for amount_class in amount_classes]
        amount_cost_df['amount_sum'] = amount_cost_df[amount_col_lst].apply(sum, axis = 1)        
        col_lst += amount_col_lst + ['amount_sum']
        fig.add_trace(
            go.Scatter(x = amount_cost_df['threshold'],
                       y = amount_cost_df['amount_sum'],
                       showlegend = False,
                       mode="lines",
                       hovertemplate = "total amount: " + currency + "%{y}<extra></extra>"))
        
        subtitle += "Amount categories: "     
        subtitle += " + ".join(amount_classes)
        subtitle += "<br>"  
            
    if cost_classes is not None:
        var_num += 1
        
        if isinstance(cost_classes, str):
            cost_classes = [cost_classes]

        cost_col_lst = ['cost_' + cost_class for cost_class in cost_classes]
        amount_cost_df['cost_sum'] = amount_cost_df[cost_col_lst].apply(sum, axis = 1)        
        col_lst += cost_col_lst + ['cost_sum']
        fig.add_trace(
            go.Scatter(x = amount_cost_df['threshold'],
                       y = amount_cost_df['cost_sum'],
                       showlegend = False,
                       mode="lines",
                       hovertemplate = "total cost: " + currency + "%{y}<extra></extra>"))
        
        subtitle += "Cost categories: "     
        subtitle += " + ".join(cost_classes)
        
    intercepts_str = ''   
    
    if var_num == 2:                 
        diff_cost_amount = list(amount_cost_df['amount_sum'] - amount_cost_df['cost_sum'])
        x_intersect = []
        y_intersect = []
        
        for i in range(len(diff_cost_amount)-1):
            if (diff_cost_amount[i] < 0) & (diff_cost_amount[i+1]>=0):
                x_intersect.append(amount_cost_df.iloc[i+1]['threshold'])
                y_intersect.append(amount_cost_df['cost_sum'].iloc[i+1])

            elif (diff_cost_amount[i] > 0) & (diff_cost_amount[i+1]<=0):
                x_intersect.append(amount_cost_df.iloc[i+1]['threshold'])
                y_intersect.append(amount_cost_df['cost_sum'].iloc[i+1])

        fig.add_trace(
            go.Scatter(x=x_intersect, 
                       y=y_intersect, 
                       showlegend = False,
                       mode = "markers",
                       marker_symbol = 'diamond', 
                       marker_size = 8,
                       marker=dict(color='black'),
                       hovertemplate = "%{x}<extra></extra>"))
        
        if x_intersect:
            intercepts_str = 'Swaps at thresholds: '
            intercepts_str += ", ".join(str(round(x, n_of_decimals)) for x in x_intersect)
        
    fig.update_layout(title = dict(text = f"<b>{title}</b><span style='font-size: 13px;'><br>" + subtitle + \
                                   '<br>' + intercepts_str,
                                   y = 0.965, yanchor = 'bottom'),
                      margin={'t': 120},
                     )
    
    fig.update_layout(height=600, hovermode="x unified")

    # Update axis properties
    fig.update_xaxes(title_text="Threshold")
    fig.update_yaxes(title_text="Amount/Cost")
    
    fig.show(config = dict(displayModeBar = show_display_modebar))
    
    return amount_cost_df[['threshold'] + col_lst]



                   
