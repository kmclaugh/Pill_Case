#!/usr/bin/python
# Python Code used for testing a photoresistor_array circuit in LTSpice by rewriting the netlist file with new
# parameters, running the netlist in LTSpice, and interpreting the output
import re
import os
import itertools
from python_ltspice_tools import *

#---------------------------------------- Test Creators----------------------------------------#{{{1
def make_photoresitor_array_values(Photoresistor_Array_Values):
    """Turns a dictionary of photoresistors values into a list of params ready for simulation"""
    pr_dict = {}
    for key, value in Photoresistor_Array_Values.iteritems():
        if value == 1:
            value = "100"
        elif value == 0:
            value = "0"
        else:
            value = str(value)
        pr_dict[key] = value
    return(pr_dict)

def make_binary_string_values(binary_string,array_size,base_param_name):
    """converts a binary string to an photorestor array values dictionary."""
    x_total = array_size[0]
    y_total = array_size[1]
    array = []
    for y in range(0,y_total):
        row = []
        for x in range(0,x_total):
            param_name = base_param_name + str(x)+ "_" + str(y)
            row.append(param_name)
        array.append(row)
    photoresistor_array = {}
    binary_count = 0
    row_count = 0
    while row_count <= y_total-1:
        if row_count + 1 <= y_total-1:
            for xy0,xy1 in zip(array[row_count],array[row_count+1]):
                photoresistor_array[xy0] = int(binary_string[binary_count])
                binary_count += 1
                photoresistor_array[xy1] = int(binary_string[binary_count])
                binary_count += 1
        else:
            for xy0 in array[row_count]:
                photoresistor_array[xy0] = int(binary_string[binary_count])
                binary_count += 1
        row_count += 2
    return(photoresistor_array)

def make_specific_test(array_values,base_param_name):
    """convert an array of rows into a photoresistor array"""
    x_total = len(array_values[0])
    y_total = len(array_values)
    array_names = []
    for y in range(0,y_total):
        row = []
        for x in range(0,x_total):
            param_name = base_param_name + str(x) + "_" + str(y)
            row.append(param_name)
        array_names.append(row)
    photoresistor_array = {}
    for row_name,row_value in zip(array_names,array_values):
        for name,value in zip(row_name,row_value):
            photoresistor_array[name]=value
    return(photoresistor_array)
    
def all_combinations(array_size):
    """returns a list of binary strings that represent all possible combinations for the resistors.
        given the size of the array as a tuple (X,Y)."""
    total_resistors = array_size[0]*array_size[1]
   
    all_combos = ["".join(seq) for seq in itertools.product("01", repeat=total_resistors)]
    return(all_combos)

def max_16_combinations(array_size):
    """returns a list of binary string for a given array size of the first 16 possible combos.
        This corresponds to a 4x4 array which is theoretically the maximum size where one photoresistor
        could affect the other."""
    total_resistors = array_size[0]*array_size[1]
    all_combos = []
    total_count = 0
    for seq in itertools.product("01", repeat=total_resistors):
        if total_count > 15:
            break
        this_value = "".join(seq)
        all_combos.append(this_value)
        total_count += 1
    return(all_combos)
#----------------------------------------END Test Creators----------------------------------------#}}}

#---------------------------------------- make voltage cycle array values----------------------------------------#{{{1
def make_voltage_cycle_array_values(on_voltage,number_of_controls):
    """Given the one control voltage integer that should be turns on, this returns the list of voltage
        parameters with all but the given voltage turned off"""
    v_param_list = {}
    for v in range(0,number_of_controls):
        vparam_name = "vcon" + str(v)
        if v == on_voltage:
            vvalue = 5
        else:
            vvalue = -5
        v_param_list[vparam_name]=str(vvalue)
    return(v_param_list)
#----------------------------------------END make voltage cycle array value----------------------------------------#}}}

#----------------------------------------One Cylce Photoresitor Array Test----------------------------------------#{{{1
def one_cycle_photoresitor_test(photoresistor_array,array_size,netlist,base_test_name):
    """Run a single cyle of voltages with the given photoresistor values for the given array size. 
        Returns a list of the resulting the raw_values objects"""
    results = []
    netlist = netlist.change_parameters(variable_value_dictionary=photoresistor_array)
    for v in range(0,array_size[1]):
        
        v_param_list = make_voltage_cycle_array_values(v,array_size[1])
        new_netlist = netlist.change_parameters(variable_value_dictionary=v_param_list)
        new_raw_values = new_netlist.run_netlist()

        this_test_name = base_test_name + "." + str(v)
        netlist_results = netlist_results_class(new_netlist,new_raw_values,test_name=this_test_name)
        results.append(netlist_results)
    return(results)
#----------------------------------------END One Cylce Photoresitor Array Test----------------------------------------#}}}

#----------------------------------------Netlist-Results Class----------------------------------------#{{{1
class netlist_results_class:
    """A class containing both the netlist and resulting raw file for one cycle of a photoresistor array test.
        Methods for verifying the outputs match the input"""
    def __init__(self,netlist,raw_values,test_name):
        
        self.netlist= netlist
        self.raw_values = raw_values
        self.test_name = test_name

        #Dummy values to these attributes placed here for easy reference
        self.passed = "Passed"
        self.report = []
        self.error_report = []
        self.input_resistances = {} #of list of columns of resistor parameters statements
        self.vcontrols = []

        self.verify_cycle_routine()
 
    #----------------------------------------Verify Cycle Routine----------------------------------------#{{{2
    def verify_cycle_routine(self):
        """Checks that the resulting voltages correspend as expected with the resistances
            and voltages contaned in the netlist and raw_values objects. Checks that the only one input is on
            and the voltages for the output and within a given expected range based on the resistances."""
        #Test values
        Vcon_on = "5"
        Vcon_off = "-5"
        Vread_on = 4.0 #V
        Vread_off = 0.05 #V

        ##Collect input resistance values and makes sure only 1 Vcon is turned on
        xinput_resistances = {} #input resistances grouped by x values
        vcontrols = []
        found_von = False
        for variable, parameter_statement_obj in self.netlist.parameters.iteritems():
            if "vcon" in variable:
                control_number = int(''.join(x for x in variable if x.isdigit()))
                if parameter_statement_obj.value == Vcon_on:
                    if found_von == False:
                        self.von = control_number
                        found_von = True
                    else:
                        self.passed = "Failed"
                        self.error_report.append("Error: Two Vcon were turned on")
                vcontrols.append(parameter_statement_obj)
            if "lux" in variable:
                if "load" in variable:
                    pass
                else:
                    resistor_tuple = variable.split("_")
                    resistor_x = int(''.join(x for x in resistor_tuple[0] if x.isdigit()))
                    resistor_y = int(''.join(y for y in resistor_tuple[1] if y.isdigit()))
                    #if the x value is already in the dictionary append the param statement. If makes the new xkey
                    try:
                        xinput_resistances[str(resistor_x)].append((parameter_statement_obj,resistor_y))
                    except:
                        xinput_resistances[str(resistor_x)] = [(parameter_statement_obj,resistor_y)]
        
        #save the inputs for the reports
        self.input_resistances = xinput_resistances
        self.vcontrols = vcontrols

        ##Verify read voltages of the resistors connected to the Von are what they should be
        if found_von == False:
            self.passed = "Failed"
            self.error_report.append("Error: No Vcon were turned on")
        else:
            on_resistors = xinput_resistances[str(self.von)]
            for resistor in on_resistors:
                read_node = "read{}".format(resistor[1])
                read_node = self.raw_values.node_values[read_node]
                if resistor[0].value == "100":
                    if read_node.value <= Vread_on:
                        error = (resistor[0],read_node)
                        self.error_report.append(error)
                        self.passed = "Failed"
                    else:
                        report = (resistor[0],read_node)
                        self.report.append(report)
                elif resistor[0].value == "0":
                    if read_node.value >= Vread_off:
                        error = (resistor[0],read_node)
                        self.error_report.append(error)
                        self.passed = "Failed"
                    else:
                        report = (resistor[0],read_node)
                        self.report.append(report)
    #----------------------------------------END Verify Cycle Routine----------------------------------------#}}}
   
    def resistance_parameter_string(self):
        """Organizes the resitance parameters by colomun and returns a string for easy readibility"""
        row_total = len(self.input_resistances.itervalues().next())
        column_total = len(self.input_resistances)
        
        #make the empty string array of the right size
        a_row = []
        row_format_string = ""
        for column_number in range(0,column_total):
            a_row.append(0)
            row_format_string += "%15s"
        string_array = []
        for row_number in range(0,row_total):
            string_array.append(a_row)

        #populate the array with resistor parameter statements
        for column_number in range(0,column_total):
            this_column = self.input_resistances[str(column_number)]
            for row_number in range(0,row_total):
                stored_value = this_column[row_number] #(param_statement,row_number)
                string_array[stored_value[1]][column_number] = stored_value[0]
        
        resistor_string = ""
        for row in string_array:
            row_string = row_format_string % tuple(row)
            resistor_string += row_string + "\n"

        self.row_format_string = row_format_string
        return(resistor_string)

    def report_file_string(self):
        """generates the string to be inserted into the report"""
        final_string = "Test {} {}\n".format(self.test_name,self.passed)
        resistor_string = self.resistance_parameter_string()
        voltage_string = self.row_format_string % (self.vcontrols[0],self.vcontrols[2],self.vcontrols[1]) +"\n" #this is a bad hack
        final_string += voltage_string
        final_string += resistor_string
        
        report_string = ""
        for statement in self.report:
            report_string +=  str(statement[1]) + "\n"
        final_string += report_string
        
        return(final_string)
    
           

#----------------------------------------END Netlist-Results Class----------------------------------------#}}}                


#process original file and get resistor and voltage parameters
original_filename = "/home/kevin/.wine/drive_c/Program Files/LTC/LTspiceIV/Photoresistor_Array/Photoresistor_Array_Small.net"
original_netlist = netlist_class(original_filename)
array_size = (3,3)

#array_values = [[1,0,1],[1,1,0]]
#photoresistor_array = make_specific_test(array_values,"lux")
#all_results = one_cycle_photoresitor_test(photoresistor_array=photoresistor_array,array_size=array_size,netlist=original_netlist,
#                                        base_test_name=str(1))

def write_report(results,report_filename,error_filename):
    """Write the report to a file in an intellegible manner"""
    report_file = open(report_filename,"w")
    error_file = open(error_filename,"w")
    for result in results:
        print(result.test_name,result.passed)
        report_string = result.report_file_string()
        report_file.write(report_string)
        if result.passed == "Failed":
            error_file.write(report_string)
    report_file.close()
    error_file.close()

##Combinations test
combinations = max_16_combinations(array_size)
all_results = []
test_counter = 1
for combination in combinations:
    photoresistor_array = make_binary_string_values(binary_string=combinations[-1],array_size=array_size,base_param_name="lux")
    photoresistor_array = make_photoresitor_array_values(photoresistor_array)
    #Run photoresitor test
    results = one_cycle_photoresitor_test(photoresistor_array=photoresistor_array,array_size=array_size,netlist=original_netlist,
                                        base_test_name=str(test_counter))
    all_results += results
    test_counter += 1



error_filename = "/home/kevin/Projects/Pill_Case/Design/Photoresistor_Array/error_report"
report_filename = "/home/kevin/Projects/Pill_Case/Design/Photoresistor_Array/results_report"


write_report(all_results,report_filename,error_filename)
    
    
