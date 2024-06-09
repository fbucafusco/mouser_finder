import requests
import json
import re
import mult

power_unit_patterns = r'W|w|Watt|watt'
voltage_unit_patterns = r'V|v|Volt|volt'

api_calls = 0

voltage_rating_field_name = "voltage"

def search_component(api_key, keyword, records_per_request, starting_record, in_stock : bool = False, rohs : bool = False):
    global api_calls
    url = "https://api.mouser.com/api/v2/search/keyword?apiKey=" + api_key
    headers = {
        "Content-Type": "application/json"
    }

    search_options = "None"
    if in_stock and rohs:
        search_options = "RohsAndInStock"
    elif in_stock:
        search_options = "InStock"
    elif rohs:
        search_options = "Rohs"
 
    payload = {
        "SearchByKeywordRequest": {
            "keyword": keyword,
            "records": records_per_request,
            "startingRecord": starting_record,
            "searchOptions": search_options,
            # "searchWithYourSignUpLanguage": search_with_your_sign_up_language            
        }
    }
   
    response = requests.post(url, headers=headers, json=payload)
    api_calls += 1

    if response.status_code == 200:
        #open for write and append        
        with open('data_global.txt',  'a') as f:
            data = response.json()            
            parts = data.get("SearchResults", {}).get("Parts", [])
            for part in parts:
                f.write(json.dumps(part) + "\n")

        return response.json()
    else:
        response.raise_for_status()

def validate_component( params : dict) -> bool:
    valid_types = ["resistor", "capacitor", "inductor", "connector", "switch", "diode", "transistor", "ic", "led", "crystal", "oscillator", "fuse", "relay", "transformer", "sensor"]
    valid_packages = ["0603", "0805", "1206", "SOT-23", "SOT-223", "SOT-89"]
    valid_tolerances = re.compile(r"^\d+%$")
    valid_powers = re.compile(r"^\d+\/\d+W$")
    valid_voltages = re.compile(r"^\d+V$")
    valid_values = re.compile(r"^\d+[munpfhkMGTPEZY]?$")

    if 'type' in params and params['type'] not in valid_types:
        return False
    if 'package' in params and params['package'] not in valid_packages:
        return False
    if 'tolerance' in params and not valid_tolerances.match(params['tolerance']):
        return False
    if 'power' in params and not valid_powers.match(params['power']):
        return False
    if 'voltage' in params and not valid_voltages.match(params['voltage']):
        return False
    if 'value' in params and not valid_values.match(params['value']):
        return False

    return True

def get_keywords_from_params(params : dict) -> str:
    """
    Generates a list of keyword strings based on the provided component parameters.

    This function takes a dictionary of component parameters and generates a list of keyword strings. 
    Each keyword string is a combination of the value, tolerance, power (for resistors), or voltage (for capacitors) 
    of the component, along with the component type and package if they are provided. 
    The function generates all possible combinations of these parameters.

    Args:
        params (dict): A dictionary containing parameters for the type of component. 
            It includes type, package, tolerance, power, voltage, value, and flags for better power or voltage rating.

    Returns:
        list: A list of keyword strings for searching component descriptions.
    """
    value_variants = params['value_number_variants'] 
    tolerance_variants = params['tolerance_number_variants']

    keywords_list = []
    keywords = []

    #for each combination, we create a keyword
    if params['type'] == 'resistor':
        better_power_rating = (params.get('flags') or {}).get('better_power_rating', False)    
        power_variants = params['power_number_variants']  
        for v_v in value_variants:
            for p_v in power_variants:
                for t_v in tolerance_variants:
                    # kw = []
                    kw = [ f"{v_v[0]}{v_v[1]}" , f"{t_v[0]}{t_v[1]}%"  ]
                    if not better_power_rating:
                        kw.append( f"{p_v[0]}{p_v[1]}W" )

                    keywords_list.append( kw )

    elif params['type'] == 'capacitor':
        better_voltage_rating = (params.get('flags') or {}).get('better_voltage_rating', False)    
        voltage_variants = params['voltage_number_variants']
        for v_v in value_variants:
            for volt_v in voltage_variants:
                for t_v in tolerance_variants:
                    # kw = []
                    kw = [ f"{v_v[0]}{v_v[1]}" , f"{t_v[0]}{t_v[1]}%"  ]
                    if not better_voltage_rating:
                        kw.append( f"{volt_v[0]}{volt_v[1]}W" )

                    keywords_list.append( kw )

    for kw in keywords_list:    
        if 'type' in params:
            kw.append(params['type'])
        if 'package' in params:
            kw.append(params['package'])
        # if 'voltage' in params:
        #     kw.append(params['voltage'])

        kw = " ".join(kw)
        keywords.append(kw)
        
    return keywords

def calculate_search_patterns(component_params : dict) -> bool:
    """
    Calculates search patterns for filtering component descriptions.

    This function takes a dictionary of component parameters and calculates search patterns for each parameter. 
    These patterns are used for filtering component descriptions later. If the function cannot calculate 
    the search patterns due to invalid component parameters, it returns False.

    Args:
        component_params (dict): A dictionary containing parameters for the type of component. 
            It includes type, package, tolerance, power, voltage, value, and tempco.

    Returns:
        bool: True if the search patterns were successfully calculated, False otherwise.

    """

    if voltage_rating_field_name in component_params:
        if component_params['type']=='capacitor':  #only for caps  
            voltage = component_params[voltage_rating_field_name]            
            number, scale , unit = mult.split_value_multiplier_unit( voltage , voltage_unit_patterns)
            if number:
                number_variants = mult.get_number_variants_with_multi(number, scale)            
                regex_expression = mult.get_number_scale_regex_options(number_variants)
                component_params['voltage_pattern'] = rf"\b{regex_expression}\s*(?:{voltage_unit_patterns})\b" #this is for cleaning the description later            
                component_params['voltage_number_variants'] = number_variants #this is for create searching keyword 
                component_params['voltage_unit'] = unit
            else:
                print("Invalid power value for resistor")
                return False
        else:
            print("Invalid power value for component")
            return False        

    if 'power' in component_params:
        if component_params['type']=='resistor':  #only for resistors  
            power = component_params['power']            
            number, scale , unit = mult.split_value_multiplier_unit( power , power_unit_patterns)

            if number:
                number_variants = mult.get_number_variants_with_multi(number, scale)            
                regex_expression = mult.get_number_scale_regex_options(number_variants)
                component_params['power_pattern'] = rf"\b{regex_expression}\s*(?:{power_unit_patterns})\b" #this is for cleaning the description later            
                component_params['power_number_variants'] = number_variants #this is for create searching keyword 
                component_params['power_unit'] = unit
            else:
                print("Invalid power value for resistor")
                return False
        else:
            print("Invalid power value for component")
            return False
        
    if 'value' in component_params:        
        unit_patterns = []
        if component_params['type'] == 'resistor':
            unit_patterns = r'Ω|ohm|ohms'
            standard_unit = 'Ω'
        elif component_params['type'] == 'capacitor':
            unit_patterns = r'f|farad|farads'
            standard_unit = 'F'
        elif component_params['type'] == 'inductor':
            unit_patterns = r'h|henry|henries'
            standard_unit = 'H'
        else:
            print("Invalid component type")
            return False

        value = component_params['value']
        number, scale , unit = mult.split_value_multiplier_unit(value, unit_patterns)

        if number:
            number_variants = mult.get_number_variants_with_multi(number, scale)
            regex_expression = mult.get_number_scale_regex_options(number_variants)

            # scales = mult.get_scale_variants(scale)
            component_params["value_pattern"] = rf"\b{regex_expression}\s*(?:{unit_patterns})\b"
            component_params['value_number_variants'] = number_variants
        else:
            print("Invalid value for component")
            return False
        
    if 'tolerance' in component_params:
        #only for resistor capacitors an inductorss
        if component_params['type'] == 'resistor' or component_params['type'] == 'capacitor' or component_params['type'] == 'inductor':
            tolerance = component_params['tolerance']
            tolerance_patterns = r'%'
            number, scale , unit = mult.split_value_multiplier_unit(tolerance, tolerance_patterns)
            if number:
                number_variants = mult.get_number_variants_with_multi(number, scale)
                regex_expression = mult.get_number_scale_regex_options(number_variants)
                component_params['tolerance_pattern'] = rf"\b\s{regex_expression}\s*{tolerance_patterns}"     #\s so there is always an space before the numer
                component_params['tolerance_number_variants'] = number_variants
            else:
                print("Invalid value for component")
                return False 
        else:
            print("Invalid tolerance for component")
            return False
        
    if 'tempco' in component_params:
        tempco = component_params['tempco']
        tempco_unit_patterns = r'ppm'
        number,  unit = mult.split_value_unit(tempco, tempco_unit_patterns)
        if number:
            number_variants = mult.get_number_variants_with_multi(number, scale)
            regex_expression = mult.get_number_scale_regex_options(number_variants)
            component_params['tempco_pattern'] = rf"\b\s{regex_expression}\s*{tempco_unit_patterns}"     #\s so there is always an space before the numer
            component_params['tempco_number_variants'] = number_variants
            component_params['tempco_unit'] = unit
        else:
            print("Invalid tempco for component")
            return False
    
    # "package" does not have special preprocessing    
    # "tempco" does not have special preprocessing
        
    return True

def clenup_description(component_params : dict, description : str) -> tuple :
    """
    Cleans up and standardizes the description of an electronic component.

    This function takes a description of an electronic component and a dictionary of component parameters. 
    It standardizes the description by replacing various representations of the parameters (like power, 
    voltage, tolerance, type, package, and temperature coefficient) with a standard format. For example, 
    it replaces "1 W", "1W", "1 Watt", "1 watt", "1w", "1 watt", or "1watt" with "1W".

    Args:
        component_params (dict): A dictionary containing parameters for the type of component. 
            It includes type, package, tolerance, power, voltage, and value.
        description (str): The description of the component to be cleaned up.

    Returns:
        tuple: A tuple containing the cleaned up description and a boolean indicating whether the description is valid.
    """
    valid = False   #if the description is valid
    description = description.lower()
    #remove , from description
    description = description.replace(",", "")

    if 'value' in component_params:        
        value = component_params['value']
        value_pattern = component_params['value_pattern']  
        match = re.compile(value_pattern).search(description)
        if match:
            matched_text = match.group(0)
            description = description.replace(matched_text, value)
        else:
            return "", False #no match, invalid description
        

    if 'power' in component_params:  #only for resistors

        better_power_rating = component_params['flags'].get('better_power_rating', False)    
        power = component_params['power']
        power_pattern = component_params['power_pattern']        

        if not better_power_rating:
            match = re.compile( power_pattern ).search(description)
            if match:
                matched_text = match.group(0)
                description = description.replace(matched_text, power)
            else:
                return "", False #no match, invalid description                    
        else:     
            power_variants = component_params['power_number_variants']
            power_unit = component_params['power_unit']
                        
            #usando la unidad, hay que relevar el numero que indica la descripcion
            #luego, tomar el valor raw de los tempco_variants (sin el multiplicador)
            #compararlos, si la comparacion es valida, entonces crear un pattern nuevo y reemplazar. 
            value_match_pattern = re.compile(rf'{mult.decimal_number_pattern}\s*({power_unit_patterns})\b')            
            value_match = value_match_pattern.search(description)

            if value_match:
                value_matched = value_match.group(1) 
                value_matched = mult.convert_to_decimal(value_matched)
              
                value_power_rating = power_variants[0][0]
                value_power_rating = mult.convert_to_decimal(value_power_rating)

                if value_matched >= value_power_rating:
                    #accepted
                    matched_text = value_match.group(0)
                    description = description.replace(matched_text, mult.format_decimal (value_matched) + power_unit)
                else:
                    return "", False
            else:
                return "", False

    if 'voltage' in component_params :   #only for caps        
        better_voltage_rating = component_params['flags'].get('better_voltage_rating', False)            
        voltage = component_params[ voltage_rating_field_name ]
        voltage_pattern = component_params[ 'voltage_pattern' ]        

        if not better_voltage_rating:
          
            match = re.compile( voltage_pattern ).search(description)
            if match:
                matched_text = match.group(0)
                description = description.replace(matched_text, voltage)
            else:
                return "", False #no match, invalid description                    
        else:     
            voltage_variants = component_params[ 'voltage_number_variants' ]
            voltage_unit = component_params[ 'voltage_unit']
                        
            #usando la unidad, hay que relevar el numero que indica la descripcion
            #luego, tomar el valor raw de los tempco_variants (sin el multiplicador)
            #compararlos, si la comparacion es valida, entonces crear un pattern nuevo y reemplazar. 
            value_match_pattern = re.compile(rf'{mult.decimal_number_pattern}\s*({voltage_unit_patterns})\b')            
            value_match = value_match_pattern.search(description)

            if value_match:
                value_matched = value_match.group(1) 
                value_matched = mult.convert_to_decimal(value_matched)
              
                value_voltage_rating = voltage_variants[0][0]
                value_voltage_rating = mult.convert_to_decimal(value_voltage_rating)

                if value_matched >= value_voltage_rating:
                    #accepted
                    matched_text = value_match.group(0)
                    description = description.replace(matched_text, mult.format_decimal (value_matched) + voltage_unit)
                else:
                    return "", False
            else:
                return "", False

    if 'tolerance' in component_params:
        tolerance = component_params['tolerance']
        tolerance_pattern = component_params['tolerance_pattern']
        match = re.compile(tolerance_pattern).search(description)

        if match: #'\\b1\\s*(?:)?\\s*(?:%)\\b'
            matched_text = match.group(0)
            description = description.replace(matched_text, " " +  tolerance) #add space before the tolerance because the partter removed it.
        else:
            return "", False

    if 'type' in component_params:
        type_ = component_params['type']
        type_pattern = rf'\S*{type_}\S*'
        # description = type_pattern.sub(type_, description)
        match = re.compile(type_pattern).search(description)
        if match:
            matched_text = match.group(0)
            description = description.replace(matched_text, type_) #add space before the tolerance because the partter removed it.
        else:
            return "", False

    if 'package' in component_params:
        package = component_params['package']
        #the regex pattern should be such as can have the pachage name within another 
        #word, for example, 0603 can be within a word like "0603SMD"
        package_pattern = rf'\S*{package}\S*'
        match = re.compile(package_pattern).search(description)
        if match:
            matched_text = match.group(0)
            description = description.replace(matched_text, package) #add space before the tolerance because the partter removed it.
        else:
            return "", False
        
    if 'tempco' in component_params:                
        better_tempco = component_params['flags'].get('better_tempco', False)
        tempco_pattern = component_params['tempco_pattern']
        tempco = component_params['tempco']

        if not better_tempco:
            #tempco mus be exact
            # tempco_pattern = rf'\S*{tempco}\S*'

            match = re.compile(tempco_pattern).search(description)

            if match:
                matched_text = match.group(0)
                description = description.replace(matched_text, tempco)
            else:
                return "", False        
        else:
            tempco_pattern = component_params['tempco_pattern']
            tempco_variants = component_params['tempco_number_variants']
            tempco_unit = component_params['tempco_unit']

            #usando la unidad, hay que relevar el numero que indica la descripcion
            #luego, tomar el valor raw de los tempco_variants (sin el multiplicador)
            #compararlos, si la comparacion es valida, entonces crear un pattern nuevo y reemplazar. 
            value_match_pattern = re.compile(rf'(\d+)\s*{tempco_unit}')
            value_match = value_match_pattern.search(description)
            if value_match:
                value_matched = value_match.group(1)
                value = int(value_matched)
              
                value_tempco = tempco_variants[0][0]
                value = int(value_tempco)

                if value_matched <= value_tempco:
                    #accepted
                    matched_text = value_match.group(0)
                    description = description.replace(matched_text, value_matched + tempco_unit)
                else:
                    return "", False

            else:
                return "", False

    return description , True

def get_filtered_components(api_key , component_params : dict , total_occurrences , fields):
    """
    Fetches and filters electronic components based on given parameters.

    This function makes API calls to fetch electronic components data. It filters the data based on the 
    component parameters provided and returns the filtered data.

    Args:
        api_key (str): The API key to access the electronic components data.
        component_params (dict): A dictionary containing parameters for the type of component. 
            It includes type, package, tolerance, power, voltage, and value.
        total_occurrences (int): The total number of occurrences to fetch.
        fields (list): The fields to include in the returned data.

    Returns:
        list: A list of dictionaries, where each dictionary contains data for a component.

    Raises:
        HTTPError: If an error occurs during the API call.
    """
    global api_calls
        
    all_records = []
    records_per_request = 50
    starting_record = 0

    valid_spec = calculate_search_patterns(component_params)

    if not valid_spec:
        print("Invalid component params")
        return all_records

    keyword_list = get_keywords_from_params(component_params)
    print("Keyword: ", str(keyword_list))
    
    total_results = 0
    kw_idx = 0
    api_calls = 0

    # while starting_record < total_occurrences:
    while True:
        keyword = keyword_list[kw_idx]
        try:
            data = search_component(api_key, keyword, records_per_request, starting_record)
        except requests.exceptions.HTTPError as e:
            print( f"HTTP error:  {e} api calls {api_calls}")
            break

        total_results = data.get("SearchResults", {}).get("NumberOfResult", 0)

        parts = data.get("SearchResults", {}).get("Parts", [])
        
        for part in parts:
            filtered_part = {field: part.get(field) for field in fields}
            
            description_cleaned , res = clenup_description(component_params, filtered_part["Description"])

            if res:
                filtered_part["Description"] = description_cleaned
                all_records.append(filtered_part)
            else:
                print("Skipped record: ", filtered_part["Description"])

        starting_record += records_per_request
        if starting_record>=total_results:
            #no more records with the gioven keyword
            kw_idx += 1
            starting_record = 0
            if kw_idx >= len(keyword_list):
                #all keywords searched
                break

        if len(all_records) >= total_occurrences:
            #all found
            break  

    return all_records

#main function for the script
def main():

    #, "flags" : { "better_drift " : True, "better_power" : True, "better_tolerance" : True} // allows finding better components
    # params = { "type" : "resistor", "package" : "0603", "tolerance" : "1%", "power" : "1/10W", "value" : "2K7"  , "flags" : { "better_tempco" : False , "better_power_rating" : True } }
    params = { "type" : "capacitor", "package" : "0603", "tolerance" : "20%", voltage_rating_field_name : "50V", "value" : "1u"  , "flags" : { "better_voltage_rating" : False  } }

    # Example usage
    api_key = USER_API_KEY

    records =  get_filtered_components(api_key, params, 30 , ["Description", "Manufacturer", "ManufacturerPartNumber", "Category", "DatasheetUrl"])

    #create str with records but with a \n between each record
    records = "\n".join([str(record) for record in records])

    with open('result_total.txt', 'w') as f:
        f.write( records )

#main
if __name__ == "__main__":
    main()