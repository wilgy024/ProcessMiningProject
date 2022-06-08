import tkinter as tk
from tkinter import ttk
from tkinter import *
import glob
import pandas as pd
import pm4py
from pm4py.objects.log.util import dataframe_utils
import warnings
# sdhiraj: file transport
import os

# sdhiraj:
import re
import tkinter.messagebox
from tkinter import END

# sdhiraj: miner algorithms
from pm4py.algo.discovery.alpha import algorithm as alpha_miner
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.objects.conversion.process_tree import converter as pt_converter

# wilgy: Event log filtering modules
from pm4py.algo.filtering.log.variants import variants_filter
from pm4py.algo.filtering.log.attributes import attributes_filter
warnings.filterwarnings("ignore", category=DeprecationWarning) #wilgy: supress deprecation warning for variants_filter
# wilgy: Visualisation modules
# sdhiraj
from pm4py.visualization.graphs import visualizer as graphs_visualizer
from pm4py.visualization.process_tree import visualizer as pt_visualizer

# wilgy: Statistical modules
from pm4py.statistics.traces.generic.log import case_statistics as cs, case_arrival
from pm4py.statistics.traces.generic.pandas import case_statistics, case_arrival

# *****************************************************************************
# wilgy: This section builds a user interactive window to select percentage thresholds
# *****************************************************************************

# wilgy: build variants percentage window for user interaction. Includes slider for selection.
variants_percentage_selection = tk.Tk()
current_value = tk.DoubleVar()
variants_percentage_selection.geometry('500x250')
variants_percentage_selection.resizable(False, False)
variants_percentage_selection.title('Percentage Selector')

# wilgy: configure grid settings for window
variants_percentage_selection.columnconfigure(0, weight=1)
variants_percentage_selection.columnconfigure(1, weight=3)

# wilgy: function to format the percentage selection.
def get_current_value():
    return '{: .0f} percent'.format(current_value.get() * 100)

# wilgy: function listens for slider move and changes value label accordingly.
def slider_changed(event):
    value_label.configure(text=get_current_value())

# wilgy: function to close the window and return the selected percentage.
def closeWindow():
    selected_value = current_value.get()
    selected_value = round(selected_value, 2)
    current_value.set(selected_value)
    print("Selected threshold: {}".format(selected_value))
    variants_percentage_selection.destroy()
    return selected_value

# wilgy: label for the slider
slider_label = ttk.Label(variants_percentage_selection, text='The percentage setting determines the minimum \n'
                                                             + 'occurrences of a process to be considered. \nUse the slider to make your selection:',
                         padding=20)
slider_label.grid(column=0, row=0, sticky='w')

# wilgy: sets the scale for the slider widget, i.e., 0.1 is 10 percent.
slider = ttk.Scale(variants_percentage_selection, from_=0.0, to=0.1, orient='horizontal',
                   command=slider_changed, variable=current_value)
slider.grid(column=1, row=0, ipadx=20)

# current value label
current_value_label = ttk.Label(variants_percentage_selection, text='Current Value:')
current_value_label.grid(row=1, columnspan=2, sticky='n', ipadx=10, ipady=10)

# value label
value_label = ttk.Label(variants_percentage_selection, text=get_current_value())
value_label.grid(row=2, columnspan=2, sticky='n')

# wilgy:clicking OK button will close the window
button = Button(variants_percentage_selection, text="Ok", fg='blue', command=closeWindow)
button.place(relx=0.5, rely=0.75, anchor=CENTER)
variants_percentage_selection.mainloop()

# *****************************************************************************
# End of window
# *****************************************************************************

# *****************************************************************************
# wilgy: This section builds a user interactive window to select what type of
#       algorithm to use for process mining.
# *****************************************************************************

miner_window = Tk()
miner_selection = IntVar()

# wilgy: function returning the value of miner selection
def minerValue():
    value = miner_selection.get()
    print("Selected miner: {}".format(value))
    return value

# wilgy: function to close miner threshold selection window. If no algorithm selected, default to 1 (DFG).
def closeMinerWindow():
    value = miner_selection.get()
    if value == 0:
        miner_selection.set(1)
    miner_window.destroy()

# wilgy: New window to select which miner to utilise
# sdhiraj
Label(miner_window, text='Select which process mining algorithm to utilise:').pack(pady=20)
Radiobutton(miner_window, text="Directly Follows Graph", variable=miner_selection, value=1, command=minerValue).pack()
Radiobutton(miner_window, text="Heuristics Miner", variable=miner_selection, value=2, command=minerValue).pack()
Radiobutton(miner_window, text="Alpha Miner", variable=miner_selection, value=3, command=minerValue).pack()
Radiobutton(miner_window, text="Inductive Miner", variable=miner_selection, value=4, command=minerValue).pack()
Button(miner_window, text="Ok", fg='blue', command=closeMinerWindow).pack(
    pady=20)  # wilgy:clicking OK button will close the window

# wilgy: Setting parameters of the GUI
miner_window.title('PM Algorithm selection')
miner_window.geometry("400x300+10+10")
miner_window.mainloop()

# *****************************************************************************
# End of window
# *****************************************************************************

# wilgy: function returns the full file path of the target filename
# (useful if users have saved file path in varying locations)
def find_files(filename, path):
    file = [f for f in glob.glob(path + '**/' + filename, recursive=True)]
    for f in file:
        return (f)

# wilgy: function converts csv to event log format, with relevant variables selected as keys.
# Also filters the eventlog to determine start and end activities and corresponding count of each start and end activities.
def import_pm4py(event_log):
    event_log = pm4py.format_dataframe(event_log, case_id='EpisodeNo', activity_key='Activity'
                                       , timestamp_key='EndTime', start_timestamp_key='EventTime')
    start_activities = pm4py.get_start_activities(event_log)
    end_activities = pm4py.get_end_activities(event_log)
    num_variants = pm4py.get_variants_as_tuples(event_log)
    print("Number of variants: {}".format(len(num_variants)))
    print("Number of unique start activities: {}".format(len(set(start_activities))))
    print("Number of unique end activities: {}".format(len(set(end_activities))))
    return event_log

# wilgy: function utilises pandas to import the csv and display the count of events and total unique cases.
def import_csv(file_path):
    event_log = pd.read_csv(file_path, sep=',')
    num_events = len(event_log)
    num_cases = len(event_log.EpisodeNo.unique())
    print("Number of events: {}\nNumber of cases: {}".format(num_events, num_cases))
    # wilgy: convert timeformats for PM4PY
    event_log = dataframe_utils.convert_timestamp_columns_in_df(event_log)
    return event_log

# wilgy: function to discover and view directly follows graph (DFG). Output as PDF.
def pm_dfg(event_log):
    dfg, start_activities, end_actvities = pm4py.discover_dfg(event_log)
    #pm4py.view_dfg(dfg, start_activities, end_actvities, 'pdf')
    # sdhiraj:  converts to png and calls file_to_Algorithm_Outputs method
    pm4py.vis.save_vis_dfg(dfg, start_activities, end_actvities, 'dfg.png')
    all_episodes_miner_output('/dfg.png')

# wilgy: from GGrossmann.
def pm_heuristics(df):
    print("Discover heuristics net ...")
    # https://pm4py.fit.fraunhofer.de/static/assets/api/2.2.18/pm4py.html?highlight=discover_heuristics_net#pm4py.discovery.discover_heuristics_net
    map = pm4py.discovery.discover_heuristics_net(df, current_value.get())
    # The map object is a HeuristicsNet
    #print("Class name of variable map: " + map.__class__.__name__)
    #print("Visualizing heuristics net ...")
    #pm4py.view_heuristics_net(map, "pdf")
    # sdhiraj:  converts to png and calls All_Episodes_Miner_Output method
    pm4py.vis.save_vis_heuristics_net(map, 'heuristics.png')
    all_episodes_miner_output('/heuristics.png')

# sdhiraj alpha miner algorithm containing petri net object and visualisation
def pm_alpha(event_log):
    print("Discover petri net ...")
    net, initial_marking, final_marking = alpha_miner.apply(event_log)  # sdhiraj: The map object is a PetriNet
    print("Visualizing petri net ...")
    #https://pm4py.fit.fraunhofer.de/static/assets/api/2.2.10/pm4py.visualization.petri_net.html
    #petri_net_viz = pm4py.visualization.petri_net.visualizer.apply(net, start_activities, end_activities)
    #pm4py.visualization.petri_net.visualizer.view(petri_net_viz)
    # sdhiraj:  converts to png and calls All_Episodes_Miner_Output method
    pm4py.vis.save_vis_petri_net(net, initial_marking, final_marking, 'alpha.png')
    all_episodes_miner_output('/alpha.png')

# file_to_Algorithm_Outputs('alpha.png')

# sdhiraj: inductive miner algorithm and visualisation that depicts tree and calls pm_inductive_petri method
def pm_inductive(event_log):
    print("Discover inductive...")
    tree = inductive_miner.apply_tree(event_log)
    #print("Visualizing inductive ...")
    #inductive_viz = pt_visualizer.apply(tree)
    # tree visualisation
    #pt_visualizer.view(inductive_viz)
    # sdhiraj:  converts to png and calls file_to_Algorithm_Outputs method
    pm4py.vis.save_vis_process_tree(tree, 'inductive_tree.png')
    all_episodes_miner_output('/inductive_tree.png')

    net, initial_marking, final_marking = pt_converter.apply(tree)
    parameters = {pm4py.visualization.petri_net.visualizer.Variants.FREQUENCY.value.Parameters.FORMAT: "png"}
    petri_net_viz = pm4py.visualization.petri_net.visualizer.apply(net, initial_marking, final_marking,
                                                                   parameters=parameters,
                                                                   variant=pm4py.visualization.petri_net.visualizer.Variants.FREQUENCY,
                                                                   log=event_log)
    # petrinet visualisation
    #pm4py.visualization.petri_net.visualizer.view(petri_net_viz)
    # sdhiraj:  converts to png and calls file_to_Algorithm_Outputs method
    pm4py.vis.save_vis_petri_net(net, initial_marking, final_marking, 'inductive_petri_net.png')
    all_episodes_miner_output('/inductive_petri_net.png')


# sdhiraj:moves png file to All_Episodes_Miner_Output folder
def all_episodes_miner_output(file_name):
    script_dir = os.path.dirname(__file__)
    curr_file_dir = script_dir + file_name
    rel_path = "/All_Episodes_Miner_Output" + file_name
    abs_file_path = script_dir + rel_path
    os.replace(curr_file_dir, abs_file_path)

# wilgy: function to calcualte distribution graph of EpisodeNo events over time (months)
# If a full event log is passed in, saves file to All Episodes output folder, or for a singular episode
# saves the file to the Singular Episode output folder. 
def distribution_graph(log, file_name='Distribution_graph.pdf'):    
    if file_name =='Distribution_graph.pdf':
        pm4py.save_vis_events_distribution_graph(log, file_path='./All_Episodes_Miner_Output/' + file_name, distr_type="months")
    else:
        pm4py.save_vis_events_distribution_graph(log, file_path='./Singular_Episode_Miner_Output/' + file_name, distr_type="months")

# MAIN
df = import_pm4py(import_csv(find_files('log_dataset.csv', 'C:')))

#sdhiraj: Use for Episode Window User Interaction
episode_list = df["case:concept:name"].unique()

# Convert DataFrame object into an EventLog object (which is required for querying variants):
event_log = pm4py.convert_to_event_log(df)
#wilgy: filter variants by percentage takes the user input for percentage selection and applies it to the
#event log in order to provide clearer visulalisations.
filter = pm4py.filter_variants_percentage(event_log, current_value.get())

# wilgy: Statistics - find the median case duration of the whole log
median_case_duration = cs.get_median_case_duration(event_log,
                                 parameters={cs.Parameters.TIMESTAMP_KEY: "time:timestamp"})
print("Median case duration of the entire data set(days): {}".format(round(median_case_duration / 86400, 2)))

# wilgy: Statistics - find the median case duration of the filtered log
filtered_median_case_duration = cs.get_median_case_duration(filter,
                                 parameters={cs.Parameters.TIMESTAMP_KEY: "time:timestamp"})
print("Median case duration of the filtered data set(days): {}".format(round(filtered_median_case_duration / 86400, 2)))

# wilgy: save a distribution graph of the filtered data set. 
distribution_graph(filter)

# wilgy: Call the selected method to produce respective process mining output.
# sdhiraj: added call for inductive and alpha miner
pmSelector = miner_selection.get()
#print('pmSelector: {}'.format(pmSelector))
if pmSelector == 1:
    pm_dfg(filter)
if pmSelector == 2:
    pm_heuristics(filter)
if pmSelector == 3:
    pm_alpha(filter)
if pmSelector == 4:
    pm_inductive(filter)

#shiraj: Get dataframe with case duration and episode numbers
variant_df = case_statistics.get_variants_df_with_case_duration(df)

#sdhiraj: Determine episodeNo that has minimum case time from start to finish and duration
min_case_duration_info = variant_df.loc[variant_df['caseDuration'].idxmin()]
min_case_duration_episode = variant_df['caseDuration'].idxmin()
min_case_duration = variant_df['caseDuration'].min()
print(
    "EpisodeNo {} has the minimum case duration (case time from start to finish). The case time is {} or {} days.".format(
        min_case_duration_episode, min_case_duration, round(min_case_duration / 86400, 2)))

#sdhiraj: Determine episodeNo that has maximum case time from start to finish and duration
max_case_duration_info = variant_df.loc[variant_df['caseDuration'].idxmax()]
max_case_duration_episode = variant_df['caseDuration'].idxmax()
max_case_duration = variant_df['caseDuration'].max()
print(
    "EpisodeNo {} has the maximum case duration (case time from start to finish). The case time is {} or {} days.".format(
        max_case_duration_episode, max_case_duration, round(max_case_duration / 86400, 2)))

# ---------------------------------------------------------------------------------------------------------------------
# sdhiraj: This section builds a user interactive window to select percentage thresholds
# ---------------------------------------------------------------------------------------------------------------------

#sdhiraj: populate the drop down with matching episodes
def get_episodes(*args):
    search_str = episode_entry.get()  # user entered episode
    episode_listbox.delete(0, tk.END)  # Delete listbox episodes
    for element in episode_list:
        if (re.match(search_str, element, re.IGNORECASE)):
            episode_listbox.insert(tk.END, element)  # insert matching episodes to listbox

#sdhiraj: switch between entry and listbox for selection
def drop_down(epi_window):  # down arrow is clicked
    episode_listbox.focus()  # once down arrow is clicked, the focus moves to listbox
    episode_listbox.selection_set(0)  # defaults selection to first option after shifting focus

#sdhiraj: for listbox selection, once value is selected, the entry box will be updated
def update_window(epi_window):
    ind = int(epi_window.widget.curselection()[0])  # listbox selection position
    val = epi_window.widget.get(ind)
    entry_str.set(val)  # set value for entry string
    #print(entry_str.get())
    episode_listbox.delete(0, tk.END)  # Delete listbox elements

#sdhiraj: heuristic by singular episode - calls singular_epi_window method and outputs result to "episodeNo_miner" file
def single_episode_heuristic():
    value = entry_str.get()
    episode_match = 0
    for element in episode_list:
        if value.__eq__(element): #if episode number matches episode in list
            episode_match, df_2, episode_event_log_2 = singular_epi_window(value)
            epi_map = pm4py.discovery.discover_heuristics_net(df_2, current_value.get())
            # The map object is a HeuristicsNet
            #print("Class name of variable map: " + map.__class__.__name__)
            #print("Visualizing heuristics net ...")
            #pm4py.view_heuristics_net(epi_map, "pdf")
            file_name = element + "_heuristics.png"
            file_name_path = "/" + element + "_heuristics.png"
            pm4py.vis.save_vis_heuristics_net(epi_map, file_name)
            singular_episode_miner_output(file_name_path)

    if episode_match == 0: #if invalid episode no, will give error pop up
        tk.messagebox.showerror("error", "Episode No was Invalid. Please try again.")

#sdhiraj: dfg by singular episode - calls singular_epi_window method and outputs result to "episodeNo_miner" file
def single_episode_dfg():
    value = entry_str.get()
    episode_match = 0
    for element in episode_list:
        if value.__eq__(element): #if episode number matches episode in list
            episode_match, df_2, episode_event_log_2 = singular_epi_window(value)
            epi_dfg, epi_start_activities, epi_end_actvities = pm4py.discover_dfg(episode_event_log_2)
            #pm4py.view_dfg(epi_dfg, epi_start_activities, epi_end_actvities, 'pdf')
            file_name = element + "_dfg.png"
            file_name_path = "/" + element + "_dfg.png"
            pm4py.vis.save_vis_dfg(epi_dfg, epi_start_activities, epi_end_actvities, file_name)
            singular_episode_miner_output(file_name_path)

    if episode_match == 0: #if invalid episode no, will give error pop up
        tk.messagebox.showerror("error", "Episode No was Invalid. Please try again.")

#sdhiraj: inductive by singular episode - calls singular_epi_window method and outputs result to "episodeNo_miner" file
def single_episode_inductive():
    value = entry_str.get()
    episode_match = 0
    for element in episode_list:
        if value.__eq__(element): #if episode number matches episode in list
            episode_match, df_2, episode_event_log_2 = singular_epi_window(value)
            epi_tree = inductive_miner.apply_tree(episode_event_log_2)
            epi_inductive_viz = pt_visualizer.apply(epi_tree)
            #pt_visualizer.view(epi_inductive_viz)
            file_name = element + "_inductive_tree.png"
            file_name_path = "/" + element + "_inductive_tree.png"
            pm4py.vis.save_vis_process_tree(epi_tree, file_name)
            singular_episode_miner_output(file_name_path)

            epi_net, epi_initial_marking, epi_final_marking = pt_converter.apply(epi_tree)
            parameters = {pm4py.visualization.petri_net.visualizer.Variants.FREQUENCY.value.Parameters.FORMAT: "png"}
            #petri_net_viz = pm4py.visualization.petri_net.visualizer.apply(epi_net, epi_initial_marking, epi_final_marking,
            #                                                       parameters=parameters,
            #                                                       variant=pm4py.visualization.petri_net.visualizer.Variants.FREQUENCY,
            #                                                       log=episode_event_log_2)
            #pm4py.visualization.petri_net.visualizer.view(petri_net_viz)
            file_name_petri = element + "_inductive_petri_net.png"
            file_name_petri_path = "/" + element + "_inductive_petri_net.png"
            pm4py.vis.save_vis_petri_net(epi_net, epi_initial_marking, epi_final_marking, file_name_petri)
            singular_episode_miner_output(file_name_petri_path)

    if episode_match == 0: #if invalid episode no, will give error pop up
        tk.messagebox.showerror("error", "Episode No was Invalid. Please try again.")

#sdhiraj: alpha by singular episode - calls singular_epi_window method and outputs result to "episodeNo_miner" file
def single_episode_alpha():
    value = entry_str.get()
    episode_match = 0
    for element in episode_list:
        if value.__eq__(element): #if episode number matches episode in list
            episode_match, df_2, episode_event_log_2 = singular_epi_window(value)
            epi_net, epi_start_activities, epi_end_activities = alpha_miner.apply(episode_event_log_2)  # sdhiraj: The map object is a PetriNet
            petri_net_viz = pm4py.visualization.petri_net.visualizer.apply(epi_net, epi_start_activities, epi_end_activities)
            #pm4py.visualization.petri_net.visualizer.view(petri_net_viz)
            file_name = element + "_alpha.png"
            file_name_path = "/" + element + "_alpha.png"
            pm4py.vis.save_vis_petri_net(epi_net, epi_start_activities, epi_end_activities, file_name)
            singular_episode_miner_output(file_name_path)

    if episode_match == 0: #if invalid episode no, will give error pop up
        tk.messagebox.showerror("error", "Episode No was Invalid. Please try again.")

#sdhiraj:Creates pop up window w episode info
def singular_epi_window(episode):
    episode_info_win= Toplevel(episode_window)
    episode_info_win.geometry("700x200")
    episode_info_win.title("Singular Episode Info")
    df_2 = df.loc[df["case:concept:name"] == episode]
    episode_event_log_2 = pm4py.convert_to_event_log(df_2)
    case_duration_2 = pm4py.statistics.traces.generic.log.case_statistics.get_median_case_duration(episode_event_log_2, parameters={pm4py.statistics.traces.generic.log.case_statistics.Parameters.TIMESTAMP_KEY: 'time:timestamp'})
    case_duration_2 = round(case_duration_2 / 86400, 2)
    # print(df2)
    string = "EpisodeID {} contains {} events. The total case duration is {} days".format(episode, len(df_2),case_duration_2)
    Label(episode_info_win, text= string).pack()
    episode_save_string = "Episode " + episode + " has been saved to Singular_Episode_Miner_Output folder."
    Label(episode_info_win, text= episode_save_string).pack()
    top_bu = tk.Button(episode_info_win, text="Finish", command=closeAll)
    top_bu.pack()
    episode_match = 1
    #wilgy: produce distribution graph for selected episode
    distribution_graph(episode_event_log_2, '{}_Distribution_graph.pdf'.format(episode))
    return episode_match, df_2, episode_event_log_2

# sdhiraj:moves png file to Singular_Episode_Miner_Output folder
def singular_episode_miner_output(file_name):
    script_dir = os.path.dirname(__file__)
    curr_file_dir = script_dir + file_name
    rel_path = "/Singular_Episode_Miner_Output" + file_name
    abs_file_path = script_dir + rel_path
    os.replace(curr_file_dir, abs_file_path)

#closes episode windows once "Finish" is clicked
def closeAll():
    episode_window.destroy()

# sdhiraj: Creating episode window for interaction with users.
episode_window = tk.Tk()

#sdhiraj: Customizing Episode Window and Title
episode_window.geometry("400x400")  # Window Size
episode_window.title("Episode No Info")  # Adding a window label
title_label = tk.Label(text='Episode No Info')  #Window Title
title_label.grid(row=1, column=3)

#sdhiraj: Listbox for Episode No which acts as a drop down list for Episode No
episode_listbox = tk.Listbox(episode_window, height=15, relief='flat', bg='SystemButtonFace', highlightcolor='SystemButtonFace')
episode_listbox.grid(row=3, column=3)

#sdhiraj: Textbox for Episode No so user can type Episode No
entry_str = tk.StringVar()
episode_entry = tk.Entry(episode_window, textvariable=entry_str)  # textbox for episode entry
episode_entry.grid(row=2, column=3)

#sdhiraj: binding functions to input fields based on type of user interaction
episode_entry.bind('<Down>', drop_down)  # down arrow key is pressed
episode_listbox.bind('<Return>', update_window)  # return key is pressed
episode_listbox.bind('<Double-1>', update_window)
entry_str.trace('w', get_episodes)

des_label = tk.Label(text='Select Miner Type for Episode Workflow')  #Window Title
des_label.grid(row=5, column=3)

#sdhiraj: Button once Episode No is selected. This will call function to open up another pop up with more Episode Info
dfg_bu = tk.Button(episode_window, text="dfg", command=single_episode_dfg)
dfg_bu.grid(row=6, column=2)
heuristics_bu = tk.Button(episode_window, text="Heuristics", command=single_episode_heuristic)
heuristics_bu.grid(row=6, column=4)
alpha_bu = tk.Button(episode_window, text="Alpha", command=single_episode_alpha)
alpha_bu.grid(row=8, column=2)
inductive_bu = tk.Button(episode_window, text="Inductive", command=single_episode_inductive)
inductive_bu.grid(row=8, column=4)
#sdhiraj: Keeps episode window open
episode_window.mainloop()

# ----------------------------------------------------------------------------------------------------------------------
# sdhiraj: End of Episode Selection window
# ----------------------------------------------------------------------------------------------------------------------