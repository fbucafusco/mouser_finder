import re
from decimal import Decimal, getcontext

conversion_factors_down = {
    'm': Decimal('1e-3'),
    'u': Decimal('1e-6'),
    'n': Decimal('1e-9'),
    'p': Decimal('1e-12'),
    'f': Decimal('1e-15'),
}

conversion_factors_up = {
    'k': Decimal('1e3'),
    'K': Decimal('1e3'),
    'M': Decimal('1e6'),
    'G': Decimal('1e9')
}

def get_conversion_factor(prefix : str) -> Decimal:

    if prefix == '':
        return Decimal('1')

    try:
        return conversion_factors_down[prefix]
    except KeyError:
        try:
            return conversion_factors_up[prefix]
        except KeyError:
            raise ValueError(f"El prefijo '{prefix}' no es válido")
    
decimal_number_pattern = r'(\d+\.\d*|\.\d+|\d+/\d+|\d+)'

def get_scale_variants(scale: str) -> str:
    """
    Given a standard scale, return a string with all possible variants that can appear in the description.
    """
    if scale == 'u':
        return 'u|micro'
    elif scale == 'm':
        return 'm|milli'
    elif scale in ['k', 'K']:
        return 'k|K|kilo|Kilo'
    elif scale == 'M':
        return 'M|mega|Mega'
    elif scale == 'G':
        return 'G|giga|Giga'
    elif scale == 'T':
        return 'T|tera|Tera'
    elif scale == 'P':
        return 'P|peta|Peta'
    elif scale == 'E':
        return 'E|exa|Exa'
    elif scale == 'Z':
        return 'Z|zetta|Zetta'
    elif scale == 'Y':
        return 'Y|yotta|Yotta'
    elif scale == 'f':
        return 'f|femto|Femto'
    elif scale == 'p':
        return 'p|pico|Pico'
    elif scale == 'n':
        return 'n|nano|Nano'
    else:
        return scale
    
def build_mutiplier_patterns() -> str:
    """
    Builds a string pattern representing all possible scale variants.

    This function iterates over each character in the string 'umkKMGTPEZYfpn', 
    which represents different scale multipliers in electronics (micro, milli, kilo, etc.). 
    For each character, it calls the `get_scale_variants` function to get all possible 
    representations of that scale (for example, 'u', 'µ', and 'micro' for the micro scale). 
    It then joins all these representations together into a single string, separated by the 
    pipe character '|', which is used in regular expressions to mean "or". 

    Returns:
        str: A string pattern representing all possible scale variants, 
        suitable for use in a regular expression.
    """
    scales = [get_scale_variants(scale) for scale in 'umkKMGTPEZYfpn']
    return '|'.join(scales)

# Patrón de unidades
mutiplier_patterns = build_mutiplier_patterns()

def get_number_scale_regex_options( nm : list[tuple] ) -> str:
    #si lista son mas, entonces son opciones con | o sea ( |  | )     
    #si lista es 1, entonces es una sola opcion
    if len(nm) == 1:
        nm_ = nm[0]
        n = nm_[0]
        m = nm_[1]
        if m == "":
            return f"{n}\s*"
        else:
            return f"{n}\s*(?:{m})?"
        
    out = "("
    for n, m in nm:
        variants = get_scale_variants(m)
        print(f"{n} {variants}")
        if variants != "":
            out += f"{n}\s*(?:{variants})?|"
        else:
            out += f"{n}\s*|"

    out = out[:-1] + ")"
    return out


def convert_to_decimal(value : str) -> Decimal:    
    if '/' in value:
        numerator, denominator = value.split('/')
        value = Decimal(numerator) / Decimal(denominator)
    else:
        value = Decimal(value)
    return value

def format_decimal(value, precision=3) -> str:
    # Crear un Decimal con la precisión deseada
    quantize_str = '1.' + '0' * precision  # Por ejemplo, '1.000' para precision=3
    quantized_value = value.quantize(Decimal(quantize_str))
    # Convertir a cadena y eliminar ceros innecesarios
    return f"{quantized_value}".rstrip('0').rstrip('.')

def get_number_variants_with_multi(value : str, scale:str ) -> list:
    '''
    this value can be 1/10 or 0.1 or 10 10.0 
    but also scale can be "" or m 
    quiero obtener combinaciones de estos valores, por ej
    si es 1/10 con escala "" entonces tambien es 100m o 0.1
    si es 100 con escala "m" entonces tambien es 0.1 o 1/10
    si es 0.1 con escala "" entonces tambien es 100m o 1/10

    quiero que me generes una lista de keywords con las combinaciones posibles
    '''
    representations = []    #will store the complete representation

    getcontext().prec = 25

    # converts the raw value to a Decimal object
    value = convert_to_decimal(value)    

    # Convert the value to the standard unit (no scale)
    conversion_factor  = get_conversion_factor(scale)
    value_in_standard_unit = value * conversion_factor

    # Add the decimal representation
    value_formatted = format_decimal(value_in_standard_unit , 20 )
    representations.append( (value_formatted, "" ) )

    #add fraction representation only if the denominator is greater than 1 and less than 10 (this can be also be define as a param)
    #this is basically don for power ratings that are specified as franctions sometimes. 
    f = int(Decimal('1') / value_in_standard_unit)
    if f > 1 and f <= 10:
        value_formatted = f"1/{f}"
        representations.append( (value_formatted, "" ) )
    
    # Add the scaled representations
    # get_conversion_factor(scale)
    for scale, factor in conversion_factors_up.items():
        scaled_value = value_in_standard_unit / factor
        str_scaled_value = format_decimal(scaled_value , 20)

        if scaled_value > 1 :
            representations.append((f"{str_scaled_value}" , scale)) 
        else:
            #when you reach this point, there is no need to continue going up
            break
        
    for scale, factor in conversion_factors_down.items():
        scaled_value = value_in_standard_unit / factor
        str_scaled_value = format_decimal(scaled_value , 20)

        #HOW MANY 000 ARE IN THE 3LEAST SIGNIFICANT DIGITLS. iF THERE ARE 3 THE DOESNT MAKE SENSE TO CONTINUED GOING DOWN

        last_3_digits = str_scaled_value[-3:]
        if '.' in str_scaled_value:
            digits_to_left_of_decimal = str_scaled_value.split('.')[0][-3:]
        else:
            digits_to_left_of_decimal = str_scaled_value[-3:]

        if digits_to_left_of_decimal.count('0') == 3:
            #if there are 3 zeros in the 3 least significant digits, then there is no need to continue going down
            break

        representations.append((f"{str_scaled_value}" , scale)) 

    return representations

def split_value_unit(input :str, unit_patterns: str) -> tuple:
    pattern = rf"{decimal_number_pattern}\s*({unit_patterns})?"
    match = re.match(pattern, input)
    if match:
        number, unit = match.groups()
        # Normalizar la unidad de medida para manejar K y k de manera similar       
        if unit is None:
            unit = ''      

        return number,   unit
    else:        
        return None,   None


def split_value_multiplier_unit(input :str, unit_patterns: str) -> tuple:

    #for resistors we can also have 10K4
    pattern = rf"(\d+)({mutiplier_patterns})(\d+)\s*({unit_patterns})?"
    match = re.match(pattern, input)
    if match:
        num1, scale, num2, unit = match.groups()        
        number = f"{num1}.{num2}"
        if unit is None:
            unit = ''      
        return number, scale , unit
    else:        

        # Expresión regular para capturar números con o sin decimales y unidades de medida
        pattern = rf"{decimal_number_pattern}\s*({mutiplier_patterns})?\s*({unit_patterns})?"

        # Buscar coincidencias
        match = re.match(pattern, input  )
        
        if match:
            number, scale, unit = match.groups()
            # Normalizar la unidad de medida para manejar K y k de manera similar
            if scale is None:
                scale = ''            
            if unit is None:
                unit = ''
            return number, scale, unit        

    return None, None, None
 